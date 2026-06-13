import re
import uuid
from datetime import datetime
from typing import Any, Optional

from app.config import settings
from app.data import seed
from app.models.schemas import TicketPriority

try:
    from appwrite.client import Client
    from appwrite.services.databases import Databases
except ImportError:
    Client = None
    Databases = None


class Database:
    """Unified data access — Appwrite when configured, else in-memory seed data."""

    def __init__(self) -> None:
        self._tickets: list[dict[str, Any]] = []
        self._sessions: dict[str, dict[str, Any]] = {}
        self._analytics: dict[str, int] = {
            "total_queries": 100000,
            "resolved_internal": 0,
            "resolved_gemini": 0,
            "escalated": 0,
            "blocked_irrelevant": 0,
            "gemini_tokens_saved": 0,
            "resolution_times": [],
            "satisfaction_scores": [],
        }
        self._appwrite: Optional[Databases] = None

        if settings.appwrite_configured and Client and Databases:
            client = Client()
            client.set_endpoint(settings.appwrite_endpoint)
            client.set_project(settings.appwrite_project_id)
            client.set_key(settings.appwrite_api_key)
            self._appwrite = Databases(client)

    def get_order(self, order_id: str) -> Optional[dict[str, Any]]:
        order_id = order_id.upper().strip()
        if not re.match(r"^ZV\d{6}$", order_id):
            return None
        return seed.ORDERS.get(order_id)

    def get_cashback(self, *, order_id: Optional[str] = None, email: Optional[str] = None) -> Optional[dict[str, Any]]:
        if order_id:
            order_id = order_id.upper().strip()
            return seed.CASHBACK.get(order_id)
        if email:
            email = email.lower().strip()
            for record in seed.CASHBACK.values():
                if record["email"].lower() == email:
                    return record
        return None

    def get_coupon(self, code: str) -> Optional[dict[str, Any]]:
        return seed.COUPONS.get(code.upper().strip())

    def get_payment(self, transaction_id: str) -> Optional[dict[str, Any]]:
        return seed.PAYMENTS.get(transaction_id.upper().strip())

    def get_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        return seed.USERS.get(email.lower().strip())

    def get_products(self, category: str = "earbuds", max_price: Optional[int] = None) -> list[dict[str, Any]]:
        products = [p for p in seed.PRODUCTS if p["category"] == category]
        if max_price:
            products = [p for p in products if p["price"] <= max_price]
        return sorted(products, key=lambda p: (-p["rating"], p["price"]))

    def get_session(self, session_id: str) -> dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "intent": None,
                "step": None,
                "context": {},
                "failed_attempts": 0,
                "transcript": [],
            }
        return self._sessions[session_id]

    def update_session(self, session_id: str, **kwargs: Any) -> dict[str, Any]:
        session = self.get_session(session_id)
        if "context" in kwargs and isinstance(kwargs["context"], dict):
            session.setdefault("context", {}).update(kwargs["context"])
            kwargs = {k: v for k, v in kwargs.items() if k != "context"}
        session.update(kwargs)
        return session

    def add_transcript(self, session_id: str, role: str, content: str) -> None:
        session = self.get_session(session_id)
        session["transcript"].append(
            {"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()}
        )

    def create_ticket(
        self,
        *,
        user_id: str,
        email: Optional[str],
        order_id: Optional[str],
        transcript: list[dict[str, Any]],
        reason: str,
        priority: TicketPriority,
    ) -> dict[str, Any]:
        ticket = {
            "id": f"TKT-{uuid.uuid4().hex[:8].upper()}",
            "user_id": user_id,
            "email": email,
            "order_id": order_id,
            "transcript": transcript,
            "reason": reason,
            "priority": priority.value,
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._tickets.append(ticket)
        self._analytics["escalated"] += 1
        return ticket

    def get_open_tickets(self) -> list[dict[str, Any]]:
        return [t for t in self._tickets if t["status"] == "open"]

    def record_resolution(
        self,
        resolution_type: str,
        resolution_time: float = 1.2,
        satisfaction: float = 4.5,
        tokens_saved: int = 0,
    ) -> None:
        self._analytics["total_queries"] += 1
        key_map = {
            "internal": "resolved_internal",
            "gemini": "resolved_gemini",
            "escalated": "escalated",
            "blocked": "blocked_irrelevant",
        }
        if key := key_map.get(resolution_type):
            self._analytics[key] += 1
        if tokens_saved:
            self._analytics["gemini_tokens_saved"] += tokens_saved
        self._analytics["resolution_times"].append(resolution_time)
        self._analytics["satisfaction_scores"].append(satisfaction)

    def get_dashboard_stats(self) -> dict[str, Any]:
        times = self._analytics["resolution_times"]
        scores = self._analytics["satisfaction_scores"]
        avg_time = sum(times) / len(times) if times else 2.4
        avg_score = sum(scores) / len(scores) if scores else 4.6

        base = self._analytics["total_queries"]
        internal = self._analytics["resolved_internal"]
        blocked = self._analytics["blocked_irrelevant"]
        # Each non-Gemini query saves ~800 tokens vs full LLM routing
        token_savings = (internal + blocked) * 800 + self._analytics["gemini_tokens_saved"]

        return {
            "total_queries": base,
            "resolved_internal": internal + 87234,  # baseline demo stats
            "resolved_gemini": self._analytics["resolved_gemini"] + 8421,
            "escalated": self._analytics["escalated"] + len(self.get_open_tickets()) + 892,
            "open_tickets": len(self.get_open_tickets()) + 47,
            "avg_resolution_time_seconds": round(avg_time, 1),
            "blocked_irrelevant": blocked + 3453,
            "estimated_token_savings": token_savings + 69840000,
            "customer_satisfaction_score": round(avg_score, 1),
        }


db = Database()
