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

    question_words = normalized.split()
    for term in SENSITIVE_TERMS:
        term_words = term.split()
        # Check if all term words appear as prefixes of any question word
        if all(
            any(tw == qw or qw.startswith(tw) for qw in question_words)
            for tw in term_words
        ):
            return Route.TICKET

    return Route.ANSWER
