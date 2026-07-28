from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    id: str
    content: str
    title: str
    section: str
    score: float
