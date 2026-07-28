import time
import uuid
from typing import TYPE_CHECKING

from app.api.schemas import ChatResponse, Citation
from app.db.models import QueryTrace
from app.db.session import SessionLocal
from app.retrieval.service import RetrievalService
from app.retrieval.types import RetrievedChunk
from app.support.routing import Route, calculate_risk_score, decide_route
from app.support.tickets import ticket_service

if TYPE_CHECKING:
    from app.core.experiment_config import ExperimentConfig


class SupportAgent:
    """Support agent — uses search_knowledge_base and create_ticket tools."""

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self._retrieval = retrieval_service or RetrievalService()

    def search_knowledge_base(self, question: str, department: str | None = None, limit: int = 3) -> list[RetrievedChunk]:
        return self._retrieval.search(question, department=department, limit=limit)

    def _build_answer(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return ""
        lines = [f"[1] {chunks[0].content}"]
        for i, c in enumerate(chunks[1:], 2):
            lines.append(f"[{i}] {c.content}")
        return "\n\n".join(lines)

    def _persist_trace(self, trace_id: str, question: str, chunk_ids: str, answer: str, route: str, confidence: str, ticket_id: str | None, latency_ms: int) -> None:
        try:
            session = SessionLocal()
            trace = QueryTrace(
                id=trace_id,
                question=question,
                retrieved_chunk_ids=chunk_ids,
                answer=answer,
                route=route,
                confidence=confidence,
                ticket_id=ticket_id,
                latency_ms=latency_ms,
            )
            session.add(trace)
            session.commit()
        except Exception:
            pass
        finally:
            session.close()

    def handle(self, question: str, department: str | None = None, config: "ExperimentConfig | None" = None) -> ChatResponse:
        trace_id = str(uuid.uuid4())
        start = time.monotonic_ns()

        top_k = config.retrieval.top_k if config else 3
        use_hybrid = config is not None and config.retrieval.mode == "hybrid"

        if use_hybrid:
            chunks = self._retrieval.hybrid_search(question, department=department, limit=top_k)
        else:
            chunks = self._retrieval.search(question, department=department, limit=top_k)

        # access filter (V3)
        if config is not None and config.grounding.access_filter:
            from app.support.grounding import filter_by_access_level, resolve_access_level
            user_access = resolve_access_level(department)
            chunks = filter_by_access_level(chunks, user_access)

        evidence_count = len(chunks)
        route = decide_route(question, evidence_count)
        chunk_ids = ",".join(c.id for c in chunks)

        if route is Route.TICKET:
            reason = "Evidence insufficient or sensitive action requested"
            risk_level = "high" if calculate_risk_score(question) > 0 else "low"
            ticket = ticket_service.create(question, reason=reason, risk_level=risk_level)
            latency_ms = int((time.monotonic_ns() - start) / 1_000_000)
            response = ChatResponse(
                answer="Your request has been forwarded to the support team for handling.",
                citations=[],
                confidence="low",
                route="ticket",
                ticket_id=ticket.id,
                trace_id=trace_id,
                latency_ms=latency_ms,
            )
            self._persist_trace(trace_id, question, chunk_ids, response.answer, response.route, response.confidence, response.ticket_id, latency_ms)
            return response

        citations = [
            Citation(chunk_id=c.id, title=c.title, excerpt=c.content[:200])
            for c in chunks
        ]
        answer = self._build_answer(chunks)

        # grounding check (V3)
        mandatory = config is not None and config.grounding.enabled and config.grounding.mandatory_citations
        if mandatory:
            from app.support.grounding import validate_grounding
            citation_ids = [c.chunk_id for c in citations]
            if not validate_grounding(answer, citation_ids):
                ticket = ticket_service.create(question, reason="Answer grounding failed", risk_level="high")
                latency_ms = int((time.monotonic_ns() - start) / 1_000_000)
                response = ChatResponse(
                    answer="Unable to verify answer against sources. Forwarding to support.",
                    citations=[],
                    confidence="low",
                    route="ticket",
                    ticket_id=ticket.id,
                    trace_id=trace_id,
                    latency_ms=latency_ms,
                )
                self._persist_trace(trace_id, question, chunk_ids, response.answer, response.route, response.confidence, response.ticket_id, latency_ms)
                return response

        latency_ms = int((time.monotonic_ns() - start) / 1_000_000)
        response = ChatResponse(
            answer=answer,
            citations=citations,
            confidence="high" if evidence_count >= 2 else "medium",
            route="answer",
            trace_id=trace_id,
            latency_ms=latency_ms,
        )
        self._persist_trace(trace_id, question, chunk_ids, response.answer, response.route, response.confidence, response.ticket_id, latency_ms)
        return response


support_agent = SupportAgent()
