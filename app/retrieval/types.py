from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    id: str
    content: str
    title: str
    section: str
    score: float
    access_level: str = "public"
    department: str = "General"
    source_type: str = "markdown"
    source_path: str = ""
    page_number: int | None = None
    content_type: str = "text"
    table_name: str | None = None
