from app.retrieval.types import RetrievedChunk
from app.retrieval.hybrid import reciprocal_rank_fusion


def rank_by_token_overlap(question: str, candidates: list[str]) -> list[str]:
    """Rank candidate texts by token overlap with the question."""
    question_tokens = set(question.lower().split())
    scored = []
    for text in candidates:
        text_tokens = set(text.lower().split())
        overlap = len(question_tokens & text_tokens)
        scored.append((text, overlap))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [text for text, score in scored if score > 0] + [text for text, score in scored if score == 0]


class RetrievalService:
    """V1: token-overlap ranking. V2 will swap internals without changing the signature."""

    def search(self, question: str, department: str | None = None, limit: int = 3) -> list[RetrievedChunk]:
        tokens = question.lower().split()
        _ = tokens  # placeholder for future use
        return []

    def hybrid_search(self, question: str, vector_results: list[str], bm25_results: list[str]) -> list[str]:
        return reciprocal_rank_fusion([vector_results, bm25_results])
