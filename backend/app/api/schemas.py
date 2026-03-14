from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ResponseRoute = Literal["rag", "general", "fallback", "refusal"]
FeedbackRating = Literal["up", "down"]


class Citation(BaseModel):
    chunk_id: int
    source_name: str
    section: str
    snippet: str


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    request_id: str
    route: ResponseRoute
    answer: str
    citations: list[Citation] = Field(default_factory=list)


class MessageView(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    request_id: str | None = None
    route: ResponseRoute | None = None
    citations: list[Citation] = Field(default_factory=list)
    timestamp: datetime


class SessionResponse(BaseModel):
    session_id: str
    messages: list[MessageView] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)
    rating: FeedbackRating
    comment: str | None = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    status: Literal["accepted"]


class HealthServiceStatus(BaseModel):
    ok: bool
    detail: str


class SetupCheckStatus(BaseModel):
    ok: bool
    detail: str
    required: bool = True


class KnowledgeBaseStatus(BaseModel):
    seeded: bool
    document_count: int | None = None
    chunk_count: int | None = None
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    services: dict[str, HealthServiceStatus]
    setup_checks: dict[str, SetupCheckStatus] = Field(default_factory=dict)
    knowledge_base: KnowledgeBaseStatus
    warnings: list[str] = Field(default_factory=list)
