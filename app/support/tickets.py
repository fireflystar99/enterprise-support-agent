import uuid
from datetime import UTC, datetime

from pydantic import BaseModel


class TicketRecord(BaseModel):
    id: str
    question: str
    reason: str
    risk_level: str
    status: str = "open"
    created_at: datetime


class TicketService:
    """Simulated ticket creation — never modifies any external system."""

    def __init__(self) -> None:
        self._store: dict[str, TicketRecord] = {}

    def create(self, question: str, reason: str = "", risk_level: str = "low") -> TicketRecord:
        ticket_id = str(uuid.uuid4())
        record = TicketRecord(
            id=ticket_id,
            question=question,
            reason=reason,
            risk_level=risk_level,
            status="open",
            created_at=datetime.now(UTC),
        )
        self._store[ticket_id] = record
        return record

    def get(self, ticket_id: str) -> TicketRecord | None:
        return self._store.get(ticket_id)


ticket_service = TicketService()
