import uuid
from datetime import UTC, datetime

from pydantic import BaseModel


class TicketDatabaseError(RuntimeError):
    """Raised when ticket persistence is unavailable."""


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

    @staticmethod
    def _to_record(row: object) -> TicketRecord:
        return TicketRecord(
            id=str(row.id),
            question=row.question,
            reason=row.reason or "",
            risk_level=row.risk_level,
            status=row.status,
            created_at=row.created_at,
        )

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
                record = self._to_record(row)
                self._store[ticket_id] = record
                return record
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("Ticket DB lookup failed: %s", exc)
            raise TicketDatabaseError("Ticket database lookup failed") from exc
        return None

    def list(
        self, status: str | None = None, risk_level: str | None = None
    ) -> list[TicketRecord]:
        """Return persisted tickets in reverse creation order."""
        try:
            from app.db.models import Ticket as TicketModel
            from app.db.session import SessionLocal

            session = SessionLocal()
            try:
                query = session.query(TicketModel)
                if status is not None:
                    query = query.filter(TicketModel.status == status)
                if risk_level is not None:
                    query = query.filter(TicketModel.risk_level == risk_level)
                records = [
                    self._to_record(row)
                    for row in query.order_by(TicketModel.created_at.desc()).all()
                ]
                self._store.update({record.id: record for record in records})
                return records
            finally:
                session.close()
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("Ticket DB list failed: %s", exc)
            raise TicketDatabaseError("Ticket database list failed") from exc

    def update_status(self, ticket_id: str, status: str) -> TicketRecord | None:
        """Persist a ticket status change and refresh the in-memory cache."""
        try:
            from app.db.models import Ticket as TicketModel
            from app.db.session import SessionLocal

            session = SessionLocal()
            try:
                row = session.query(TicketModel).filter(TicketModel.id == ticket_id).first()
                if row is None:
                    return None
                row.status = status
                session.commit()
                record = self._to_record(row)
                self._store[ticket_id] = record
                return record
            finally:
                session.close()
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("Ticket DB update failed: %s", exc)
            raise TicketDatabaseError("Ticket database update failed") from exc


ticket_service = TicketService()
