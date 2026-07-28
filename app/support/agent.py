import time
import uuid

from app.api.schemas import ChatResponse, Citation
from app.retrieval.types import RetrievedChunk
from app.support.routing import SENSITIVE_TERMS, Route, decide_route
from app.support.tickets import ticket_service


class SupportAgent:
    """Support agent — uses search_knowledge_base and create_ticket tools."""

    def search_knowledge_base(self, question: str, department: str | None = None) -> list[RetrievedChunk]:
        _ = department  # reserved for pgvector-backed retrieval in V2
        normalized = question.lower()
        if "expense" in normalized or "receipt" in normalized or "travel" in normalized:
            return [
                RetrievedChunk(id="chunk-1", content="Submit receipts within 30 calendar days.", title="expense-policy", section="Submission Deadlines", score=0.95),
                RetrievedChunk(id="chunk-2", content="Expenses under ¥1,000 are auto-approved.", title="expense-policy", section="Approval Rules", score=0.85),
            ]
        if "vpn" in normalized:
            return [
                RetrievedChunk(id="chunk-3", content="VPN password resets require IT Support.", title="vpn-faq", section="Password Reset", score=0.9),
            ]
        return []

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
        answer = f"Based on the knowledge base: {chunks[0].content}"
        latency_ms = int((time.monotonic_ns() - start) / 1_000_000)
        return ChatResponse(
            answer=answer,
            citations=citations,
            confidence="high",
            route="answer",
            trace_id=trace_id,
            latency_ms=latency_ms,
        )


support_agent = SupportAgent()
