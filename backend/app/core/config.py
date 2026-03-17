from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
import shutil
import subprocess
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["openai", "gemini"]


@dataclass(frozen=True)
class ResolvedProviderCredentials:
    provider: ProviderName
    api_key: str
    source: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Enterprise RAG Chatbot"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    model_provider: Literal["auto", "openai", "gemini"] = "auto"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_api_key: str | None = None
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

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
    def api_key_file_candidates(self) -> tuple[Path, ...]:
        return (
            self.repo_root / "api",
            self.repo_root / "api.rtf",
        )

    @property
    def sync_postgres_url(self) -> str:
        return self.postgres_url

    @property
    def resolved_provider_credentials(self) -> ResolvedProviderCredentials | None:
        if self.model_provider != "auto":
            return self._resolve_provider_credentials(self.model_provider)

        for provider in ("openai", "gemini"):
            credentials = self._resolve_provider_credentials(provider)
            if credentials is not None:
                return credentials

        return None

    @property
    def resolved_model_provider(self) -> ProviderName | None:
        credentials = self.resolved_provider_credentials
        return credentials.provider if credentials is not None else None

    @property
    def resolved_api_key(self) -> str | None:
        credentials = self.resolved_provider_credentials
        return credentials.api_key if credentials is not None else None

    @property
    def active_chat_model(self) -> str | None:
        if self.resolved_model_provider == "openai":
            return self.openai_chat_model
        if self.resolved_model_provider == "gemini":
            return self.gemini_chat_model
        return None

    @property
    def active_embedding_model(self) -> str | None:
        if self.resolved_model_provider == "openai":
            return self.openai_embedding_model
        if self.resolved_model_provider == "gemini":
            return self.gemini_embedding_model
        return None

    def _resolve_provider_credentials(self, provider: ProviderName) -> ResolvedProviderCredentials | None:
        env_key = getattr(self, f"{provider}_api_key")
        direct_match = _match_provider_api_key(provider, env_key or "")
        if direct_match:
            return ResolvedProviderCredentials(
                provider=provider,
                api_key=direct_match,
                source=f"{provider.upper()}_API_KEY",
            )

        for candidate in self.api_key_file_candidates:
            secret = _read_provider_api_key_from_file(candidate, provider=provider)
            if secret:
                return ResolvedProviderCredentials(
                    provider=provider,
                    api_key=secret,
                    source=candidate.name,
                )

        return None


OPENAI_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{20,}")
GEMINI_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_-]{35}")
SUPPORTED_API_KEY_PATTERNS: dict[ProviderName, re.Pattern[str]] = {
    "openai": OPENAI_KEY_PATTERN,
    "gemini": GEMINI_KEY_PATTERN,
}


def _extract_text_content(path: Path) -> str | None:
    try:
        if path.suffix.lower() == ".rtf" and shutil.which("textutil"):
            result = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _read_openai_api_key_from_file(path: Path) -> str | None:
    return _read_provider_api_key_from_file(path, provider="openai")


def _read_gemini_api_key_from_file(path: Path) -> str | None:
    return _read_provider_api_key_from_file(path, provider="gemini")


def _match_provider_api_key(provider: ProviderName, content: str) -> str | None:
    match = SUPPORTED_API_KEY_PATTERNS[provider].search(content)
    if match:
        return match.group(0).strip()
    return None


def _read_provider_api_key_from_file(path: Path, *, provider: ProviderName) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    content = _extract_text_content(path)
    if content is None:
        return None

    return _match_provider_api_key(provider, content)


@lru_cache
def get_settings() -> Settings:
    return Settings()
