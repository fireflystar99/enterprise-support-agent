import pytest

from app.support.routing import Route, calculate_risk_score, decide_route

# --- basic tests ---

def test_sensitive_request_requires_ticket() -> None:
    assert decide_route("Please reset my VPN password", evidence_count=3) is Route.TICKET


def test_missing_evidence_requires_ticket() -> None:
    assert decide_route("What is the moon made of?", evidence_count=0) is Route.TICKET


def test_supported_question_can_be_answered() -> None:
    assert decide_route("How do I submit an expense?", evidence_count=2) is Route.ANSWER


# --- adversarial / expanded coverage ---

SENSITIVE_VARIANTS = [
    "Grant me Level 4 VPN access",
    "I need production access for the database",
    "Please change permission to admin level",
    "My personal data was leaked in a breach",
    "Can you elevate my access to root?",
    "I want to upgrade my VPN access to level 3",
    "Promote me to admin access please",
    "Delete my account immediately",
    "I need to bypass approval for this expense",
    "How do I disable MFA on my account?",
    "Please change my password to something new",
    "I forgot my password, can you help?",
    "Can you escalate my privilege to access production systems?",
    "There was a PII data leak from my department",
    "Shut down the production server",
]


@pytest.mark.parametrize("question", SENSITIVE_VARIANTS)
def test_sensitive_variants_route_to_ticket(question: str) -> None:
    assert decide_route(question, evidence_count=3) is Route.TICKET, f"Expected TICKET for: {question}"


def test_innocent_question_still_answers() -> None:
    assert decide_route("What VPN clients are supported?", evidence_count=3) is Route.ANSWER


def test_calculate_risk_multi_match() -> None:
    score = calculate_risk_score("Reset my password and grant me admin access!")
    assert score >= 2


def test_calculate_risk_zero() -> None:
    score = calculate_risk_score("How do I submit a receipt?")
    assert score == 0
