from app.retrieval.bm25 import bm25_rank, tokenize_chinese


def test_tokenize_chinese_keeps_exact_terms_and_numbers() -> None:
    assert "30" in tokenize_chinese("报销应在 30 天内提交")
    assert "报销" in tokenize_chinese("报销应在 30 天内提交")


def test_bm25_rank_prefers_exact_chinese_policy_clause() -> None:
    ranked = bm25_rank(
        "报销 30 天内提交",
        ["VPN 密码重置需提交工单", "差旅报销必须在费用发生后 30 天内提交"],
    )
    assert ranked == [1, 0]


def test_bm25_rank_handles_empty_documents() -> None:
    assert bm25_rank("报销", ["", ""]) == [0, 1]
