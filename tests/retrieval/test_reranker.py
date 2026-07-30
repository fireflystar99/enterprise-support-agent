from app.retrieval.reranker import rerank_candidates
from app.retrieval.types import RetrievedChunk


def test_rerank_candidates_orders_chunks_by_model_score(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.retrieval.reranker._get_reranker",
        lambda: type("Model", (), {"predict": lambda self, pairs: [0.1, 0.9]})(),
    )
    chunks = [
        RetrievedChunk("a", "VPN password", "VPN", "", 0.1),
        RetrievedChunk("b", "Expense reimbursement is due in 30 days", "Expenses", "", 0.1),
    ]

    reranked = rerank_candidates("What is the expense deadline?", chunks)

    assert [chunk.id for chunk in reranked] == ["b", "a"]
    assert [chunk.score for chunk in reranked] == [0.9, 0.1]


def test_rerank_candidates_returns_empty_list_without_loading_model(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.retrieval.reranker._get_reranker",
        lambda: (_ for _ in ()).throw(AssertionError("model should not load")),
    )

    assert rerank_candidates("question", []) == []
