from app.support.grounding import validate_grounding


def test_ungrounded_answer_fails() -> None:
    assert validate_grounding(
        answer="The sky is blue.",
        citations=[],
    ) is False


def test_grounded_answer_passes() -> None:
    assert validate_grounding(
        answer="Submit receipts within 30 days [1].",
        citations=["1"],
    ) is True


def test_empty_answer_fails_grounding() -> None:
    assert validate_grounding(
        answer="",
        citations=[],
    ) is False


def test_answer_with_citations_but_no_marker_fails() -> None:
    assert validate_grounding(
        answer="Submit receipts within 30 days.",
        citations=["1"],
    ) is False
