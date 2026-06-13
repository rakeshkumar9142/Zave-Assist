from app.models.schemas import ChatResponse, Intent, ResolutionType
from app.services import flows
from app.services.gemini_service import get_product_recommendations
from app.services.intent_classifier import classify_intent, extract_price_limit
from app.services import session_manager as sm


WORKFLOW_HANDLERS = {
    Intent.ORDER_TRACKING: flows.handle_order_tracking,
    Intent.CASHBACK: flows.handle_cashback,
    Intent.COUPON: flows.handle_coupon,
    Intent.PAYMENT: flows.handle_payment,
    Intent.RETURN_REFUND: flows.handle_return,
    Intent.ACCOUNT: flows.handle_account,
    Intent.GREETING: lambda msg, session: flows.handle_greeting(session),
    Intent.IRRELEVANT: lambda msg, session: flows.handle_irrelevant(session),
    Intent.ESCALATION: flows.handle_escalation,
}


class DecisionEngine:
    """
    Support Decision Engine — exact sequence:
    1. Identify intent
    2. Check if operational workflow exists
    3. Query internal databases
    4. Return deterministic responses
    5. Use Gemini only for recommendation or reasoning tasks
    6. Escalate unresolved issues
    """

    async def process(
        self,
        message: str,
        session: dict,
        *,
        action: str | None = None,
        action_payload: dict | None = None,
    ) -> ChatResponse:
        session["session_id"] = session.get("session_id", "")
        text = message.strip()

        # Escalate after repeated failures (unless resolving via action)
        if not action and session.get("failed_attempts", 0) >= 3:
            return flows.handle_escalation(message, session)

        # Handle button / action triggers
        if action == "initiate_return":
            response = flows.handle_initiate_return(
                session, (action_payload or {}).get("order_id", "")
            )
            sm.finalize_workflow_state(session, response)
            return response

        if action == "retry_refund":
            response = flows.handle_retry_refund(
                session, (action_payload or {}).get("transaction_id", "")
            )
            sm.finalize_workflow_state(session, response)
            return response

        # Session recall (e.g. "What was my order ID?")
        recall = sm.try_session_recall(text, session)
        if recall:
            return recall

        # Contextual follow-ups (cashback timing, coupon tomorrow)
        follow_up = sm.try_context_follow_up(text, session)
        if follow_up:
            return follow_up

        # Payment retry within refund workflow
        if sm.is_retry_refund(text) and sm.get_ctx(session, "last_transaction_id"):
            response = flows.handle_payment(text, session)
            sm.finalize_workflow_state(session, response)
            return response

        # Continue awaiting multi-turn workflow without re-classifying
        if sm.resolve_active_intent(text, session):
            intent = Intent(session["intent"])
            handler = WORKFLOW_HANDLERS.get(intent)
            if handler:
                response = handler(text, session)
                sm.finalize_workflow_state(session, response)
                return response

        # Text-based "Initiate Return" when confirmation context exists
        if sm.is_initiate_return(text) and sm.get_ctx(session, "last_order_id"):
            if session.get("step") == "awaiting_confirmation" or session.get("intent") == Intent.RETURN_REFUND.value:
                response = flows.handle_initiate_return(session, sm.get_ctx(session, "last_order_id"))
                sm.finalize_workflow_state(session, response)
                return response

        # Classify new intent
        intent = classify_intent(text)

        # Block irrelevant queries (no LLM)
        if intent == Intent.IRRELEVANT:
            sm.clear_workflow(session, keep_context=True)
            return flows.handle_irrelevant(session)

        # Fraud / explicit escalation always takes priority
        if intent == Intent.ESCALATION:
            response = flows.handle_escalation(text, session)
            sm.finalize_workflow_state(session, response)
            return response

        session["intent"] = intent.value

        # Gemini only for product recommendations
        if intent == Intent.RECOMMENDATION:
            max_price = extract_price_limit(text) or 2000
            response_text = await get_product_recommendations(text, max_price)
            sm.clear_workflow(session, keep_context=True)
            return ChatResponse(
                message=response_text,
                intent=Intent.RECOMMENDATION,
                resolution_type=ResolutionType.GEMINI,
                session_id=session["session_id"],
            )

        handler = WORKFLOW_HANDLERS.get(intent)
        if handler:
            response = handler(text, session)
            sm.finalize_workflow_state(session, response)
            return response

        # Unknown intent — increment failed attempts if mid-workflow
        if sm.has_active_workflow(session):
            sm.increment_failed(session)

        if session.get("failed_attempts", 0) >= 3:
            return flows.handle_escalation(text, session)

        session["step"] = None
        session["intent"] = None
        return ChatResponse(
            message=(
                "I'm not sure I understood that. I can help with:\n"
                "• Order tracking\n• Cashback issues\n• Coupon problems\n"
                "• Payment issues\n• Returns & refunds\n• Account/login help\n"
                "• Product recommendations\n\n"
                "What would you like help with?"
            ),
            intent=Intent.UNKNOWN,
            resolution_type=ResolutionType.INTERNAL,
            session_id=session["session_id"],
        )


decision_engine = DecisionEngine()
