"""
API-level conftest: imports FastAPI app and provides client fixture.
Heaviest conftest — only loaded for tests under tests/api/ and tests/support/test_agent.py.
"""
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class _FakeEncoding:
    def __init__(self, data):
        self._data = data

    def tolist(self):
        return self._data


def _make_mock_chunk(id="c1", content="Submit receipts within 30 calendar days.", title="expense-policy", section="Submission Deadlines"):
    chunk = MagicMock()
    chunk.id = id
    chunk.content = content
    chunk.title = title
    chunk.section = section
    chunk.department = "General"
    chunk.access_level = "public"
    return chunk


@pytest.fixture(autouse=True)
def _mock_deps(monkeypatch) -> Generator[None, None, None]:
    """Mock heavy dependencies so tests run without network or database."""
    from app.core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "admin_token", "test-admin-token")
    monkeypatch.setattr(app_settings, "app_env", "development")

    fake_model = MagicMock()
    fake_model.encode = MagicMock(return_value=_FakeEncoding([[0.0] * 1024]))

    fake_reranker = MagicMock()
    fake_reranker.predict = MagicMock(return_value=[0.0])

    mock_chunk = _make_mock_chunk()
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    mock_query = MagicMock()
    mock_query.order_by.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [mock_chunk]
    mock_query.first.return_value = None  # trace GET → not found → 404
    mock_session.query.return_value = mock_query

    with (
        patch("sentence_transformers.SentenceTransformer", return_value=fake_model),
        patch("sentence_transformers.CrossEncoder", return_value=fake_reranker),
        patch("app.db.session.SessionLocal", return_value=mock_session),
        # Module-level aliases imported before patch takes effect
        patch("app.support.agent.SessionLocal", return_value=mock_session),
        patch("app.api.main.SessionLocal", return_value=mock_session),
        # support/conftest disables _persist_trace for unit tests, but
        # API tests route through app so we need the full agent untouched
    ):
        yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    from app.api.main import app
    with TestClient(app) as c:
        yield c
