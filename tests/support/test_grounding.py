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
