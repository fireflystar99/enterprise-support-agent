"""Shared test fixtures."""
from typing import Generator
from fastapi.testclient import TestClient
import pytest
from app.api.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
