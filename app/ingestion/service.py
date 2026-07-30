"""文档摄入服务——加载、分块、编码 embedding、写入 pgvector。"""
from pathlib import Path

from app.ingestion.chunking import ChunkDraft, chunk_markdown

_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        from app.core.config import settings
        _embedding_model = SentenceTransformer(settings.embedding_model, trust_remote_code=True)
    return _embedding_model


def ingest_documents(docs_dir: Path) -> list[ChunkDraft]:
    """加载 docs_dir 下所有 markdown 文件并分块。"""
    all_chunks: list[ChunkDraft] = []
    for filepath in sorted(docs_dir.glob("*.md")):
        text = filepath.read_text(encoding="utf-8")
        chunks = chunk_markdown(text, title=filepath.stem)
        all_chunks.extend(chunks)
    return all_chunks


def ingest_to_db(docs_dir: Path, clear: bool = False) -> int:
    """加载、分块、编码 embedding 并写入 pgvector。返回 Chunk 数量。"""
    from app.db.models import Chunk, Document
    from app.db.session import SessionLocal

    draft_chunks = ingest_documents(docs_dir)
    if not draft_chunks:
        return 0

    model = _get_embedding_model()
    session = SessionLocal()

    try:
        if clear:
            session.query(Chunk).delete()
            session.query(Document).delete()
            session.commit()

        seen_titles = {row[0] for row in session.query(Document.title).all()}
        chunk_count = 0

        # Group all drafts by title so one Document row covers all its chunks
        from collections import OrderedDict
        groups: OrderedDict[str, list[ChunkDraft]] = OrderedDict()
        for d in draft_chunks:
            groups.setdefault(d.title, []).append(d)

        for title, drafts in groups.items():
            if title in seen_titles:
                continue

            first = drafts[0]
            doc = Document(title=title, department=first.department, version=first.version)
            session.add(doc)
            session.flush()

            texts = [d.content for d in drafts]
            embeddings = model.encode(texts, normalize_embeddings=True).tolist()

            for draft, emb in zip(drafts, embeddings, strict=False):
                chunk = Chunk(
                    document_id=doc.id,
                    content=draft.content,
                    title=title,
                    section=draft.section,
                    department=draft.department,
                    access_level=draft.access_level,
                    version=draft.version,
                    embedding=emb,
                )
                session.add(chunk)
                chunk_count += 1

            seen_titles.add(title)

        session.commit()
        return chunk_count
    finally:
        session.close()
