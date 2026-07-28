import time
import uuid

from app.api.schemas import ChatResponse, Citation
from app.retrieval.service import RetrievalService
from app.retrieval.types import RetrievedChunk
from app.support.routing import SENSITIVE_TERMS, Route, decide_route
from app.support.tickets import ticket_service


class SupportAgent:
    """Support agent — uses search_knowledge_base and create_ticket tools."""

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self._retrieval = retrieval_service or RetrievalService()

    def search_knowledge_base(self, question: str, department: str | None = None, limit: int = 3) -> list[RetrievedChunk]:
        return self._retrieval.search(question, department=department, limit=limit)

    def _build_answer(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return ""
        lines = [chunks[0].content]
        for i, c in enumerate(chunks[1:], 2):
            lines.append(f"[{i}] {c.content}")
        return "\n\n".join(lines)

    def handle(self, question: str, department: str | None = None) -> ChatResponse:
        trace_id = str(uuid.uuid4())
        start = time.monotonic_ns()

        chunks = self.search_knowledge_base(question, department)
        evidence_count = len(chunks)
        route = decide_route(question, evidence_count)

        if route is Route.TICKET:
            reason = "Evidence insufficient or sensitive action requested"
            risk_level = "high" if any(term in question.lower() for term in SENSITIVE_TERMS) else "low"
            ticket = ticket_service.create(question, reason=reason, risk_level=risk_level)
            latency_ms = int((time.monotonic_ns() - start) / 1_000_000)
            return ChatResponse(
                answer="Your request has been forwarded to the support team for handling.",
                citations=[],
                confidence="low",
                route="ticket",
                ticket_id=ticket.id,
                trace_id=trace_id,
                latency_ms=latency_ms,
            )

        citations = [
            Citation(chunk_id=c.id, title=c.title, excerpt=c.content[:200])
            for c in chunks
        ]
        answer = self._build_answer(chunks)
        latency_ms = int((time.monotonic_ns() - start) / 1_000_000)
        return ChatResponse(
            answer=answer,
            citations=citations,
            confidence="high" if evidence_count >= 2 else "medium",
            route="answer",
            trace_id=trace_id,
            latency_ms=latency_ms,
        )


support_agent = SupportAgent()
