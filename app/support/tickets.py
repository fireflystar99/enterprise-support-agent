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
    """Ticket creation with in-memory cache and optional database persistence."""

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

        try:
            from app.db.models import Ticket as TicketModel
            from app.db.session import SessionLocal
            session = SessionLocal()
            db_ticket = TicketModel(
                id=ticket_id,
                question=question,
                reason=reason,
                risk_level=risk_level,
                status="open",
            )
            session.add(db_ticket)
            session.commit()
            session.close()
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("Ticket DB persist failed: %s", exc)

        return record

    def get(self, ticket_id: str) -> TicketRecord | None:
        if ticket_id in self._store:
            return self._store[ticket_id]
        try:
            from app.db.models import Ticket as TicketModel
            from app.db.session import SessionLocal
            session = SessionLocal()
            row = session.query(TicketModel).filter(TicketModel.id == ticket_id).first()
            session.close()
            if row:
                record = TicketRecord(
                    id=str(row.id),
                    question=row.question,
                    reason=row.reason or "",
                    risk_level=row.risk_level,
                    status=row.status,
                    created_at=row.created_at,
                )
                self._store[ticket_id] = record
                return record
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("Ticket DB lookup failed: %s", exc)
        return None


ticket_service = TicketService()
