from datetime import date, datetime, timedelta

from app.data import seed
from app.database import db
from app.models.schemas import ChatAction, ChatResponse, Intent, ResolutionType, TicketPriority
from app.services import session_manager as sm
from app.services.intent_classifier import (
    extract_coupon_code,
    extract_email,
    extract_order_id,
    extract_transaction_id,
)


def _status_label(status: str) -> str:
    labels = {
        "out_for_delivery": "out for delivery",
        "delivered": "delivered",
        "confirmed": "confirmed and being prepared",
        "shipped": "shipped",
        "cancelled": "cancelled",
    }
    return labels.get(status, status.replace("_", " "))


def _sid(session: dict) -> str:
    return session.get("session_id", "")


def handle_order_tracking(message: str, session: dict) -> ChatResponse:
    order_id = extract_order_id(message) or sm.get_ctx(session, "last_order_id")

    if not order_id:
        sm.mark_step(session, "awaiting_order_id", Intent.ORDER_TRACKING)
        return ChatResponse(
            message="I'd be happy to help track your order. Please share your Order ID (e.g., ZV123456).",
            intent=Intent.ORDER_TRACKING,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            awaiting_input="order_id",
        )

    order = db.get_order(order_id)
    if not order:
        attempts = sm.increment_failed(session)
        if attempts >= 3:
            return _escalate_missing_record(session, order_id, "Order not found in system")
        sm.mark_step(session, "awaiting_order_id", Intent.ORDER_TRACKING)
        return ChatResponse(
            message=f"I couldn't find order {order_id}. Please double-check your Order ID and try again.",
            intent=Intent.ORDER_TRACKING,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            awaiting_input="order_id",
        )

    sm.set_ctx(session, last_order_id=order_id)
    sm.reset_failed(session)
    session["step"] = None
    session["intent"] = None

    delivery = datetime.fromisoformat(order["expected_delivery"]).strftime("%B %d")
    msg = (
        f"Your order **{order_id}** for **{order['product_name']}** is currently "
        f"**{_status_label(order['status'])}** through **{order['courier']}** "
        f"and is expected to arrive by **{delivery}**."
    )
    return ChatResponse(
        message=msg,
        intent=Intent.ORDER_TRACKING,
        resolution_type=ResolutionType.INTERNAL,
        session_id=_sid(session),
    )


def handle_cashback(message: str, session: dict) -> ChatResponse:
    order_id = extract_order_id(message) or sm.get_ctx(session, "last_order_id")
    email = extract_email(message) or sm.get_ctx(session, "last_email")

    if not order_id and not email:
        sm.mark_step(session, "awaiting_cashback_identifier", Intent.CASHBACK)
        return ChatResponse(
            message="Please share your registered email address or Order ID so I can check your cashback status.",
            intent=Intent.CASHBACK,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            awaiting_input="email_or_order_id",
        )

    record = db.get_cashback(order_id=order_id, email=email)
    if not record:
        attempts = sm.increment_failed(session)
        if attempts >= 3:
            return _escalate_missing_record(session, order_id or email or "unknown", "Cashback record not found")
        sm.mark_step(session, "awaiting_cashback_identifier", Intent.CASHBACK)
        return ChatResponse(
            message="I couldn't find any cashback records for the details provided. Please verify and try again.",
            intent=Intent.CASHBACK,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            awaiting_input="email_or_order_id",
        )

    if order_id:
        sm.set_ctx(session, last_order_id=order_id)
    if email or record.get("email"):
        sm.set_ctx(session, last_email=email or record["email"])
    sm.set_ctx(
        session,
        last_cashback_status=record["status"],
        last_cashback_amount=record["amount"],
    )
    sm.reset_failed(session)
    sm.mark_step(session, "cashback_active", Intent.CASHBACK)

    if not record["eligible"]:
        msg = "This order was not eligible for cashback under the applicable terms."
    elif record["status"] == "pending":
        msg = "Your cashback is currently under processing and should reflect within 48 hours."
    elif record["status"] == "credited":
        credited_date = datetime.fromisoformat(record["credited_at"]).strftime("%B %d")
        msg = f"₹{record['amount']} cashback was successfully credited on {credited_date}."
    else:
        msg = "Your cashback status is being reviewed. Please check back shortly."

    return ChatResponse(
        message=msg,
        intent=Intent.CASHBACK,
        resolution_type=ResolutionType.INTERNAL,
        session_id=_sid(session),
    )


def handle_coupon(message: str, session: dict) -> ChatResponse:
    code = extract_coupon_code(message) or sm.get_ctx(session, "last_coupon_code")
    cart_value = sm.get_ctx(session, "cart_value", 3800)

    if not code:
        sm.mark_step(session, "awaiting_coupon_code", Intent.COUPON)
        return ChatResponse(
            message="Could you please share the coupon code you're trying to use?",
            intent=Intent.COUPON,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            awaiting_input="coupon_code",
        )

    coupon = db.get_coupon(code)
    if not coupon:
        attempts = sm.increment_failed(session)
        if attempts >= 3:
            return _escalate_missing_record(session, code, "Coupon not found")
        return ChatResponse(
            message=f"The coupon code **{code}** is not valid. Please check the code and try again.",
            intent=Intent.COUPON,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            awaiting_input="coupon_code",
        )

    sm.set_ctx(
        session,
        last_coupon_code=code,
        last_coupon_expires=coupon["expires_at"],
    )
    sm.reset_failed(session)
    sm.mark_step(session, "coupon_active", Intent.COUPON)

    expires = date.fromisoformat(coupon["expires_at"])
    if not coupon["active"] or expires < date.today():
        return ChatResponse(
            message=f"The coupon **{code}** expired on {expires.strftime('%B %d, %Y')}.",
            intent=Intent.COUPON,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    if coupon["used_count"] >= coupon["max_uses"]:
        return ChatResponse(
            message=f"The coupon **{code}** has reached its usage limit and is no longer available.",
            intent=Intent.COUPON,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    if not coupon["user_eligible"]:
        return ChatResponse(
            message=f"The coupon **{code}** is not available for your account.",
            intent=Intent.COUPON,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    if cart_value < coupon["min_cart"]:
        return ChatResponse(
            message=(
                f"The coupon **{code}** requires a minimum cart value of **₹{coupon['min_cart']:,}**. "
                f"Your current cart value is **₹{cart_value:,}**."
            ),
            intent=Intent.COUPON,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    return ChatResponse(
        message=f"Great news! Coupon **{code}** is valid and will give you **₹{coupon['discount']}** off.",
        intent=Intent.COUPON,
        resolution_type=ResolutionType.INTERNAL,
        session_id=_sid(session),
    )


def handle_payment(message: str, session: dict) -> ChatResponse:
    # Retry refund within active payment workflow
    if sm.is_retry_refund(message) and sm.get_ctx(session, "last_transaction_id"):
        txn_id = sm.get_ctx(session, "last_transaction_id")
        sm.reset_failed(session)
        return ChatResponse(
            message=(
                f"I've re-initiated the refund check for transaction **{txn_id}**. "
                "The refund is processing and should reflect within **5–7 business days**."
            ),
            intent=Intent.PAYMENT,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            actions=[ChatAction(label="Retry Refund", action="retry_refund", payload={"transaction_id": txn_id})],
        )

    txn_id = extract_transaction_id(message) or sm.get_ctx(session, "last_transaction_id")

    if not txn_id:
        sm.mark_step(session, "awaiting_transaction_id", Intent.PAYMENT)
        return ChatResponse(
            message="Please provide your Transaction ID (e.g., TXN987654321) so I can verify the payment status.",
            intent=Intent.PAYMENT,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            awaiting_input="transaction_id",
        )

    payment = db.get_payment(txn_id)
    if not payment:
        attempts = sm.increment_failed(session)
        if attempts >= 3:
            return _escalate_missing_record(session, txn_id, "Payment record not found")
        sm.mark_step(session, "awaiting_transaction_id", Intent.PAYMENT)
        return ChatResponse(
            message=f"I couldn't find transaction **{txn_id}**. Please verify the Transaction ID.",
            intent=Intent.PAYMENT,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            awaiting_input="transaction_id",
        )

    sm.set_ctx(session, last_transaction_id=txn_id)
    sm.reset_failed(session)

    if payment["status"] == "mismatch":
        return _escalate_payment_mismatch(session, payment)

    if payment["status"] == "failed" or not payment["order_created"]:
        sm.mark_step(session, "refund_offered", Intent.PAYMENT)
        return ChatResponse(
            message="We've initiated an automatic refund. It should reflect within 5–7 business days.",
            intent=Intent.PAYMENT,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            actions=[
                ChatAction(
                    label="Retry Refund",
                    action="retry_refund",
                    payload={"transaction_id": txn_id},
                )
            ],
        )

    session["step"] = None
    session["intent"] = None
    return ChatResponse(
        message=f"Your payment was successful and your order **{payment['order_id']}** has been confirmed.",
        intent=Intent.PAYMENT,
        resolution_type=ResolutionType.INTERNAL,
        session_id=_sid(session),
    )


def handle_return(message: str, session: dict) -> ChatResponse:
    step = session.get("step")

    # Confirmation step — user responds Yes / No / Initiate Return
    if step == "awaiting_confirmation":
        return _handle_return_confirmation(message, session)

    order_id = extract_order_id(message) or sm.get_ctx(session, "last_order_id")

    if not order_id:
        sm.mark_step(session, "awaiting_return_order_id", Intent.RETURN_REFUND)
        return ChatResponse(
            message="Please share your Order ID so I can check return eligibility.",
            intent=Intent.RETURN_REFUND,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            awaiting_input="order_id",
        )

    order = db.get_order(order_id)
    if not order:
        attempts = sm.increment_failed(session)
        if attempts >= 3:
            return _escalate_missing_record(session, order_id, "Order not found for return")
        sm.mark_step(session, "awaiting_return_order_id", Intent.RETURN_REFUND)
        return ChatResponse(
            message=f"I couldn't find order **{order_id}**. Please verify and try again.",
            intent=Intent.RETURN_REFUND,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
            awaiting_input="order_id",
        )

    sm.set_ctx(session, last_order_id=order_id)
    sm.reset_failed(session)

    if order["category"] in seed.NON_RETURNABLE_CATEGORIES:
        sm.clear_workflow(session)
        return ChatResponse(
            message="This product category is not eligible for return as per Zave's return policy.",
            intent=Intent.RETURN_REFUND,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    if order["status"] != "delivered" or not order.get("delivered_at"):
        sm.clear_workflow(session)
        return ChatResponse(
            message="Returns can only be initiated after the product has been delivered.",
            intent=Intent.RETURN_REFUND,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    delivered = date.fromisoformat(order["delivered_at"])
    deadline = delivered + timedelta(days=seed.RETURN_WINDOW_DAYS)
    if date.today() > deadline:
        sm.clear_workflow(session)
        return ChatResponse(
            message=f"The return window for this order closed on {deadline.strftime('%B %d, %Y')}.",
            intent=Intent.RETURN_REFUND,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    sm.set_ctx(session, last_product_name=order["product_name"], return_deadline=deadline.isoformat())
    sm.mark_step(session, "awaiting_confirmation", Intent.RETURN_REFUND)

    return ChatResponse(
        message=(
            f"Your **{order['product_name']}** is eligible for return until "
            f"**{deadline.strftime('%B %d')}**. Would you like me to initiate the return process?"
        ),
        intent=Intent.RETURN_REFUND,
        resolution_type=ResolutionType.INTERNAL,
        session_id=_sid(session),
        awaiting_input="confirmation",
        actions=[ChatAction(label="Initiate Return", action="initiate_return", payload={"order_id": order_id})],
    )


def _handle_return_confirmation(message: str, session: dict) -> ChatResponse:
    order_id = sm.get_ctx(session, "last_order_id")

    if sm.is_negative(message):
        sm.clear_workflow(session)
        return ChatResponse(
            message="No problem — I've cancelled the return request. Let me know if you need anything else.",
            intent=Intent.RETURN_REFUND,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    if sm.is_affirmative(message) or sm.is_initiate_return(message):
        return handle_initiate_return(session, order_id or "")

    # Re-prompt if unclear
    return ChatResponse(
        message="Would you like me to initiate the return? Reply **Yes** or **No**, or tap **Initiate Return**.",
        intent=Intent.RETURN_REFUND,
        resolution_type=ResolutionType.INTERNAL,
        session_id=_sid(session),
        awaiting_input="confirmation",
        actions=[
            ChatAction(
                label="Initiate Return",
                action="initiate_return",
                payload={"order_id": order_id},
            )
        ],
    )


def handle_account(message: str, session: dict) -> ChatResponse:
    text = message.lower()
    email = extract_email(message) or sm.get_ctx(session, "last_email", "priya@example.com")
    if extract_email(message):
        sm.set_ctx(session, last_email=email)
    user = db.get_user_by_email(email)

    if "otp" in text or "not received" in text or "didn't receive" in text:
        last4 = user["mobile_last4"] if user else "****"
        sm.reset_failed(session)
        return ChatResponse(
            message=f"I've sent a new OTP to your registered mobile number ending in **{last4}**.",
            intent=Intent.ACCOUNT,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    if "password" in text or "reset" in text:
        sm.reset_failed(session)
        return ChatResponse(
            message=f"A password reset link has been sent to **{email}**. The link expires in 30 minutes.",
            intent=Intent.ACCOUNT,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    if "email" in text and ("wrong" in text or "mismatch" in text or "different" in text):
        return ChatResponse(
            message="It looks like there's an email mismatch. Please contact support with your registered phone number for verification.",
            intent=Intent.ACCOUNT,
            resolution_type=ResolutionType.INTERNAL,
            session_id=_sid(session),
        )

    return ChatResponse(
        message=(
            "I can help with login issues. Are you facing:\n"
            "• OTP not received\n"
            "• Password reset needed\n"
            "• Email mismatch\n\n"
            "Please describe your issue."
        ),
        intent=Intent.ACCOUNT,
        resolution_type=ResolutionType.INTERNAL,
        session_id=_sid(session),
    )


def handle_greeting(session: dict) -> ChatResponse:
    return ChatResponse(
        message=(
            "Hi! I'm Zave Assist — your shopping support specialist. "
            "I can help with order tracking, cashback, coupons, payments, returns, and product recommendations. "
            "How can I help you today?"
        ),
        intent=Intent.GREETING,
        resolution_type=ResolutionType.INTERNAL,
        session_id=_sid(session),
    )


def handle_irrelevant(session: dict) -> ChatResponse:
    return ChatResponse(
        message="I'm designed specifically to assist with Zave-related shopping and support queries.",
        intent=Intent.IRRELEVANT,
        resolution_type=ResolutionType.BLOCKED,
        session_id=_sid(session),
    )


def handle_initiate_return(session: dict, order_id: str) -> ChatResponse:
    order_id = order_id or sm.get_ctx(session, "last_order_id") or ""
    ref_id = sm.generate_return_ref_id(order_id)
    sm.reset_failed(session)
    sm.clear_workflow(session)

    return ChatResponse(
        message=(
            f"I've initiated the return request for order **{order_id}**.\n"
            f"Pickup has been scheduled.\n"
            f"Reference ID: **{ref_id}**."
        ),
        intent=Intent.RETURN_REFUND,
        resolution_type=ResolutionType.INTERNAL,
        session_id=_sid(session),
    )


def handle_retry_refund(session: dict, transaction_id: str) -> ChatResponse:
    txn_id = transaction_id or sm.get_ctx(session, "last_transaction_id") or ""
    sm.set_ctx(session, last_transaction_id=txn_id)
    sm.mark_step(session, "refund_offered", Intent.PAYMENT)
    sm.reset_failed(session)

    return ChatResponse(
        message=(
            f"I've re-initiated the refund check for transaction **{txn_id}**. "
            "The refund is processing and should reflect within **5–7 business days**."
        ),
        intent=Intent.PAYMENT,
        resolution_type=ResolutionType.INTERNAL,
        session_id=_sid(session),
        actions=[
            ChatAction(label="Retry Refund", action="retry_refund", payload={"transaction_id": txn_id})
        ],
    )


def _escalate_missing_record(session: dict, record_id: str, reason: str) -> ChatResponse:
    ticket = db.create_ticket(
        user_id=session.get("user_id", "guest"),
        email=sm.get_ctx(session, "last_email"),
        order_id=record_id if isinstance(record_id, str) and record_id.startswith("ZV") else sm.get_ctx(session, "last_order_id"),
        transcript=session.get("transcript", []),
        reason=f"{reason}: {record_id}",
        priority=TicketPriority.HIGH,
    )
    sm.clear_workflow(session)
    return ChatResponse(
        message="I couldn't locate this in our system. I've escalated your case to our support team — you'll hear back within 24 hours.",
        intent=Intent.ESCALATION,
        resolution_type=ResolutionType.ESCALATED,
        session_id=_sid(session),
        ticket_id=ticket["id"],
    )


def _escalate_payment_mismatch(session: dict, payment: dict) -> ChatResponse:
    ticket = db.create_ticket(
        user_id=session.get("user_id", "guest"),
        email=sm.get_ctx(session, "last_email"),
        order_id=payment.get("order_id"),
        transcript=session.get("transcript", []),
        reason=f"Payment mismatch: {payment['transaction_id']}",
        priority=TicketPriority.CRITICAL,
    )
    sm.clear_workflow(session)
    return ChatResponse(
        message="There appears to be a discrepancy with your payment. I've created a priority ticket — our team will resolve this within 4 hours.",
        intent=Intent.ESCALATION,
        resolution_type=ResolutionType.ESCALATED,
        session_id=_sid(session),
        ticket_id=ticket["id"],
    )


def handle_escalation(message: str, session: dict) -> ChatResponse:
    text = message.lower()
    priority = TicketPriority.HIGH
    reason = "Customer requested escalation"

    if "fraud" in text or "scam" in text:
        priority = TicketPriority.CRITICAL
        reason = "Fraud report"
    elif any(w in text for w in ["unhappy", "worst", "complaint", "legal"]):
        priority = TicketPriority.HIGH
        reason = "Customer dissatisfaction"
    elif session.get("failed_attempts", 0) >= 3:
        reason = "Multiple failed attempts"

    ticket = db.create_ticket(
        user_id=session.get("user_id", "guest"),
        email=sm.get_ctx(session, "last_email"),
        order_id=sm.get_ctx(session, "last_order_id"),
        transcript=session.get("transcript", []),
        reason=reason,
        priority=priority,
    )
    sm.clear_workflow(session)
    return ChatResponse(
        message="I've connected you with our support team. A specialist will reach out shortly.",
        intent=Intent.ESCALATION,
        resolution_type=ResolutionType.ESCALATED,
        session_id=_sid(session),
        ticket_id=ticket["id"],
    )
