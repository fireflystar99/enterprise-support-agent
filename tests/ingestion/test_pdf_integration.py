"""PDF 入库运维报告：seed 输出统计、批量失败兜底与表格元数据持久化。"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

from app.ingestion.chunking import ChunkDraft
from app.ingestion.pdf import PdfIngestionReport
from app.ingestion.service import IngestionSummary, ingest_documents, ingest_to_db


def _load_seed_demo():
    spec = importlib.util.spec_from_file_location(
        "seed_demo", Path(__file__).resolve().parents[2] / "scripts" / "seed_demo.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["seed_demo"] = module
    spec.loader.exec_module(module)
    return module


def test_seed_reports_pdf_and_table_counts(monkeypatch, capsys) -> None:
    seed_demo = _load_seed_demo()
    summary = IngestionSummary(
        chunk_count=5,
        markdown_documents=1,
        pdf_reports=(PdfIngestionReport("policy.pdf", "success", 3, 1),),
    )
    monkeypatch.setattr(seed_demo, "ingest_to_db", lambda *_args, **_kwargs: summary)
    seed_demo.main()
    output = capsys.readouterr().out
    assert "PDF documents: 1" in output
    assert "Table chunks: 1" in output


def test_seed_reports_skipped_pdf(monkeypatch, capsys) -> None:
    seed_demo = _load_seed_demo()
    summary = IngestionSummary(
        chunk_count=0,
        markdown_documents=0,
        pdf_reports=(PdfIngestionReport("bad.pdf", "pdf_parse_error"),),
    )
    monkeypatch.setattr(seed_demo, "ingest_to_db", lambda *_args, **_kwargs: summary)
    seed_demo.main()
    output = capsys.readouterr().out
    assert "SKIPPED: bad.pdf (pdf_parse_error)" in output


def test_ingest_to_db_returns_summary_with_counts(tmp_path: Path) -> None:
    """回归：ingest_to_db 返回 IngestionSummary，chunk 计数与文档数确定。"""
    (tmp_path / "a.md").write_text("# A\nContent A.", encoding="utf-8")
    with (
        patch("app.db.session.SessionLocal") as mock_cls,
        patch("app.ingestion.service._get_embedding_model") as mock_model,
    ):
        fake_model = mock_model.return_value
        fake_model.encode.return_value.tolist.return_value = [[0.0] * 1024]

        mock_session = mock_cls.return_value
        mock_session.query.return_value.all.return_value = []

        summary = ingest_to_db(tmp_path, clear=False)
        assert summary.chunk_count == 1
        assert summary.markdown_documents == 1


def test_batch_failure_keeps_markdown_and_reports_bad_pdf(tmp_path: Path) -> None:
    """一个损坏 PDF 不阻断同一目录的 Markdown 入库。"""
    (tmp_path / "faq.md").write_text("# FAQ\nSubmit within 30 days.", encoding="utf-8")
    (tmp_path / "broken.pdf").write_bytes(b"%PDF-1.4 " + b"garbagegarbage" * 5)

    with (
        patch("app.db.session.SessionLocal") as mock_cls,
        patch("app.ingestion.service._get_embedding_model") as mock_model,
    ):
        fake_model = mock_model.return_value
        fake_model.encode.return_value.tolist.return_value = [[0.0] * 1024]

        mock_session = mock_cls.return_value
        mock_session.query.return_value.all.return_value = []

        drafts, reports = ingest_documents(tmp_path)
        assert any(d.source_type == "markdown" for d in drafts)
        assert reports[0].status == "pdf_parse_error"


def test_ingest_to_db_persists_pdf_table_chunk(tmp_path: Path) -> None:
    """持久化的表格 chunk 保留 page_number / content_type / 精确 table JSON。"""
    (tmp_path / "policy.pdf").write_bytes(b"%PDF-test")
    table_draft = ChunkDraft(
        content="| 职级 | 上限 |\n| --- | --- |\n| P4 | 800 元 |",
        title="policy", section="第 1 页", department="General",
        source_type="pdf", source_path="data/documents/policy.pdf",
        page_number=1, content_type="table", table_name="表格 1",
        table_json='[["职级", "上限"], ["P4", "800 元"]]',
    )
    with (
        patch("app.db.session.SessionLocal") as mock_cls,
        patch("app.ingestion.service._get_embedding_model") as mock_model,
        patch("app.ingestion.service.load_pdf") as mock_load_pdf,
    ):
        fake_model = mock_model.return_value
        fake_model.encode.return_value.tolist.return_value = [[0.0] * 1024]

        mock_load_pdf.return_value = (
            [table_draft],
            PdfIngestionReport("policy.pdf", "success", 0, 1),
        )

        mock_session = mock_cls.return_value
        mock_session.query.return_value.all.return_value = []

        ingest_to_db(tmp_path, clear=False)

        added = mock_session.add
        added.assert_called()
        chunks = [call.args[0] for call in added.call_args_list if call.args[0].__class__.__name__ == "Chunk"]
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.page_number == 1
        assert chunk.content_type == "table"
        assert chunk.table_json == '[["职级", "上限"], ["P4", "800 元"]]'
