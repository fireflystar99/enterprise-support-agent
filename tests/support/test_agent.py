from unittest.mock import MagicMock

from app.core.experiment_config import ExperimentConfig, RetrievalConfig
from app.retrieval.service import RetrievalService
from app.retrieval.types import RetrievedChunk
from app.support.agent import SupportAgent


def test_agent_answers_expense_question() -> None:
    """Agent returns answer with citations when retrieval finds chunks."""
    mock_chunks = [
        RetrievedChunk(id="chunk-1", content="Submit receipts within 30 calendar days.", title="expense-policy", section="Submission Deadlines", score=0.95),
    ]
    mock_svc = MagicMock(spec=RetrievalService)
    mock_svc.search.return_value = mock_chunks

    agent = SupportAgent(retrieval_service=mock_svc)
    response = agent.handle("How do I submit a receipt?")

    assert response.route == "answer"
    assert len(response.citations) == 1
    assert response.citations[0].title == "expense-policy"


def test_agent_routes_password_reset_to_ticket() -> None:
    """Sensitive question routes to ticket even when evidence exists."""
    mock_svc = MagicMock(spec=RetrievalService)
    mock_svc.search.return_value = [
        RetrievedChunk(id="chunk-1", content="VPN password resets require IT.", title="vpn-faq", section="Password Reset", score=0.95),
    ]
    agent = SupportAgent(retrieval_service=mock_svc)
    response = agent.handle("Please reset my VPN password")

    assert response.route == "ticket"
    assert response.ticket_id is not None
    assert response.citations == []


def test_agent_routes_unknown_to_ticket() -> None:
    """No evidence → ticket even for non-sensitive question."""
    mock_svc = MagicMock(spec=RetrievalService)
    mock_svc.search.return_value = []

    agent = SupportAgent(retrieval_service=mock_svc)
    response = agent.handle("What is the meaning of life?")

    assert response.route == "ticket"
    assert response.ticket_id is not None


def test_agent_uses_rerank_settings_from_experiment_config() -> None:
    mock_svc = MagicMock(spec=RetrievalService)
    mock_svc.hybrid_search.return_value = [
        RetrievedChunk(
            id="chunk-1",
            content="差旅报销须在 30 天内提交。",
            title="差旅报销政策",
            section="提交时限",
            score=0.95,
        ),
    ]
    config = ExperimentConfig(
        version="v4-rerank",
        retrieval=RetrievalConfig(
            mode="three_stage", top_k=3, rerank=True, rerank_top_n=6
        ),
    )

    SupportAgent(retrieval_service=mock_svc).handle("如何提交差旅报销？", config=config)

    mock_svc.hybrid_search.assert_called_once_with(
        "如何提交差旅报销？",
        department=None,
        limit=3,
        rerank=True,
        rerank_top_n=6,
    )
