from pathlib import Path

from app.ingestion.service import ingest_documents


def test_ingest_documents_loads_and_chunks_markdown(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("# FAQ\nAnswer content here.", encoding="utf-8")
    chunks = ingest_documents(tmp_path)
    assert len(chunks) >= 1
    assert chunks[0].title == "test"


def test_ingest_to_db_returns_zero_for_empty_dir() -> None:
    from app.ingestion.service import ingest_to_db

    result = ingest_to_db(Path("/nonexistent_dir_xyz"), clear=False)
    assert result == 0
