"""Lightweight session context helpers for multi-turn workflows."""

import uuid
from datetime import date, timedelta
from typing import Any, Optional

from app.models.schemas import ChatResponse, Intent, ResolutionType

# Steps waiting for user input — route to active handler before re-classifying
AWAITING_STEPS = frozenset({
    "awaiting_order_id",
    "awaiting_return_order_id",
    "awaiting_confirmation",
    "awaiting_cashback_identifier",
    "awaiting_coupon_code",
    "awaiting_transaction_id",
})

# Steps that keep intent alive after a response (including follow-up-capable states)
CONTINUATION_STEPS = AWAITING_STEPS | frozenset({
    "refund_offered",
    "cashback_active",
    "coupon_active",
})

AFFIRMATIVE = frozenset({
    "yes", "yeah", "yep", "sure", "ok", "okay", "please", "go ahead", "confirm", "do it",
})
NEGATIVE = frozenset({"no", "nope", "cancel", "don't", "dont", "never mind", "nevermind"})


def ensure_context(session: dict) -> dict[str, Any]:
    if "context" not in session or session["context"] is None:
        session["context"] = {}
    return session["context"]


def get_ctx(session: dict, key: str, default: Any = None) -> Any:
    return ensure_context(session).get(key, default)


def set_ctx(session: dict, **kwargs: Any) -> None:
    ctx = ensure_context(session)
    ctx.update(kwargs)


def clear_workflow(session: dict, *, keep_context: bool = True) -> None:
    """Reset active workflow while optionally retaining recall fields."""
    ctx = ensure_context(session)
    recall = {k: ctx[k] for k in (
        "last_order_id", "last_transaction_id", "last_coupon_code", "last_email",
        "last_cashback_status", "last_cashback_amount", "last_coupon_expires",
    ) if k in ctx} if keep_context else {}
    session["intent"] = None
    session["step"] = None
    session["context"] = recall


def mark_step(session: dict, step: str, intent: Intent | str) -> None:
    session["step"] = step
    session["intent"] = intent.value if isinstance(intent, Intent) else intent


def has_active_workflow(session: dict) -> bool:
    return bool(session.get("intent") and session.get("step"))


def has_awaiting_step(session: dict) -> bool:
    return session.get("step") in AWAITING_STEPS


def should_persist_workflow(session: dict, response: ChatResponse) -> bool:
    if response.awaiting_input:
        return True
    if session.get("step") in CONTINUATION_STEPS:
        return True
    return False


def finalize_workflow_state(session: dict, response: ChatResponse) -> None:
    """Update session after a handler returns — keep or clear workflow state."""
    if response.resolution_type.value == "escalated":
        clear_workflow(session, keep_context=True)
        return

    if should_persist_workflow(session, response):
        return

    if not response.awaiting_input:
        session["step"] = None
        session["intent"] = None
        session["failed_attempts"] = 0


def is_affirmative(message: str) -> bool:
    text = message.lower().strip().rstrip(".!")
    return text in AFFIRMATIVE or text.startswith("yes ")


def is_negative(message: str) -> bool:
    text = message.lower().strip().rstrip(".!")
    return text in NEGATIVE or text.startswith("no ")


def is_initiate_return(message: str) -> bool:
    text = message.lower().strip()
    return "initiate return" in text or text in {"initiate", "start return", "return it"}


def is_retry_refund(message: str) -> bool:
    text = message.lower().strip()
    return "retry refund" in text or text in {"retry", "check refund again", "refund status"}


def increment_failed(session: dict) -> int:
    session["failed_attempts"] = session.get("failed_attempts", 0) + 1
    return session["failed_attempts"]


def reset_failed(session: dict) -> None:
    session["failed_attempts"] = 0


def generate_return_ref_id(order_id: str) -> str:
    return f"RET{order_id[-5:]}{uuid.uuid4().hex[:3].upper()}"


def try_session_recall(message: str, session: dict) -> Optional[ChatResponse]:
    """Answer recall questions from stored session context."""
    text = message.lower().strip()
    sid = session.get("session_id", "")

    order_recall = (
        "what was my order id",
        "what is my order id",
        "which order id",
        "my order id",
        "order id again",
    )
    if any(p in text for p in order_recall):
        order_id = get_ctx(session, "last_order_id")
        if order_id:
            return ChatResponse(
                message=f"Your last order ID in this conversation was **{order_id}**.",
                intent=Intent.ORDER_TRACKING,
                resolution_type=ResolutionType.INTERNAL,
                session_id=sid,
            )

    return None


def try_context_follow_up(message: str, session: dict) -> Optional[ChatResponse]:
    """Handle follow-ups that rely on stored context without re-classifying intent."""
    text = message.lower().strip()
    sid = session.get("session_id", "")

    # Cashback timing follow-up
    if any(p in text for p in ("when will i receive", "how long", "when will it reflect", "when do i get")):
        status = get_ctx(session, "last_cashback_status")
        amount = get_ctx(session, "last_cashback_amount")
        if status == "pending":
            return ChatResponse(
                message=(
                    f"Your ₹{amount} cashback is still processing. "
                    "It should reflect in your Zave wallet within **48 hours** of order delivery."
                ),
                intent=Intent.CASHBACK,
                resolution_type=ResolutionType.INTERNAL,
                session_id=sid,
            )
        if status == "credited":
            return ChatResponse(
                message="Your cashback has already been credited to your Zave wallet.",
                intent=Intent.CASHBACK,
                resolution_type=ResolutionType.INTERNAL,
                session_id=sid,
            )

    # Coupon validity follow-up
    if any(p in text for p in ("can i use it tomorrow", "use tomorrow", "valid tomorrow", "still valid")):
        code = get_ctx(session, "last_coupon_code")
        expires = get_ctx(session, "last_coupon_expires")
        if code and expires:
            tomorrow = date.today() + timedelta(days=1)
            exp_date = date.fromisoformat(expires)
            if exp_date >= tomorrow:
                return ChatResponse(
                    message=(
                        f"Yes! Coupon **{code}** is valid until **{exp_date.strftime('%B %d, %Y')}**, "
                        "so you can use it tomorrow."
                    ),
                    intent=Intent.COUPON,
                    resolution_type=ResolutionType.INTERNAL,
                    session_id=sid,
                )
            return ChatResponse(
                message=f"Coupon **{code}** expires on **{exp_date.strftime('%B %d, %Y')}** and won't be valid tomorrow.",
                intent=Intent.COUPON,
                resolution_type=ResolutionType.INTERNAL,
                session_id=sid,
            )

    # Return confirmation via text (when step may have been lost but context remains)
    if is_initiate_return(message) or (is_affirmative(message) and get_ctx(session, "last_order_id") and session.get("step") == "awaiting_confirmation"):
        order_id = get_ctx(session, "last_order_id")
        if order_id and session.get("intent") == Intent.RETURN_REFUND.value:
            return None  # let flows.handle_return_confirmation handle via active workflow

    # Payment retry via text
    if is_retry_refund(message) and get_ctx(session, "last_transaction_id"):
        return None  # let flows.handle_payment handle via active workflow

    return None


def resolve_active_intent(message: str, session: dict) -> bool:
    """
    Returns True if the message should continue an awaiting workflow
    instead of re-classifying intent (e.g. bare order ID during return flow).
    """
    if not has_awaiting_step(session):
        return False

    active = session.get("intent")
    step = session.get("step")

    if active == Intent.RETURN_REFUND.value and step in ("awaiting_return_order_id", "awaiting_confirmation"):
        return True
    if active == Intent.ORDER_TRACKING.value and step == "awaiting_order_id":
        return True
    if active == Intent.CASHBACK.value and step == "awaiting_cashback_identifier":
        return True
    if active == Intent.COUPON.value and step == "awaiting_coupon_code":
        return True
    if active == Intent.PAYMENT.value and step == "awaiting_transaction_id":
        return True

    return False
