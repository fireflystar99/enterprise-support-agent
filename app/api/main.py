from fastapi import FastAPI, HTTPException, Header

from app.api.rate_limit import RateLimitMiddleware
from app.api.schemas import ChatRequest, ChatResponse
from app.core.config import settings
from app.core.experiment_config import load_config
from app.db.models import QueryTrace
from app.db.session import SessionLocal
from app.support.agent import support_agent

app = FastAPI(title="Enterprise Support Agent")
app.add_middleware(RateLimitMiddleware, max_requests=60, window_seconds=60)

_production_config = load_config("production")


def _verify_admin(x_admin_token: str | None = Header(None)) -> None:
    expected = settings.admin_token
    if expected and x_admin_token != expected:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "enterprise-support-agent"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return support_agent.handle(request.question, request.department, config=_production_config)


@app.get("/traces/{trace_id}")
def get_trace(trace_id: str, x_admin_token: str | None = Header(None)) -> dict:
    _verify_admin(x_admin_token)
    session = SessionLocal()
    try:
        trace = session.query(QueryTrace).filter(QueryTrace.id == trace_id).first()
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return {
            "id": str(trace.id),
            "route": trace.route,
            "confidence": trace.confidence,
            "ticket_id": trace.ticket_id,
            "latency_ms": trace.latency_ms,
            "created_at": trace.created_at.isoformat() if trace.created_at else None,
        }
    finally:
        session.close()


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str, x_admin_token: str | None = Header(None)) -> dict:
    _verify_admin(x_admin_token)
    from app.support.tickets import ticket_service
    record = ticket_service.get(ticket_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return record.model_dump()
