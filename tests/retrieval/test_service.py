from app.retrieval.service import rank_by_token_overlap


def test_expense_question_ranks_expense_chunk_first() -> None:
    ranked = rank_by_token_overlap(
        "When should I submit a receipt?",
        [
            "Reset VPN password via IT.",
            "Submit receipts within 30 days.",
        ],
    )
    assert ranked[0] == "Submit receipts within 30 days."
