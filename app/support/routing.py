from enum import StrEnum


class Route(StrEnum):
    ANSWER = "answer"
    TICKET = "ticket"


SENSITIVE_PATTERNS: list[str] = [
    # password / credentials
    r"\breset\b.*\bpassword\b", r"\bchange\b.*\bpassword\b", r"\bforgot\b.*\bpassword\b",
    r"\bnew\b.*\bpassword\b", r"\bcredential\b",
    # permission / access escalation
    r"\bchange\b.*\bpermission\b", r"\bgrant\b.*\baccess\b", r"\bgrant\b.*\bme\b",
    r"\badmin\b.*\baccess\b", r"\blevel\s*[34]\b", r"\bproduction\b.*\baccess\b",
    r"\bproduction\b.*\bsystem\b", r"\bupgrade\b.*\baccess\b", r"\belevate\b.*\b(my|access)\b",
    r"\bescalat\w*\b.*\bprivilege\b", r"\broot\b.*\baccess\b", r"\bpromot\w*\b.*\baccess\b",
    # role / account changes
    r"\bchange\b.*\brole\b", r"\bdelete\b.*\baccount\b", r"\bdisable\b.*\bmfa\b",
    r"\bbypass\b.*\bapprov\w*\b", r"\boverride\b",
    # data privacy / security
    r"\bpersonal\b.*\bdata\b", r"\bleak\w*\b", r"\bdata\b.*\bbreach\b", r"\bPII\b",
    r"\bprivacy\b.*\bviolation\b", r"\bexpose\w*\b.*\bdata\b",
    # system / infra changes
    r"\bshut\s*down\b", r"\breboot\b.*\bserver\b", r"\brestart\b.*\bservice\b",
    r"\bdelete\b.*\bdatabase\b", r"\bdrop\b.*\btable\b",
]

import re


def calculate_risk_score(question: str) -> int:
    """Return count of matched sensitive patterns (0 = safe)."""
    normalized = question.lower()
    matches = 0
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, normalized):
            matches += 1
    return matches


def decide_route(question: str, evidence_count: int) -> Route:
    """Route to TICKET when evidence is missing or question is sensitive."""
    if evidence_count == 0:
        return Route.TICKET
    if calculate_risk_score(question) > 0:
        return Route.TICKET
    return Route.ANSWER
