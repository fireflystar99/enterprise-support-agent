from pathlib import Path
from unittest.mock import patch

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


def test_ingest_to_db_inserts_all_chunks_per_document(tmp_path: Path) -> None:
    """Regression: multi-heading doc must insert all chunks, not just the first."""
    content = "# Section 1\nContent A.\n\n# Section 2\nContent B.\n\n# Section 3\nContent C."
    (tmp_path / "multi.md").write_text(content, encoding="utf-8")

    from app.ingestion.service import ingest_to_db

    with (
        patch.object(type(ingest_to_db), "__globals__", {}),
        patch("app.ingestion.service.SessionLocal") as mock_cls,
        patch("app.ingestion.service._get_embedding_model") as mock_model,
    ):

            fake_model = mock_model.return_value
            fake_model.encode.return_value.tolist.return_value = [[0.0] * 1024] * 3

            mock_session = mock_cls.return_value.__enter__.return_value
            mock_session.query.return_value.all.return_value = []

            result_count = ingest_to_db(tmp_path, clear=False)

            # 3 sections → 3 chunks
            assert result_count == 3
