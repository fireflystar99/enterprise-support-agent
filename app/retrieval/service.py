from typing import List
from app.retrieval.types import RetrievedChunk


def rank_by_token_overlap(question: str, candidates: List[str]) -> List[str]:
    """Rank candidate texts by token overlap with the question (deterministic test helper)."""
    question_tokens = set(question.lower().split())
    scored = []
    for text in candidates:
        text_tokens = set(text.lower().split())
        overlap = len(question_tokens & text_tokens)
        scored.append((text, overlap))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [text for text, _ in scored if _ > 0] + [text for text, _ in scored if _ == 0]


class RetrievalService:
    """V1: token-overlap ranking. V2 will swap internals without changing the signature."""

    def search(self, question: str, department: str | None = None, limit: int = 3) -> List[RetrievedChunk]:
        tokens = question.lower().split()
        _ = tokens  # placeholder for future use
        return []
