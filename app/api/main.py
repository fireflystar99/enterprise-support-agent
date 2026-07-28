from fastapi import FastAPI, HTTPException

from app.api.schemas import ChatRequest, ChatResponse
from app.db.session import SessionLocal
from app.db.models import QueryTrace
from app.support.agent import support_agent

app = FastAPI(title="Enterprise Support Agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "enterprise-support-agent"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return support_agent.handle(request.question, request.department)


@app.get("/traces/{trace_id}")
def get_trace(trace_id: str) -> dict:
    session = SessionLocal()
    try:
        trace = session.query(QueryTrace).filter(QueryTrace.id == trace_id).first()
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return {
            "id": str(trace.id),
            "question": trace.question,
            "retrieved_chunk_ids": trace.retrieved_chunk_ids,
            "answer": trace.answer,
            "route": trace.route,
            "confidence": trace.confidence,
            "ticket_id": trace.ticket_id,
            "latency_ms": trace.latency_ms,
            "created_at": trace.created_at.isoformat() if trace.created_at else None,
        }
    finally:
        session.close()


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    from app.support.tickets import ticket_service
    record = ticket_service.get(ticket_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return record.model_dump()
