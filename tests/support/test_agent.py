from unittest.mock import MagicMock

import app.support.agent as agent_module
from app.core.experiment_config import (
    ExperimentConfig,
    GroundingConfig,
    RetrievalConfig,
)
from app.llm.deepseek import DeepSeekError
from app.retrieval.service import RetrievalService
from app.retrieval.types import RetrievedChunk
from app.support.agent import SupportAgent


def test_agent_answers_expense_question(monkeypatch) -> None:
    """Agent returns answer with citations when retrieval finds chunks."""
    mock_chunks = [
        RetrievedChunk(id="chunk-1", content="Submit receipts within 30 calendar days.", title="expense-policy", section="Submission Deadlines", score=0.95),
    ]
    mock_svc = MagicMock(spec=RetrievalService)
    mock_svc.search.return_value = mock_chunks
    monkeypatch.setattr(
        agent_module,
        "generate_answer",
        lambda *_args: "Submit receipts within 30 calendar days. [1]",
        raising=False,
    )

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


def test_agent_uses_deepseek_only_after_safe_retrieval(monkeypatch) -> None:
    chunks = [
        RetrievedChunk(
            id="chunk-1",
            content="报销须在 30 天内提交。[1]",
            title="差旅政策",
            section="提交时限",
            score=0.95,
        ),
    ]
    service = MagicMock(spec=RetrievalService)
    service.search.return_value = chunks
    monkeypatch.setattr(
        agent_module,
        "generate_answer",
        lambda *_args: "请在 30 天内提交。[1]",
        raising=False,
    )

    response = SupportAgent(retrieval_service=service).handle("如何报销？")

    assert response.route == "answer"
    assert response.answer == "请在 30 天内提交。[1]"


def test_sensitive_question_never_calls_deepseek(monkeypatch) -> None:
    service = MagicMock(spec=RetrievalService)
    service.search.return_value = [
        RetrievedChunk(
            id="chunk-1",
            content="VPN 密码由 IT 支持处理。",
            title="VPN 常见问题",
            section="密码重置",
            score=0.95,
        ),
    ]
    llm = MagicMock()
    monkeypatch.setattr(agent_module, "generate_answer", llm, raising=False)

    response = SupportAgent(retrieval_service=service).handle("请重置 VPN 密码")

    assert response.route == "ticket"
    llm.assert_not_called()


def test_deepseek_failure_routes_to_ticket(monkeypatch) -> None:
    service = MagicMock(spec=RetrievalService)
    service.search.return_value = [
        RetrievedChunk(
            id="chunk-1",
            content="报销须在 30 天内提交。",
            title="差旅政策",
            section="提交时限",
            score=0.95,
        ),
    ]

    def raise_deepseek_error(*_args):
        raise DeepSeekError("offline")

    monkeypatch.setattr(
        agent_module, "generate_answer", raise_deepseek_error, raising=False
    )

    response = SupportAgent(retrieval_service=service).handle("如何报销？")

    assert response.route == "ticket"
    assert response.ticket_id is not None


def test_uncited_deepseek_answer_routes_to_ticket(monkeypatch) -> None:
    service = MagicMock(spec=RetrievalService)
    service.search.return_value = [
        RetrievedChunk(
            id="chunk-1",
            content="报销须在 30 天内提交。",
            title="差旅政策",
            section="提交时限",
            score=0.95,
        ),
    ]
    config = ExperimentConfig(
        version="test",
        grounding=GroundingConfig(enabled=True, mandatory_citations=True),
    )
    monkeypatch.setattr(
        agent_module, "generate_answer", lambda *_args: "请在 30 天内提交。", raising=False
    )

    response = SupportAgent(retrieval_service=service).handle("如何报销？", config=config)

    assert response.route == "ticket"


def test_stream_with_out_of_range_citation_routes_to_ticket(monkeypatch) -> None:
    service = MagicMock(spec=RetrievalService)
    service.search.return_value = [
        RetrievedChunk(
            id="chunk-1",
            content="报销须在 30 天内提交。",
            title="差旅政策",
            section="提交时限",
            score=0.95,
        ),
    ]
    config = ExperimentConfig(
        version="test",
        grounding=GroundingConfig(enabled=True, mandatory_citations=True),
    )
    monkeypatch.setattr(
        agent_module,
        "stream_answer",
        lambda *_args: iter(["请在 30 天内提交。 [999]"]),
    )

    events = list(SupportAgent(retrieval_service=service).stream("如何报销？", config=config))

    assert [event for event, _ in events] == ["metadata"]
    assert events[0][1]["route"] == "ticket"


def test_stream_interruption_creates_ticket_and_final_metadata(monkeypatch) -> None:
    service = MagicMock(spec=RetrievalService)
    service.search.return_value = [
        RetrievedChunk(
            id="chunk-1",
            content="报销须在 30 天内提交。",
            title="差旅政策",
            section="提交时限",
            score=0.95,
        ),
    ]
    config = ExperimentConfig(
        version="test",
        grounding=GroundingConfig(enabled=True, mandatory_citations=True),
    )

    def interrupted_stream(*_args):
        yield "请在 30 天内提交。 [1]"
        raise DeepSeekError("offline")

    monkeypatch.setattr(agent_module, "stream_answer", interrupted_stream)

    events = list(SupportAgent(retrieval_service=service).stream("如何报销？", config=config))

    assert events[-1][0] == "metadata"
    assert events[-1][1]["route"] == "ticket"


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


def test_agent_citation_includes_pdf_page_and_table(monkeypatch) -> None:
    service = MagicMock(spec=RetrievalService)
    service.search.return_value = [RetrievedChunk(
        id="chunk-1", content="| 职级 | 上限 |\n| --- | --- |\n| P4 | 800 元 |",
        title="travel-policy", section="第 3 页", score=0.95,
        source_type="pdf", source_path="data/documents/travel-policy.pdf",
        page_number=3, content_type="table", table_name="表格 1",
    )]
    monkeypatch.setattr(agent_module, "generate_answer", lambda *_: "P4 的上限为 800 元。[1]", raising=False)

    response = SupportAgent(retrieval_service=service).handle("P4 住宿上限是多少？")

    assert response.route == "answer"
    assert response.citations[0].location == "第 3 页，表格 1"
