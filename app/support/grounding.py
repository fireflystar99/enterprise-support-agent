import re

from app.retrieval.types import RetrievedChunk


def validate_grounding(answer: str, citations: list[str]) -> bool:
    """Return True only when the answer has content AND at least one citation reference."""
    if not answer.strip():
        return False
    if not citations:
        return False
    has_citation_marker = bool(re.search(r'\[\d+\]|\[source-\d+\]', answer))
    return has_citation_marker


def filter_by_access_level(chunks: list[RetrievedChunk], user_access: str) -> list[RetrievedChunk]:
    """Filter chunks by minimum access level."""
    access_order = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
    user_level = access_order.get(user_access, 0)
    return [
        c for c in chunks
        if access_order.get(c.access_level, 0) <= user_level
    ]


def resolve_access_level(department: str | None) -> str:
    """Map a department to a minimum access level for filtering."""
    if department in ("Finance", "IT", "HR"):
        return "internal"
    if department in ("Legal", "Executive"):
        return "confidential"
    return "public"
