from app.retrieval.hybrid import reciprocal_rank_fusion


def test_rrf_promotes_item_returned_by_both_retrievers() -> None:
    result = reciprocal_rank_fusion([["a", "b"], ["b", "c"]])
    assert result[0] == "b"
