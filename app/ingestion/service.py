"""Ingestion service — document loading, chunking, embedding, and pgvector storage."""
from pathlib import Path
from typing import List
from app.ingestion.chunking import ChunkDraft, chunk_markdown


def ingest_documents(docs_dir: Path) -> List[ChunkDraft]:
    """Load all markdown files from docs_dir and chunk them."""
    all_chunks: List[ChunkDraft] = []
    for filepath in sorted(docs_dir.glob("*.md")):
        text = filepath.read_text(encoding="utf-8")
        chunks = chunk_markdown(text, title=filepath.stem)
        all_chunks.extend(chunks)
    return all_chunks
