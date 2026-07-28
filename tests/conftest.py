"""Shared test fixtures."""
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.main import app


class _FakeEncoding:
    """Mimics a numpy array so .tolist() works on mocked encode() result."""
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
def _mock_deps() -> Generator[None, None, None]:
    """Mock heavy dependencies so tests run without network or database."""
    fake_model = MagicMock()
    fake_model.encode = MagicMock(return_value=_FakeEncoding([[0.0] * 1024]))

    mock_chunk = _make_mock_chunk()
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    mock_query = MagicMock()
    mock_query.order_by.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [mock_chunk]
    mock_session.query.return_value = mock_query

    with (
        patch("sentence_transformers.SentenceTransformer", return_value=fake_model),
        patch("app.db.session.SessionLocal", return_value=mock_session),
    ):
        yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
