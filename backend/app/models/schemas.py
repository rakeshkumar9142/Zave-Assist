from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Intent(str, Enum):
    ORDER_TRACKING = "order_tracking"
    CASHBACK = "cashback"
    COUPON = "coupon"
    PAYMENT = "payment"
    RETURN_REFUND = "return_refund"
    ACCOUNT = "account"
    RECOMMENDATION = "recommendation"
    IRRELEVANT = "irrelevant"
    GREETING = "greeting"
    ESCALATION = "escalation"
    UNKNOWN = "unknown"


class ResolutionType(str, Enum):
    INTERNAL = "internal"
    GEMINI = "gemini"
    ESCALATED = "escalated"
    BLOCKED = "blocked"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChatAction(BaseModel):
    label: str
    action: str
    payload: Optional[dict[str, Any]] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    message: str
    session_id: str
    user_id: Optional[str] = "guest"
    user_email: Optional[str] = None
    context: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    message: str
    intent: Intent
    resolution_type: ResolutionType
    actions: list[ChatAction] = []
    session_id: str
    awaiting_input: Optional[str] = None
    ticket_id: Optional[str] = None


class TicketCreate(BaseModel):
    user_id: str
    email: Optional[str] = None
    order_id: Optional[str] = None
    transcript: list[dict[str, Any]]
    reason: str
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketResponse(BaseModel):
    id: str
    user_id: str
    email: Optional[str]
    order_id: Optional[str]
    reason: str
    priority: TicketPriority
    status: str
    created_at: datetime


class DashboardStats(BaseModel):
    total_queries: int
    resolved_internal: int
    resolved_gemini: int
    escalated: int
    open_tickets: int
    avg_resolution_time_seconds: float
    blocked_irrelevant: int
    estimated_token_savings: int
    customer_satisfaction_score: float
