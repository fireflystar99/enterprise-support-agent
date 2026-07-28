"""Ingestion service — document loading, chunking, embedding, and pgvector storage."""
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
    """Load all markdown files from docs_dir, chunk, embed, and store in pgvector."""
    all_chunks: list[ChunkDraft] = []
    for filepath in sorted(docs_dir.glob("*.md")):
        text = filepath.read_text(encoding="utf-8")
        chunks = chunk_markdown(text, title=filepath.stem)
        all_chunks.extend(chunks)
    return all_chunks


def ingest_to_db(docs_dir: Path, clear: bool = False) -> int:
    """Load, chunk, embed, and write documents to pgvector. Returns chunk count."""
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

        for draft in draft_chunks:
            if draft.title in seen_titles:
                continue

            doc = Document(title=draft.title, department=draft.department, version=draft.version)
            session.add(doc)
            session.flush()

            texts = [draft.content]
            embedding = model.encode(texts, normalize_embeddings=True).tolist()[0]

            chunk = Chunk(
                document_id=doc.id,
                content=draft.content,
                title=draft.title,
                section=draft.section,
                department=draft.department,
                access_level=draft.access_level,
                version=draft.version,
                embedding=embedding,
            )
            session.add(chunk)
            session.flush()
            seen_titles.add(draft.title)
            chunk_count += 1

        session.commit()
        return chunk_count
    finally:
        session.close()
