"""文档摄入服务——加载、分块、编码 embedding、写入 pgvector，并按格式分发 Markdown / PDF。"""
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.chunking import ChunkDraft, chunk_markdown
from app.ingestion.pdf import PdfIngestionReport, load_pdf

_embedding_model = None


@dataclass(frozen=True)
class IngestionSummary:
    chunk_count: int
    markdown_documents: int
    pdf_reports: tuple[PdfIngestionReport, ...]


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        from app.core.config import settings
        _embedding_model = SentenceTransformer(settings.embedding_model, trust_remote_code=True)
    return _embedding_model


def ingest_documents(docs_dir: Path) -> tuple[list[ChunkDraft], list[PdfIngestionReport]]:
    """加载 docs_dir 下的一级 Markdown 与 PDF 文件并分块。

    按名称顺序遍历；未知扩展名直接跳过；目录不存在时返回空结果。
    """
    if not docs_dir.is_dir():
        return [], []

    all_chunks: list[ChunkDraft] = []
    pdf_reports: list[PdfIngestionReport] = []
    for filepath in sorted(docs_dir.iterdir()):
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() == ".md":
            text = filepath.read_text(encoding="utf-8")
            all_chunks.extend(chunk_markdown(text, title=filepath.stem))
        elif filepath.suffix.lower() == ".pdf":
            drafts, report = load_pdf(filepath, relative_path=str(filepath))
            all_chunks.extend(drafts)
            pdf_reports.append(report)
    return all_chunks, pdf_reports


def ingest_to_db(docs_dir: Path, clear: bool = False) -> IngestionSummary:
    """加载、分块、编码 embedding 并写入 pgvector。返回汇总统计。"""
    from app.db.models import Chunk, Document
    from app.db.session import SessionLocal

    draft_chunks, pdf_reports = ingest_documents(docs_dir)
    if not draft_chunks:
        return _summary(draft_chunks, pdf_reports)

    model = _get_embedding_model()
    session = SessionLocal()

    try:
        if clear:
            session.query(Chunk).delete()
            session.query(Document).delete()
            session.commit()

        seen_titles = {row[0] for row in session.query(Document.title).all()}
        chunk_count = 0

        # Group all drafts by title so one Document row covers all its chunks
        from collections import OrderedDict
        groups: OrderedDict[str, list[ChunkDraft]] = OrderedDict()
        for d in draft_chunks:
            groups.setdefault(d.title, []).append(d)

        for title, drafts in groups.items():
            if title in seen_titles:
                continue

            first = drafts[0]
            doc = Document(title=title, department=first.department, version=first.version)
            session.add(doc)
            session.flush()

            texts = [d.content for d in drafts]
            embeddings = model.encode(texts, normalize_embeddings=True).tolist()

            for draft, emb in zip(drafts, embeddings, strict=False):
                chunk = Chunk(
                    document_id=doc.id,
                    content=draft.content,
                    title=title,
                    section=draft.section,
                    department=draft.department,
                    access_level=draft.access_level,
                    version=draft.version,
                    source_type=draft.source_type,
                    source_path=draft.source_path,
                    page_number=draft.page_number,
                    content_type=draft.content_type,
                    table_name=draft.table_name,
                    table_json=draft.table_json,
                    embedding=emb,
                )
                session.add(chunk)
                chunk_count += 1

            seen_titles.add(title)

        session.commit()
        return _summary(draft_chunks, pdf_reports)
    finally:
        session.close()


def _summary(
    drafts: list[ChunkDraft],
    pdf_reports: list[PdfIngestionReport],
) -> IngestionSummary:
    """从已分块的 drafts 与 PDF 报告聚合一次性汇总，不重复解析文件。"""
    markdown_documents = {d.title for d in drafts if d.source_type == "markdown"}
    return IngestionSummary(
        chunk_count=len(drafts),
        markdown_documents=len(markdown_documents),
        pdf_reports=tuple(pdf_reports),
    )
