import re
from dataclasses import dataclass


@dataclass
class ChunkDraft:
    content: str
    title: str
    section: str
    department: str
    access_level: str = "public"
    version: str = "1.0"
    source_type: str = "markdown"
    source_path: str = ""
    page_number: int | None = None
    content_type: str = "text"
    table_name: str | None = None
    table_json: str | None = None


def chunk_text(
    text: str,
    *,
    title: str,
    section: str = "",
    department: str = "General",
    access_level: str = "public",
    version: str = "1.0",
    source_type: str = "markdown",
    source_path: str = "",
    page_number: int | None = None,
    content_type: str = "text",
    table_name: str | None = None,
    table_json: str | None = None,
    max_size: int = 800,
    overlap: int = 120,
) -> list[ChunkDraft]:
    """在单一来源边界内切分文本，绝不跨越该边界。"""
    content = text.strip()
    if not content:
        return []

    def make_chunk(segment: str) -> ChunkDraft:
        return ChunkDraft(
            content=segment,
            title=title,
            section=section,
            department=department,
            access_level=access_level,
            version=version,
            source_type=source_type,
            source_path=source_path,
            page_number=page_number,
            content_type=content_type,
            table_name=table_name,
            table_json=table_json,
        )

    if len(content) <= max_size:
        return [make_chunk(content)]

    chunks: list[ChunkDraft] = []
    start = 0
    while start < len(content):
        end = min(start + max_size, len(content))
        segment = content[start:end].strip()
        if segment:
            chunks.append(make_chunk(segment))
        if end >= len(content):
            break
        start = end - overlap
    return chunks


def chunk_markdown(
    text: str,
    title: str,
    department: str = "General",
    access_level: str = "public",
    version: str = "1.0",
    max_size: int = 800,
    overlap: int = 120,
) -> list[ChunkDraft]:
    """按 Markdown 标题拆分文档为带元数据的分块。"""
    lines = text.split("\n")
    chunks: list[ChunkDraft] = []
    current_section = ""
    current_buffer: list[str] = []

    def flush() -> None:
        nonlocal current_buffer
        content = "\n".join(current_buffer).strip()
        if not content:
            current_buffer = []
            return
        chunks.extend(chunk_text(
            content,
            title=title,
            section=current_section,
            department=department,
            access_level=access_level,
            version=version,
            max_size=max_size,
            overlap=overlap,
        ))
        current_buffer = []

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            flush()
            current_section = heading_match.group(2).strip()
            current_buffer.append(line)
        else:
            current_buffer.append(line)
    flush()

    return chunks
