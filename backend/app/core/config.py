from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Enterprise RAG Chatbot"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    postgres_url: str = "postgresql+psycopg://chatbot:chatbot@localhost:5432/chatbot"
    redis_url: str = "redis://localhost:6379/0"

    message_max_chars: int = 4000
    memory_max_messages: int = 10
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    embedding_dimensions: int = 1536

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def prompt_dir(self) -> Path:
        return self.repo_root / "backend" / "app" / "prompts"

    @property
    def knowledge_base_path(self) -> Path:
        return self.repo_root / "data" / "docs"

    @property
    def sync_postgres_url(self) -> str:
        return self.postgres_url.replace("+psycopg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()

