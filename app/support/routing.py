from enum import StrEnum


class Route(StrEnum):
    ANSWER = "answer"
    TICKET = "ticket"


SENSITIVE_TERMS = (
    "reset my password",
    "reset password",
    "change permission",
    "grant access",
    "personal data",
)


def decide_route(question: str, evidence_count: int) -> Route:
    normalized = question.lower()
    if evidence_count == 0:
        return Route.TICKET

    question_words = set(normalized.split())
    for term in SENSITIVE_TERMS:
        term_words = term.split()
        if all(tw in question_words for tw in term_words):
            return Route.TICKET

    return Route.ANSWER
