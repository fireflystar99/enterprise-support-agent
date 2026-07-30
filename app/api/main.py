from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.api.rate_limit import RateLimitMiddleware
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    TicketStatus,
    TicketStatusUpdateRequest,
)
from app.api.sse import encode_sse
from app.core.config import settings, validate_production_config
from app.core.experiment_config import load_config
from app.db.models import QueryTrace
from app.db.session import SessionLocal
from app.retrieval.reranker import warm_reranker_model
from app.retrieval.service import warm_embedding_model
from app.support.agent import support_agent
from app.support.tickets import TicketDatabaseError, ticket_service


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # 在开始监听请求前完成生产配置校验和模型预热，避免首个用户请求承担加载成本。
    validate_production_config()
    warm_embedding_model()
    if settings.app_env != "demo":
        warm_reranker_model()
    yield


# 限流放在 API 边界，避免异常流量进入检索模型和数据库。
app = FastAPI(title="Enterprise Support Agent", lifespan=lifespan)
# 表示每个窗口最多 60 次请求，避免接口被短时间滥用。
app.add_middleware(RateLimitMiddleware, max_requests=60, window_seconds=60)

# 配置在进程启动时加载；每次聊天请求复用同一份经过校验的实验配置。
_production_config = load_config("production")


def _verify_admin(x_admin_token: str | None = Header(None)) -> None:
    # Trace 与工单包含内部信息，因此所有管理接口都必须显式携带管理员令牌。
    expected = settings.admin_token
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured")
    if x_admin_token != expected:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "enterprise-support-agent"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    # API 层只负责协议转换；检索、安全路由和持久化都由 SupportAgent 编排。
    return support_agent.handle(request.question, request.department, config=_production_config)


@app.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """以 SSE 转发 Agent 的增量回答与最终元数据。"""
    events = (
        encode_sse(event, payload)
        for event, payload in support_agent.stream(
            request.question, request.department, config=_production_config
        )
    )
    return StreamingResponse(events, media_type="text/event-stream")


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
    try:
        record = ticket_service.get(ticket_id)
    except TicketDatabaseError as exc:
        raise HTTPException(status_code=503, detail="Ticket service unavailable") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return record.model_dump()


@app.get("/tickets")
def list_tickets(
    status: TicketStatus | None = None,
    risk_level: str | None = None,
    x_admin_token: str | None = Header(None),
) -> list[dict]:
    _verify_admin(x_admin_token)
    try:
        records = ticket_service.list(status=status, risk_level=risk_level)
    except TicketDatabaseError as exc:
        raise HTTPException(status_code=503, detail="Ticket service unavailable") from exc
    return [
        record.model_dump(mode="json")
        for record in records
    ]


@app.patch("/tickets/{ticket_id}")
def update_ticket_status(
    ticket_id: str,
    request: TicketStatusUpdateRequest,
    x_admin_token: str | None = Header(None),
) -> dict:
    _verify_admin(x_admin_token)
    try:
        record = ticket_service.update_status(ticket_id, request.status)
    except TicketDatabaseError as exc:
        raise HTTPException(status_code=503, detail="Ticket service unavailable") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return record.model_dump(mode="json")
