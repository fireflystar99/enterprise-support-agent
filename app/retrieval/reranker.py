import logging
from dataclasses import replace

from app.core.config import settings
from app.retrieval.types import RetrievedChunk

_reranker = None
logger = logging.getLogger(__name__)


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(settings.reranker_model, trust_remote_code=True)
    return _reranker


def warm_reranker_model() -> None:
    """应用启动时预先加载 reranker 模型。"""
    try:
        _get_reranker()
    except OSError:
        logger.warning("Reranker model unavailable; continuing in degraded mode")


def rerank_candidates(question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """按 cross-encoder 相关性分数对 Chunk 排序。"""
    if not chunks:
        return []

    scores = _get_reranker().predict([(question, chunk.content) for chunk in chunks])
    reranked = [replace(chunk, score=float(score)) for chunk, score in zip(chunks, scores)]
    return sorted(reranked, key=lambda chunk: chunk.score, reverse=True)
