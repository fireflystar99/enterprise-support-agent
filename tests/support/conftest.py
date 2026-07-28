"""Test fixtures for support agent unit tests — disable DB persistence entirely."""
from unittest.mock import MagicMock

import pytest

from app.support.agent import SupportAgent


@pytest.fixture(autouse=True)
def disable_persistence(monkeypatch):
    """Prevent agent handle() and ticket_service from touching real PostgreSQL."""
    monkeypatch.setattr(SupportAgent, "_persist_trace", lambda *_: None)

    fake_ticket_svc = MagicMock()
    fake_ticket_svc.create.return_value.model_dump.return_value = {"id": "ticket-test-1"}
    fake_ticket_svc.create.return_value.id = "ticket-test-1"
    monkeypatch.setattr("app.support.agent.ticket_service", fake_ticket_svc)
