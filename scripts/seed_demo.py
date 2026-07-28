#!/usr/bin/env python3
"""Seed the knowledge base with demo documents."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.chunking import chunk_markdown

DOCUMENTS_DIR = Path("data/documents")


def main() -> None:
    print("Seeding knowledge base...")
    for filepath in sorted(DOCUMENTS_DIR.glob("*.md")):
        text = filepath.read_text(encoding="utf-8")
        title = filepath.stem
        chunks = chunk_markdown(text, title=title)
        print(f"  {filepath.name}: {len(chunks)} chunks")
    print("Done. Start the API with: uvicorn app.api.main:app --reload")


if __name__ == "__main__":
    main()
