import time
import uuid
from fastapi import FastAPI
from app.api.schemas import ChatRequest, ChatResponse, Citation
from app.support.routing import Route, decide_route

app = FastAPI(title="Enterprise Support Agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "enterprise-support-agent"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    trace_id = str(uuid.uuid4())
    start = time.monotonic_ns()

    evidence_count = 2  # placeholder — real retrieval later
    route = decide_route(request.question, evidence_count)

    if route is Route.TICKET:
        ticket_id = str(uuid.uuid4())
        latency_ms = int((time.monotonic_ns() - start) / 1_000_000)
        return ChatResponse(
            answer="Your request has been forwarded to the support team.",
            citations=[],
            confidence="low",
            route="ticket",
            ticket_id=ticket_id,
            trace_id=trace_id,
            latency_ms=latency_ms,
        )

    answer = "Submit receipts within 30 calendar days of the expense date."
    latency_ms = int((time.monotonic_ns() - start) / 1_000_000)
    return ChatResponse(
        answer=answer,
        citations=[Citation(chunk_id="test-1", title="expense-policy", excerpt=answer)],
        confidence="high",
        route="answer",
        trace_id=trace_id,
        latency_ms=latency_ms,
    )
