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
    args = parser.parse_args()

    print("Seeding knowledge base...")
    count = ingest_to_db(DOCUMENTS_DIR, clear=args.clear)
    print(f"  Inserted {count} chunks into pgvector.")
    print("Done. Start the API with: uvicorn app.api.main:app --reload")


if __name__ == "__main__":
    main()
