from dataclasses import dataclass, field
from typing import List
import re


@dataclass
class ChunkDraft:
    content: str
    title: str
    section: str
    department: str
    access_level: str = "public"
    version: str = "1.0"


def chunk_markdown(
    text: str,
    title: str,
    department: str = "General",
    access_level: str = "public",
    version: str = "1.0",
    max_size: int = 800,
    overlap: int = 120,
) -> List[ChunkDraft]:
    """Split Markdown by headings into chunks with metadata."""
    lines = text.split("\n")
    chunks: List[ChunkDraft] = []
    current_section = ""
    current_buffer: List[str] = []

    def flush() -> None:
        nonlocal current_buffer
        content = "\n".join(current_buffer).strip()
        if not content:
            current_buffer = []
            return
        if len(content) > max_size:
            start = 0
            while start < len(content):
                end = min(start + max_size, len(content))
                segment = content[start:end].strip()
                if segment:
                    chunks.append(ChunkDraft(
                        content=segment,
                        title=title,
                        section=current_section,
                        department=department,
                        access_level=access_level,
                        version=version,
                    ))
                start = end - overlap
        else:
            chunks.append(ChunkDraft(
                content=content,
                title=title,
                section=current_section,
                department=department,
                access_level=access_level,
                version=version,
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
