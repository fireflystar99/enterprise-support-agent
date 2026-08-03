from pathlib import Path
from typing import Self

import fitz
import pytest

import app.ingestion.pdf as pdf_module
from app.ingestion.pdf import load_pdf


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """构造一个两页、可选中文本的 PDF。"""
    path = tmp_path / "sample.pdf"
    doc = fitz.open()
    for line in ("首页文本内容。", "第二页文本内容。"):
        page = doc.new_page()
        page.insert_font(fontname="china-s")
        page.insert_text((72, 72), line, fontname="china-s")
    doc.save(str(path))
    doc.close()
    return path


class _FakePage:
    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = rows

    def extract_tables(self) -> list[list[list[str]]]:
        return [self._rows]


class _FakePdf:
    def __init__(self, rows: list[list[str]]) -> None:
        self.pages = [_FakePage(rows)]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def test_load_pdf_creates_page_bounded_text_drafts(sample_pdf: Path) -> None:
    drafts, report = load_pdf(sample_pdf, relative_path="data/documents/sample.pdf")
    assert report.status == "success"
    assert {(d.page_number, d.content_type) for d in drafts} == {(1, "text"), (2, "text")}
    assert all(d.source_type == "pdf" for d in drafts)


def test_load_pdf_serializes_simple_table(monkeypatch, sample_pdf: Path) -> None:
    monkeypatch.setattr(pdf_module.pdfplumber, "open", lambda _: _FakePdf(
        [["职级", "上限"], ["P4", "800 元"]]
    ))
    drafts, _ = load_pdf(sample_pdf, relative_path="data/documents/sample.pdf")
    table = next(d for d in drafts if d.content_type == "table")
    assert table.table_name == "表格 1"
    assert table.table_json == '[["职级", "上限"], ["P4", "800 元"]]'
    assert "| 职级 | 上限 |" in table.content


def test_load_pdf_no_text_returns_empty_and_status(monkeypatch, tmp_path: Path) -> None:
    blank = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(blank))
    doc.close()
    monkeypatch.setattr(pdf_module.pdfplumber, "open", lambda _: _FakePdf([]))
    drafts, report = load_pdf(blank, relative_path="data/documents/blank.pdf")
    assert report.status == "no_extractable_text"
    assert drafts == []


def test_load_pdf_skips_complex_table(monkeypatch, sample_pdf: Path) -> None:
    rows = [["职级", "上限", "备注"], ["P4"], ["P5", "1200 元", "含绩效"]]
    monkeypatch.setattr(pdf_module.pdfplumber, "open", lambda _: _FakePdf(rows))
    drafts, report = load_pdf(sample_pdf, relative_path="data/documents/sample.pdf")
    assert not any(d.content_type == "table" for d in drafts)
    assert report.skipped_complex_tables == 1


def test_load_pdf_encrypted_returns_status(tmp_path: Path) -> None:
    encrypted = tmp_path / "encrypted.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(encrypted), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="password")
    doc.close()
    drafts, report = load_pdf(encrypted, relative_path="data/documents/encrypted.pdf")
    assert report.status == "encrypted_pdf"
    assert drafts == []


def test_load_pdf_corrupted_returns_status(tmp_path: Path) -> None:
    corrupted = tmp_path / "corrupted.pdf"
    corrupted.write_bytes(b"%PDF-1.4 " + b"garbagegarbagegarbage" * 5)
    drafts, report = load_pdf(corrupted, relative_path="data/documents/corrupted.pdf")
    assert report.status == "pdf_parse_error"
    assert drafts == []
