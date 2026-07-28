from fastapi import FastAPI
from app.api.schemas import ChatRequest, ChatResponse
from app.support.agent import support_agent

app = FastAPI(title="Enterprise Support Agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "enterprise-support-agent"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return support_agent.handle(request.question, request.department)
