from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError


def test_ticket_status_update_accepts_supported_status() -> None:
    from app.api.schemas import TicketStatusUpdateRequest

    assert TicketStatusUpdateRequest(status="in_progress").status == "in_progress"


def test_ticket_status_update_rejects_unknown_status() -> None:
    from app.api.schemas import TicketStatusUpdateRequest

    with pytest.raises(ValidationError):
        TicketStatusUpdateRequest(status="closed")


def test_ticket_list_requires_admin_token(client) -> None:
    response = client.get("/tickets")

    assert response.status_code == 403


def test_ticket_list_returns_records_with_admin_token(client, monkeypatch) -> None:
    from app.api.main import ticket_service
    from app.support.tickets import TicketRecord

    record = TicketRecord(
        id="ticket-1",
        question="请帮我重置 VPN 密码",
        reason="密码重置需人工核验",
        risk_level="high",
        status="open",
        created_at=datetime(2026, 7, 29, tzinfo=UTC),
    )
    monkeypatch.setattr(ticket_service, "list", lambda status=None, risk_level=None: [record])

    response = client.get("/tickets", headers={"X-Admin-Token": "test-admin-token"})

    assert response.status_code == 200
    assert response.json()[0]["id"] == "ticket-1"


def test_ticket_status_update_rejects_unknown_ticket(client, monkeypatch) -> None:
    from app.api.main import ticket_service

    monkeypatch.setattr(ticket_service, "update_status", lambda ticket_id, status: None)

    response = client.patch(
        "/tickets/missing-ticket",
        headers={"X-Admin-Token": "test-admin-token"},
        json={"status": "resolved"},
    )

    assert response.status_code == 404


def test_ticket_list_returns_service_unavailable_when_database_fails(
    client, monkeypatch
) -> None:
    from app.api.main import ticket_service
    from app.support.tickets import TicketDatabaseError

    def fail_list(status=None, risk_level=None):
        raise TicketDatabaseError("database unavailable")

    monkeypatch.setattr(ticket_service, "list", fail_list)

    response = client.get("/tickets", headers={"X-Admin-Token": "test-admin-token"})

    assert response.status_code == 503


def test_ticket_status_update_returns_service_unavailable_when_database_fails(
    client, monkeypatch
) -> None:
    from app.api.main import ticket_service
    from app.support.tickets import TicketDatabaseError

    def fail_update(ticket_id, status):
        raise TicketDatabaseError("database unavailable")

    monkeypatch.setattr(ticket_service, "update_status", fail_update)

    response = client.patch(
        "/tickets/ticket-1",
        headers={"X-Admin-Token": "test-admin-token"},
        json={"status": "resolved"},
    )

    assert response.status_code == 503


def test_ticket_service_lists_database_records_with_filters(monkeypatch) -> None:
    from app.support.tickets import TicketService

    row = MagicMock(
        id="ticket-1",
        question="请帮我重置 VPN 密码",
        reason="密码重置需人工核验",
        risk_level="high",
        status="open",
        created_at=datetime(2026, 7, 29, tzinfo=UTC),
    )
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.all.return_value = [row]
    session = MagicMock()
    session.query.return_value = query
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: session)

    records = TicketService().list(status="open", risk_level="high")

    assert [record.id for record in records] == ["ticket-1"]
    assert query.filter.call_count == 2
    query.order_by.assert_called_once()
    session.close.assert_called_once()


def test_ticket_service_persists_status_and_updates_cache(monkeypatch) -> None:
    from app.support.tickets import TicketService

    row = MagicMock(
        id="ticket-1",
        question="请帮我重置 VPN 密码",
        reason="密码重置需人工核验",
        risk_level="high",
        status="open",
        created_at=datetime(2026, 7, 29, tzinfo=UTC),
    )
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = row
    session = MagicMock()
    session.query.return_value = query
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: session)

    record = TicketService().update_status("ticket-1", "resolved")

    assert record is not None
    assert record.status == "resolved"
    assert row.status == "resolved"
    session.commit.assert_called_once()
    session.close.assert_called_once()


def test_ticket_service_raises_database_error_instead_of_empty_list(monkeypatch) -> None:
    from app.support.tickets import TicketDatabaseError, TicketService

    def fail_session():
        raise RuntimeError("connection timeout")

    monkeypatch.setattr("app.db.session.SessionLocal", fail_session)

    with pytest.raises(TicketDatabaseError, match="list"):
        TicketService().list()
