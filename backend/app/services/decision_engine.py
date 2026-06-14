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
    Support Decision Engine

    Sequence:
    1. Identify intent
    2. Check operational workflow
    3. Query internal data
    4. Return deterministic responses
    5. Use Gemini only for recommendations
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

        # --------------------------------------------------
        # 1. Handle explicit actions
        # --------------------------------------------------
        if action == "initiate_return":
            response = flows.handle_initiate_return(
                session,
                (action_payload or {}).get("order_id", ""),
            )

            sm.finalize_workflow_state(session, response)
            return response

        if action == "retry_refund":
            response = flows.handle_retry_refund(
                session,
                (action_payload or {}).get("transaction_id", ""),
            )

            sm.finalize_workflow_state(session, response)
            return response

        # --------------------------------------------------
        # 2. Session recall
        # --------------------------------------------------
        recall = sm.try_session_recall(text, session)

        if recall:
            return recall

        # --------------------------------------------------
        # 3. Context follow-up
        # --------------------------------------------------
        follow_up = sm.try_context_follow_up(text, session)

        if follow_up:
            return follow_up

        # --------------------------------------------------
        # 4. Retry refund flow
        # --------------------------------------------------
        if (
            sm.is_retry_refund(text)
            and sm.get_ctx(session, "last_transaction_id")
        ):
            response = flows.handle_payment(text, session)

            sm.finalize_workflow_state(session, response)
            return response

        # --------------------------------------------------
        # 5. Continue active workflow
        # --------------------------------------------------
        if sm.has_active_workflow(session):

            if sm.resolve_active_intent(text, session):

                intent = Intent(session["intent"])

                handler = WORKFLOW_HANDLERS.get(intent)

                if handler:
                    response = handler(text, session)

                    sm.finalize_workflow_state(session, response)

                    return response

        # --------------------------------------------------
        # 6. Text initiate return
        # --------------------------------------------------
        if (
            sm.is_initiate_return(text)
            and sm.get_ctx(session, "last_order_id")
            and (
                session.get("step") == "awaiting_confirmation"
                or session.get("intent") == Intent.RETURN_REFUND.value
            )
        ):

            response = flows.handle_initiate_return(
                session,
                sm.get_ctx(session, "last_order_id"),
            )

            sm.finalize_workflow_state(session, response)

            return response

        # --------------------------------------------------
        # 7. Classify new intent
        # --------------------------------------------------
        intent = classify_intent(text)

        if intent != Intent.UNKNOWN:
            session["failed_attempts"] = 0

        # --------------------------------------------------
        # 8. Irrelevant intent
        # --------------------------------------------------
        if intent == Intent.IRRELEVANT:
            sm.clear_workflow(session, keep_context=True)

            return flows.handle_irrelevant(session)

        # --------------------------------------------------
        # 9. Escalation
        # --------------------------------------------------
        if intent == Intent.ESCALATION:

            response = flows.handle_escalation(text, session)

            sm.finalize_workflow_state(session, response)

            return response

        session["intent"] = intent.value

        # --------------------------------------------------
        # 10. Gemini recommendations
        # --------------------------------------------------
        if intent == Intent.RECOMMENDATION:

            max_price = extract_price_limit(text) or 2000

            response_text = await get_product_recommendations(
                text,
                max_price,
            )

            sm.clear_workflow(session, keep_context=True)

            return ChatResponse(
                message=response_text,
                intent=Intent.RECOMMENDATION,
                resolution_type=ResolutionType.GEMINI,
                session_id=session["session_id"],
            )

        # --------------------------------------------------
        # 11. Deterministic handlers
        # --------------------------------------------------
        handler = WORKFLOW_HANDLERS.get(intent)

        if handler:

            response = handler(text, session)

            sm.finalize_workflow_state(session, response)

            return response

        # --------------------------------------------------
        # 12. Unknown handling
        # --------------------------------------------------
        if sm.has_active_workflow():

            sm.increment_failed(session)

            if session.get("failed_attempts", 0) >= 3:

                response = flows.handle_escalation(text, session)

                sm.finalize_workflow_state(session, response)

                return response

        # --------------------------------------------------
        # 13. Fallback
        # --------------------------------------------------
        session["step"] = None
        session["intent"] = None

        return ChatResponse(
            message=(
                "I'm not sure I understood that. I can help with:\n"
                "• Order tracking\n"
                "• Cashback issues\n"
                "• Coupon problems\n"
                "• Payment issues\n"
                "• Returns & refunds\n"
                "• Account/login help\n"
                "• Product recommendations\n\n"
                "What would you like help with?"
            ),
            intent=Intent.UNKNOWN,
            resolution_type=ResolutionType.INTERNAL,
            session_id=session["session_id"],
        )


decision_engine = DecisionEngine()