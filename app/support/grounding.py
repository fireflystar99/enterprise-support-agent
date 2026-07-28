import re


def validate_grounding(answer: str, citations: list[str]) -> bool:
    """Check that factual answer has at least one citation reference."""
    if not answer.strip():
        return True
    if not citations:
        return False
    has_citation_marker = bool(re.search(r'\[\d+\]|\[source-\d+\]', answer))
    return has_citation_marker


def filter_by_access_level(chunks: list, user_access: str) -> list:
    """Filter chunks by minimum access level."""
    access_order = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
    user_level = access_order.get(user_access, 0)
    return [
        c for c in chunks
        if access_order.get(c.access_level, 0) <= user_level
    ]
