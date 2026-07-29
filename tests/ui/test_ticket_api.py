from unittest.mock import MagicMock


def test_fetch_tickets_sends_admin_token_and_filters(monkeypatch) -> None:
    from app.ui.ticket_api import fetch_tickets

    response = MagicMock()
    response.json.return_value = []
    get = MagicMock(return_value=response)
    monkeypatch.setattr("httpx.get", get)

    assert fetch_tickets("http://localhost:8000/", "admin-token", "open", "high") == []

    get.assert_called_once_with(
        "http://localhost:8000/tickets",
        headers={"X-Admin-Token": "admin-token"},
        params={"status": "open", "risk_level": "high"},
        timeout=10,
    )
    response.raise_for_status.assert_called_once()


def test_update_ticket_status_uses_patch_request(monkeypatch) -> None:
    from app.ui.ticket_api import update_ticket_status

    response = MagicMock()
    response.json.return_value = {"id": "ticket-1", "status": "resolved"}
    patch = MagicMock(return_value=response)
    monkeypatch.setattr("httpx.patch", patch)

    result = update_ticket_status(
        "http://localhost:8000", "admin-token", "ticket-1", "resolved"
    )

    assert result["status"] == "resolved"
    patch.assert_called_once_with(
        "http://localhost:8000/tickets/ticket-1",
        headers={"X-Admin-Token": "admin-token"},
        json={"status": "resolved"},
        timeout=10,
    )
