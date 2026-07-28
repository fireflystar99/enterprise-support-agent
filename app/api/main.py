from fastapi import FastAPI

app = FastAPI(title="Enterprise Support Agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "enterprise-support-agent"}
