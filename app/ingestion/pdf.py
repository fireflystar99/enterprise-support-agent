"""解析 PDF 正文与原生表格，产出 ChunkDraft。

逐页提取可选文本与简单表格：
- 文本按页调用 chunk_text()，绝不跨页。
- 表格仅接收行数/列数规整且规模受限的简单表格；复杂表格跳过并计数。
- 加密、损坏或无法提取内容的文件只返回报告，不向外抛异常。
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import fitz
import pdfplumber

from app.ingestion.chunking import ChunkDraft, chunk_text

MAX_TABLE_CELLS = 500


@dataclass(frozen=True)
class PdfIngestionReport:
    path: str
    status: Literal["success", "encrypted_pdf", "pdf_parse_error", "no_extractable_text"]
    text_chunks: int = 0
    table_chunks: int = 0
    skipped_complex_tables: int = 0
    detail: str = ""


def _normalize_cell(cell) -> str:
    return (cell or "").replace("\n", " ").strip()


def _render_markdown(rows: list[list[str]]) -> str:
    header = "| " + " | ".join(rows[0]) + " |"
    separator = "| " + " | ".join("---" for _ in rows[0]) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows[1:])
    return f"{header}\n{separator}\n{body}"


def load_pdf(path: Path, *, relative_path: str) -> tuple[list[ChunkDraft], PdfIngestionReport]:
    """逐页提取可选文本和简单表格；异常文件只返回报告，不向外抛异常。"""
    path_str = str(path)
    try:
        document = fitz.open(path)
    except (fitz.FileDataError, OSError) as exc:
        return [], PdfIngestionReport(path=path_str, status="pdf_parse_error", detail=str(exc))
    except Exception as exc:  # noqa: BLE001 其他底层解析异常也收敛为解析错误
        return [], PdfIngestionReport(path=path_str, status="pdf_parse_error", detail=str(exc))

    with document:  # with 保证提前 return 时也关闭 document
        try:
            if document.needs_pass:
                return [], PdfIngestionReport(path=path_str, status="encrypted_pdf")
        except Exception as exc:  # noqa: BLE001
            return [], PdfIngestionReport(path=path_str, status="pdf_parse_error", detail=str(exc))

        drafts: list[ChunkDraft] = []
        for page_number, page in enumerate(document, start=1):
            content = page.get_text("text").strip()
            if content:
                drafts.extend(chunk_text(
                    content,
                    title=path.stem,
                    section=f"第 {page_number} 页",
                    source_type="pdf",
                    source_path=relative_path,
                    page_number=page_number,
                ))

    skipped_complex_tables = 0
    try:
        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                try:
                    tables = page.extract_tables()
                except Exception as exc:  # noqa: BLE001 表格通道异常收敛为解析错误
                    return _report(drafts, path_str, "pdf_parse_error", skipped_complex_tables, str(exc))
                for raw_rows in tables:
                    rows = [[_normalize_cell(cell) for cell in row] for row in raw_rows]
                    non_empty = [row for row in rows if any(cell for cell in row)]
                    col_counts = {len(row) for row in non_empty}
                    total_cells = sum(len(row) for row in non_empty)
                    if (
                        len(non_empty) < 2
                        or len(col_counts) != 1
                        or total_cells > MAX_TABLE_CELLS
                    ):
                        skipped_complex_tables += 1
                        continue
                    header = non_empty[0]
                    for i, cell in enumerate(header, start=1):
                        if not cell:
                            header[i - 1] = f"列{i}"
                    table_index = sum(1 for d in drafts if d.content_type == "table") + 1
                    drafts.append(ChunkDraft(
                        content=_render_markdown(non_empty),
                        title=path.stem,
                        section=f"第 {page_number} 页",
                        department="General",
                        source_type="pdf",
                        source_path=relative_path,
                        page_number=page_number,
                        content_type="table",
                        table_name=f"表格 {table_index}",
                        table_json=json.dumps(non_empty, ensure_ascii=False),
                    ))
    except Exception as exc:  # noqa: BLE001 表格通道失败同样收敛为解析错误
        return _report(drafts, path_str, "pdf_parse_error", skipped_complex_tables, str(exc))

    if not drafts:
        return [], PdfIngestionReport(path=path_str, status="no_extractable_text")
    return _report(drafts, path_str, "success", skipped_complex_tables)


def _report(
    drafts: list[ChunkDraft],
    path_str: str,
    status: Literal["success", "encrypted_pdf", "pdf_parse_error", "no_extractable_text"],
    skipped_complex_tables: int,
    detail: str = "",
) -> tuple[list[ChunkDraft], PdfIngestionReport]:
    return drafts, PdfIngestionReport(
        path=path_str,
        status=status,
        text_chunks=sum(1 for d in drafts if d.content_type == "text"),
        table_chunks=sum(1 for d in drafts if d.content_type == "table"),
        skipped_complex_tables=skipped_complex_tables,
        detail=detail,
    )
