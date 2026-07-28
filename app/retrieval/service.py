from app.retrieval.types import RetrievedChunk

_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        from app.core.config import settings
        _embedding_model = SentenceTransformer(settings.embedding_model, trust_remote_code=True)
    return _embedding_model


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
    """V1: vector search. V2: hybrid vector + text search via RRF."""

    def search(self, question: str, department: str | None = None, limit: int = 3) -> list[RetrievedChunk]:
        from app.db.models import Chunk
        from app.db.session import SessionLocal

        model = _get_embedding_model()
        query_embedding = model.encode([question], normalize_embeddings=True).tolist()[0]

        session = SessionLocal()
        try:
            q = session.query(Chunk).order_by(
                Chunk.embedding.cosine_distance(query_embedding)
            )
            if department:
                q = q.filter(Chunk.department == department)
            rows = q.limit(limit).all()

            return [
                RetrievedChunk(
                    id=str(row.id),
                    content=row.content,
                    title=row.title,
                    section=row.section,
                    score=1.0,
                    access_level=row.access_level,
                    department=row.department,
                )
                for row in rows
            ]
        finally:
            session.close()

    def hybrid_search(self, question: str, department: str | None = None, limit: int = 3) -> list[RetrievedChunk]:
        from app.db.models import Chunk
        from app.db.session import SessionLocal

        model = _get_embedding_model()
        query_embedding = model.encode([question], normalize_embeddings=True).tolist()[0]

        session = SessionLocal()
        try:
            base = session.query(Chunk)
            if department:
                base = base.filter(Chunk.department == department)

            vector_rows = base.order_by(
                Chunk.embedding.cosine_distance(query_embedding)
            ).limit(limit * 4).all()

            text_rows = base.filter(
                Chunk.content.ilike(f"%{question.split()[0]}%")
            ).limit(limit * 2).all()

            def row_key(row: Chunk) -> str:
                return str(row.id)

            # RRF fuse
            all_ids: dict[str, float] = {}
            for rank, row in enumerate(vector_rows, 1):
                all_ids[row_key(row)] = all_ids.get(row_key(row), 0.0) + 1.0 / (60 + rank)
            for rank, row in enumerate(text_rows, 1):
                all_ids[row_key(row)] = all_ids.get(row_key(row), 0.0) + 1.0 / (60 + rank)

            ranked_ids = sorted(all_ids, key=all_ids.get, reverse=True)[:limit]  # type: ignore[arg-type]

            id_map = {row_key(row): row for row in vector_rows + text_rows}
            return [
                RetrievedChunk(
                    id=str(id_map[rid].id),
                    content=id_map[rid].content,
                    title=id_map[rid].title,
                    section=id_map[rid].section,
                    score=all_ids[rid],
                    access_level=id_map[rid].access_level,
                    department=id_map[rid].department,
                )
                for rid in ranked_ids if rid in id_map
            ]
        finally:
            session.close()
