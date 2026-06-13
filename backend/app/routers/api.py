import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import db
from app.models.schemas import ChatRequest, ChatResponse, DashboardStats, TicketResponse
from app.services.decision_engine import decision_engine

router = APIRouter(prefix="/api", tags=["chat"])


class ActionRequest(BaseModel):
    session_id: str
    action: str
    payload: dict | None = None
    user_id: str = "guest"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    start = time.time()
    session = db.get_session(request.session_id)
    session["session_id"] = request.session_id
    session["user_id"] = request.user_id or "guest"
    if request.user_email:
        session.setdefault("context", {})["email"] = request.user_email
    if request.context:
        session.setdefault("context", {}).update(request.context)

    db.add_transcript(request.session_id, "user", request.message)

    response = await decision_engine.process(request.message, session)

    db.add_transcript(request.session_id, "assistant", response.message)

    # Persist session state (intent, step, context, failed_attempts)
    db.update_session(
        request.session_id,
        intent=session.get("intent"),
        step=session.get("step"),
        context=session.get("context", {}),
        failed_attempts=session.get("failed_attempts", 0),
        user_id=session.get("user_id"),
    )

    resolution_map = {
        "internal": "internal",
        "gemini": "gemini",
        "escalated": "escalated",
        "blocked": "blocked",
    }
    db.record_resolution(
        resolution_map.get(response.resolution_type.value, "internal"),
        resolution_time=round(time.time() - start, 2),
        tokens_saved=800 if response.resolution_type.value != "gemini" else 0,
    )

    return response


@router.post("/chat/action", response_model=ChatResponse)
async def chat_action(request: ActionRequest) -> ChatResponse:
    session = db.get_session(request.session_id)
    session["session_id"] = request.session_id
    session["user_id"] = request.user_id

    response = await decision_engine.process(
        "",
        session,
        action=request.action,
        action_payload=request.payload,
    )
    db.add_transcript(request.session_id, "assistant", response.message)
    db.update_session(
        request.session_id,
        intent=session.get("intent"),
        step=session.get("step"),
        context=session.get("context", {}),
        failed_attempts=session.get("failed_attempts", 0),
    )
    db.record_resolution("internal")
    return response


@router.get("/admin/stats", response_model=DashboardStats)
async def get_stats() -> DashboardStats:
    stats = db.get_dashboard_stats()
    return DashboardStats(**stats)


@router.get("/admin/tickets", response_model=list[TicketResponse])
async def get_tickets() -> list[TicketResponse]:
    tickets = db.get_open_tickets()
    return [
        TicketResponse(
            id=t["id"],
            user_id=t["user_id"],
            email=t.get("email"),
            order_id=t.get("order_id"),
            reason=t["reason"],
            priority=t["priority"],
            status=t["status"],
            created_at=t["created_at"],
        )
        for t in tickets
    ]


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "zave-assist-api"}
