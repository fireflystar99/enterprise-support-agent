from dataclasses import dataclass, field


@dataclass
class RetrievedChunk:
    id: str
    content: str
    title: str
    section: str
    score: float
    access_level: str = "public"
