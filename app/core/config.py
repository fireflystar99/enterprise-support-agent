from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # LLM
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    # Embedding
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # Database
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/support_agent"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    admin_token: str = ""
    user_id: str = "demo"

    # Retrieval
    top_k: int = 3
    chunk_size: int = 800
    chunk_overlap: int = 120

    class Config:
        env_file = PROJECT_ROOT / ".env"
        extra = "ignore"


settings = Settings()
