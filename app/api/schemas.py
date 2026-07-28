from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    department: str | None = None


class Citation(BaseModel):
    chunk_id: str
    title: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: Literal["high", "medium", "low"]
    route: Literal["answer", "ticket"]
    ticket_id: str | None = None
    trace_id: str
    latency_ms: int
