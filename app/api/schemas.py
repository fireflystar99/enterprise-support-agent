from typing import List, Literal
from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    department: str | None = None


class Citation(BaseModel):
    chunk_id: str
    title: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    confidence: Literal["high", "medium", "low"]
    route: Literal["answer", "ticket"]
    ticket_id: str | None = None
    trace_id: str
    latency_ms: int
