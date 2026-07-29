from app.retrieval.service import RetrievalService, rank_by_token_overlap


def test_expense_question_ranks_expense_chunk_first() -> None:
    ranked = rank_by_token_overlap(
        "When should I submit a receipt?",
        [
            "Reset VPN password via IT.",
            "Submit receipts within 30 days.",
        ],
    )
    assert ranked[0] == "Submit receipts within 30 days."


def test_retrieval_exposes_stage_timings() -> None:
    assert set(RetrievalService().last_timings) == {
        "embedding_ms",
        "vector_search_ms",
        "text_search_ms",
        "fusion_ms",
    }
