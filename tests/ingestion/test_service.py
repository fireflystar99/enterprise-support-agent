from pathlib import Path
from unittest.mock import patch

from app.ingestion.chunking import ChunkDraft
from app.ingestion.pdf import PdfIngestionReport
from app.ingestion.service import ingest_documents


def test_ingest_documents_loads_and_chunks_markdown(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("# FAQ\nAnswer content here.", encoding="utf-8")
    chunks, reports = ingest_documents(tmp_path)
    assert len(chunks) >= 1
    assert chunks[0].title == "test"
    assert reports == []


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
        patch("app.db.session.SessionLocal") as mock_cls,
        patch("app.ingestion.service._get_embedding_model") as mock_model,
    ):
        fake_model = mock_model.return_value
        fake_model.encode.return_value.tolist.return_value = [[0.0] * 1024] * 3

        mock_session = mock_cls.return_value.__enter__.return_value
        mock_session.query.return_value.all.return_value = []

        result_count = ingest_to_db(tmp_path, clear=False)

        # 3 sections → 3 chunks
        assert result_count == 3


def test_ingest_documents_loads_markdown_and_pdf(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "faq.md").write_text("# FAQ\nSubmit within 30 days.", encoding="utf-8")
    (tmp_path / "policy.pdf").write_bytes(b"%PDF-test")
    pdf_draft = ChunkDraft(
        content="住宿上限为 800 元。", title="policy", section="第 1 页",
        department="General", source_type="pdf",
        source_path="data/documents/policy.pdf", page_number=1,
    )
    monkeypatch.setattr("app.ingestion.service.load_pdf", lambda *_a, **_kw:
        ([pdf_draft], PdfIngestionReport("policy.pdf", "success", 1))
    )
    chunks, reports = ingest_documents(tmp_path)
    assert {chunk.source_type for chunk in chunks} == {"markdown", "pdf"}
    assert reports[0].status == "success"
