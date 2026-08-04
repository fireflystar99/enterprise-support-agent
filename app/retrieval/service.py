import logging
import threading
import time

from app.core.config import settings
from app.retrieval.bm25 import bm25_rank
from app.retrieval.reranker import rerank_candidates
from app.retrieval.types import RetrievedChunk

_embedding_model = None
_embedding_lock = threading.Lock()
logger = logging.getLogger(__name__)

_DEMO_CHUNKS: dict[str, RetrievedChunk] = {
    "expense": RetrievedChunk(id="demo-1", content="差旅报销必须在费用发生日起30天内提交，逾期需经理审批。", title="差旅报销政策", section="提交时限", score=0.95, access_level="public", department="General"),
    "receipt": RetrievedChunk(id="demo-2", content="¥1,000元以下的费用自动批准，¥1,000-¥5,000需部门经理审批。", title="差旅报销政策", section="审批规则", score=0.85, access_level="public", department="General"),
    "travel": RetrievedChunk(id="demo-3", content="4小时以下航班经济舱，4小时以上可申请商务舱。", title="差旅报销政策", section="可报销项目", score=0.8, access_level="public", department="General"),
    "vpn": RetrievedChunk(id="demo-4", content="VPN密码重置需要联系IT支持，请拨打IT服务台电话或提交工单。", title="VPN常见问题", section="密码重置", score=0.9, access_level="public", department="IT"),
}


def _demo_search(question: str) -> list[RetrievedChunk]:
    normalized = question.lower()
    results = []
    for keyword, chunk in _DEMO_CHUNKS.items():
        if keyword in normalized:
            results.append(chunk)
    # Chinese fallback keywords for demo mode
    if not results:
        if "报销" in normalized or "提交" in normalized or "差旅" in normalized or "多久" in normalized:
            results.append(_DEMO_CHUNKS["expense"])
        if "报销" in normalized or "审批" in normalized or "金额" in normalized:
            results.append(_DEMO_CHUNKS["receipt"])
        if "报销" in normalized or "航班" in normalized or "商务" in normalized or "经济舱" in normalized:
            results.append(_DEMO_CHUNKS["travel"])
    if not results and ("vpn" in normalized or "密码" in normalized or "连接" in normalized):
        results.append(_DEMO_CHUNKS["vpn"])
    return results[:3]


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        # 进程内单例缓存：模型只加载一次，后续请求直接复用。
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(settings.embedding_model, trust_remote_code=True)
    return _embedding_model


def warm_embedding_model() -> None:
    """应用启动时预先加载 embedding 模型。"""
    if settings.app_env == "demo":
        return
    try:
        _get_embedding_model()
    except OSError:
        import logging
        logging.getLogger(__name__).warning("Embedding model unavailable — continuing in degraded mode")


def rank_by_token_overlap(question: str, candidates: list[str]) -> list[str]:
    """按 Token 重叠度对候选文本排序。"""
    question_tokens = set(question.lower().split())
    scored = []
    for text in candidates:
        text_tokens = set(text.lower().split())
        overlap = len(question_tokens & text_tokens)
        scored.append((text, overlap))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [text for text, score in scored if score > 0] + [text for text, score in scored if score == 0]


class RetrievalService:
    """V1: 向量检索。V2: 向量 + 关键词混合检索（RRF）。"""

    def __init__(self) -> None:
        self.last_timings = self._empty_timings()

    @staticmethod
    def _empty_timings() -> dict[str, int]:
        return {
            "embedding_ms": 0,
            "vector_search_ms": 0,
            "bm25_ms": 0,
            "fusion_ms": 0,
            "rerank_ms": 0,
            "total_ms": 0,
        }

    def search(self, question: str, department: str | None = None, limit: int = 3) -> list[RetrievedChunk]:
        if settings.app_env == "demo":
            return _demo_search(question)

        from app.db.models import Chunk
        from app.db.session import SessionLocal

        total_started = time.perf_counter()
        self.last_timings = self._empty_timings()
        started = time.perf_counter()
        model = _get_embedding_model()
        with _embedding_lock:
            query_embedding = model.encode([question], normalize_embeddings=True).tolist()[0]
        self.last_timings["embedding_ms"] = int((time.perf_counter() - started) * 1000)

        session = SessionLocal()
        try:
            started = time.perf_counter()
            q = session.query(Chunk).order_by(
                Chunk.embedding.cosine_distance(query_embedding)
            )
            if department:
                q = q.filter(Chunk.department == department)
            rows = q.limit(limit).all()
            self.last_timings["vector_search_ms"] = int((time.perf_counter() - started) * 1000)

            result = [
                RetrievedChunk(
                    id=str(row.id),
                    content=row.content,
                    title=row.title,
                    section=row.section,
                    score=1.0,
                    access_level=row.access_level,
                    department=row.department,
                    source_type=getattr(row, "source_type", "markdown"),
                    source_path=getattr(row, "source_path", ""),
                    page_number=getattr(row, "page_number", None),
                    content_type=getattr(row, "content_type", "text"),
                    table_name=getattr(row, "table_name", None),
                )
                for row in rows
            ]
            self.last_timings["total_ms"] = int(
                (time.perf_counter() - total_started) * 1000
            )
            return result
        finally:
            session.close()

    def hybrid_search(
        self,
        question: str,
        department: str | None = None,
        limit: int = 3,
        *,
        rerank: bool = False,
        rerank_top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        if settings.app_env == "demo":
            return _demo_search(question)

        from app.db.models import Chunk
        from app.db.session import SessionLocal

        total_started = time.perf_counter()
        self.last_timings = self._empty_timings()
        started = time.perf_counter()
        model = _get_embedding_model()
        with _embedding_lock:
            query_embedding = model.encode([question], normalize_embeddings=True).tolist()[0]
        self.last_timings["embedding_ms"] = int((time.perf_counter() - started) * 1000)

        session = SessionLocal()
        try:
            base = session.query(Chunk)
            if department:
                base = base.filter(Chunk.department == department)

            # 先多召回，再融合/精排；向量 4 倍、文本 2 倍是质量与延迟的平衡。
            vector_candidate_limit = limit * 4
            text_candidate_limit = limit * 2
            started = time.perf_counter()
            vector_rows = base.order_by(
                Chunk.embedding.cosine_distance(query_embedding)
            ).limit(vector_candidate_limit).all()
            self.last_timings["vector_search_ms"] = int((time.perf_counter() - started) * 1000)

            started = time.perf_counter()
            from sqlalchemy.orm import load_only

            # BM25 只需要文本与元数据，显式排除 embedding 大字段，避免无谓传输。
            rows = base.options(
                load_only(
                    Chunk.id,
                    Chunk.content,
                    Chunk.title,
                    Chunk.section,
                    Chunk.access_level,
                    Chunk.department,
                    Chunk.source_type,
                    Chunk.source_path,
                    Chunk.page_number,
                    Chunk.content_type,
                    Chunk.table_name,
                )
            ).all()
            bm25_indexes = bm25_rank(
                question,
                [row.content for row in rows],
            )[:text_candidate_limit]
            bm25_rows = [rows[index] for index in bm25_indexes]
            self.last_timings["bm25_ms"] = int((time.perf_counter() - started) * 1000)

            def row_key(row: Chunk) -> str:
                return str(row.id)

            started = time.perf_counter()
            # Reciprocal Rank Fusion：同一文档在两个召回列表中排名靠前时得分更高。
            all_ids: dict[str, float] = {}
            for rank, row in enumerate(vector_rows, 1):
                all_ids[row_key(row)] = all_ids.get(row_key(row), 0.0) + 1.0 / (60 + rank)
            for rank, row in enumerate(bm25_rows, 1):
                all_ids[row_key(row)] = all_ids.get(row_key(row), 0.0) + 1.0 / (60 + rank)

            ranked_ids = sorted(all_ids, key=all_ids.get, reverse=True)

            id_map = {row_key(row): row for row in vector_rows + bm25_rows}
            candidates = [
                RetrievedChunk(
                    id=str(id_map[rid].id),
                    content=id_map[rid].content,
                    title=id_map[rid].title,
                    section=id_map[rid].section,
                    score=all_ids[rid],
                    access_level=id_map[rid].access_level,
                    department=id_map[rid].department,
                    source_type=getattr(id_map[rid], "source_type", "markdown"),
                    source_path=getattr(id_map[rid], "source_path", ""),
                    page_number=getattr(id_map[rid], "page_number", None),
                    content_type=getattr(id_map[rid], "content_type", "text"),
                    table_name=getattr(id_map[rid], "table_name", None),
                )
                for rid in ranked_ids if rid in id_map
            ]
            self.last_timings["fusion_ms"] = int((time.perf_counter() - started) * 1000)

            started = time.perf_counter()
            if rerank:
                try:
                    # 只对融合后的前 N 个候选进行 Cross-Encoder 精排，控制模型推理开销。
                    rerank_limit = rerank_top_n or len(candidates)
                    reranked = rerank_candidates(question, candidates[:rerank_limit])
                    candidates = reranked + candidates[rerank_limit:]
                except OSError:
                    # 重排序模型不可用时保留 RRF 结果，检索服务仍可正常对外提供答案。
                    logger.warning("Reranker unavailable; using RRF ordering")
            self.last_timings["rerank_ms"] = int((time.perf_counter() - started) * 1000)

            result = candidates[:limit]
            self.last_timings["total_ms"] = int(
                (time.perf_counter() - total_started) * 1000
            )
            if self.last_timings["total_ms"] > 1000:
                # 分段耗时写日志，方便定位模型、数据库或重排阶段的性能瓶颈。
                logger.warning("Slow retrieval: %s", self.last_timings)
            return result
        finally:
            session.close()
