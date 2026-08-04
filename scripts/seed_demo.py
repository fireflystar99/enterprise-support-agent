#!/usr/bin/env python3
"""Seed the knowledge base with demo documents."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.service import ingest_to_db

DOCUMENTS_DIR = Path("data/documents")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed knowledge base with demo documents")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
    args, _ = parser.parse_known_args()

    print("Seeding knowledge base...")
    summary = ingest_to_db(DOCUMENTS_DIR, clear=args.clear)
    text_chunks = sum(r.text_chunks for r in summary.pdf_reports)
    table_chunks = sum(r.table_chunks for r in summary.pdf_reports)
    print(f"  Inserted {summary.chunk_count} chunks into pgvector.")
    print(f"  Markdown documents: {summary.markdown_documents}")
    print(f"  PDF documents: {len(summary.pdf_reports)}")
    print(f"  PDF text chunks: {text_chunks}")
    print(f"  Table chunks: {table_chunks}")
    for report in summary.pdf_reports:
        if report.status != "success":
            print(f"  SKIPPED: {report.path} ({report.status})")
    print("Done. Start the API with: uvicorn app.api.main:app --reload")


if __name__ == "__main__":
    main()
