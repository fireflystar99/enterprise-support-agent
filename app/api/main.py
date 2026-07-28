from fastapi import FastAPI, HTTPException

from app.api.schemas import ChatRequest, ChatResponse
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
    """Return trace info for demo/admin use only."""
    raise HTTPException(status_code=404, detail="Trace storage not yet connected to database")
