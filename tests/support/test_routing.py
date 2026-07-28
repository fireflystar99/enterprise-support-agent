from app.support.routing import Route, decide_route


def test_sensitive_request_requires_ticket() -> None:
    assert decide_route("Please reset my VPN password", evidence_count=3) is Route.TICKET


def test_missing_evidence_requires_ticket() -> None:
    assert decide_route("What is the moon made of?", evidence_count=0) is Route.TICKET


def test_supported_question_can_be_answered() -> None:
    assert decide_route("How do I submit an expense?", evidence_count=2) is Route.ANSWER
