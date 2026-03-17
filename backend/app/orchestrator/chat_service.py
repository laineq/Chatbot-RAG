from __future__ import annotations

import time
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    MessageView,
    SessionResponse,
)
from app.core.config import Settings
from app.core.logger import get_logger
from app.db.models import FeedbackRecord, MessageRecord, RequestLogRecord, RetrievalLogRecord, SessionRecord
from app.guardrails.input_guard import InputGuardError, inspect_message, validate_chat_payload
from app.guardrails.output_guard import build_fallback_answer, build_refusal_answer, enforce_output_guardrails
from app.llm.client import LLMClient, ProviderError
from app.memory.redis_history import RedisHistoryStore
from app.orchestrator.prompt_builder import PromptBuilder
from app.orchestrator.router import decide_route
from app.rag.retriever import RAGRetriever, RetrievedChunk

logger = get_logger(__name__)


class ChatService:
    def __init__(
        self,
        *,
        settings: Settings,
        history_store: RedisHistoryStore,
        llm_client: LLMClient,
        retriever: RAGRetriever,
        prompt_builder: PromptBuilder,
    ) -> None:
        self.settings = settings
        self.history_store = history_store
        self.llm_client = llm_client
        self.retriever = retriever
        self.prompt_builder = prompt_builder

    async def chat(self, db_session: AsyncSession, payload: ChatRequest) -> ChatResponse:
        request_id = str(uuid4())
        started_at = time.perf_counter()

        try:
            normalized_message = validate_chat_payload(
                payload.session_id,
                payload.message,
                max_chars=self.settings.message_max_chars,
            )
        except InputGuardError as exc:
            raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc

        guard_result = inspect_message(normalized_message)
        history = await self.history_store.get_history(payload.session_id)
        route = "general"
        answer = ""
        reason_code: str | None = None
        citations = []
        retrieved_chunks: list[RetrievedChunk] = []

        if guard_result.risk_level == "high":
            route = "refusal"
            answer = build_refusal_answer()
            reason_code = "prompt_injection_high"
        else:
            route_decision = decide_route(
                normalized_message,
                history,
                forced_rag=guard_result.risk_level == "medium",
            )
            route = route_decision.route
            reason_code = route_decision.reason_code

            try:
                if route == "rag":
                    retrieved_chunks = await self.retriever.search(db_session, normalized_message)

                    if not retrieved_chunks or max(chunk.score for chunk in retrieved_chunks) < self.settings.retrieval_score_threshold:
                        route = "fallback"
                        answer = build_fallback_answer()
                        reason_code = "insufficient_evidence"
                    else:
                        prompt = self.prompt_builder.build_rag_prompt(
                            message=normalized_message,
                            history=history,
                            retrieved_chunks=retrieved_chunks,
                        )
                        answer = await self.llm_client.generate(prompt)
                        output_decision = enforce_output_guardrails(
                            route="rag",
                            answer=answer,
                            retrieved_chunks=retrieved_chunks,
                            score_threshold=self.settings.retrieval_score_threshold,
                            retry_allowed=True,
                        )
                        if output_decision.retry_required:
                            strict_prompt = self.prompt_builder.build_rag_prompt(
                                message=normalized_message,
                                history=history,
                                retrieved_chunks=retrieved_chunks,
                                strict=True,
                            )
                            answer = await self.llm_client.generate(strict_prompt)
                            output_decision = enforce_output_guardrails(
                                route="rag",
                                answer=answer,
                                retrieved_chunks=retrieved_chunks,
                                score_threshold=self.settings.retrieval_score_threshold,
                                retry_allowed=False,
                            )

                        route = output_decision.route
                        answer = output_decision.answer
                        citations = output_decision.citations
                        reason_code = output_decision.reason_code or reason_code
                else:
                    prompt = self.prompt_builder.build_general_prompt(message=normalized_message, history=history)
                    answer = await self.llm_client.generate(prompt)
                    output_decision = enforce_output_guardrails(
                        route="general",
                        answer=answer,
                        retrieved_chunks=[],
                        score_threshold=self.settings.retrieval_score_threshold,
                        retry_allowed=False,
                    )
                    route = output_decision.route
                    answer = output_decision.answer
                    reason_code = output_decision.reason_code or reason_code
            except ProviderError as exc:
                logger.warning("provider unavailable: %s", exc)
                route = "fallback"
                answer = (
                    "The assistant is not fully configured yet. Set a valid OPENAI_API_KEY or GEMINI_API_KEY "
                    "in the environment, or place a supported key in ./api or ./api.rtf to enable retrieval "
                    "and generation."
                )
                reason_code = "provider_unavailable"

        await self._persist_chat(
            db_session=db_session,
            session_id=payload.session_id,
            request_id=request_id,
            user_message=normalized_message,
            answer=answer,
            route=route,
            citations=citations,
            risk_level=guard_result.risk_level,
            retrieved_chunks=retrieved_chunks,
            reason_code=reason_code,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
        )

        await self.history_store.append_messages(
            payload.session_id,
            [
                {"role": "user", "content": normalized_message},
                {"role": "assistant", "content": answer},
            ],
        )

        return ChatResponse(request_id=request_id, route=route, answer=answer, citations=citations)

    async def get_session_history(self, db_session: AsyncSession, session_id: str) -> SessionResponse:
        statement = (
            select(MessageRecord)
            .where(MessageRecord.session_id == session_id)
            .order_by(MessageRecord.timestamp.asc())
        )
        rows = (await db_session.execute(statement)).scalars().all()
        return SessionResponse(
            session_id=session_id,
            messages=[
                MessageView(
                    id=row.id,
                    role=row.role,
                    content=row.content,
                    request_id=row.request_id,
                    route=row.route,
                    citations=row.citations,
                    timestamp=row.timestamp,
                )
                for row in rows
            ],
        )

    async def submit_feedback(self, db_session: AsyncSession, payload: FeedbackRequest) -> FeedbackResponse:
        request_log = await db_session.get(RequestLogRecord, payload.request_id)
        if request_log is None:
            raise HTTPException(status_code=404, detail={"code": "request_not_found", "message": "Request ID not found."})

        existing = await db_session.get(FeedbackRecord, payload.request_id)
        if existing is None:
            db_session.add(FeedbackRecord(request_id=payload.request_id, rating=payload.rating, comment=payload.comment))
        else:
            existing.rating = payload.rating
            existing.comment = payload.comment

        await db_session.commit()
        return FeedbackResponse(status="accepted")

    async def _persist_chat(
        self,
        *,
        db_session: AsyncSession,
        session_id: str,
        request_id: str,
        user_message: str,
        answer: str,
        route: str,
        citations: list[object],
        risk_level: str,
        retrieved_chunks: list[RetrievedChunk],
        reason_code: str | None,
        latency_ms: int,
    ) -> None:
        await self._ensure_session(db_session, session_id)

        db_session.add(
            MessageRecord(
                id=str(uuid4()),
                session_id=session_id,
                role="user",
                content=user_message,
                request_id=None,
                route=None,
                citations=[],
            )
        )
        db_session.add(
            MessageRecord(
                id=str(uuid4()),
                session_id=session_id,
                role="assistant",
                content=answer,
                request_id=request_id,
                route=route,
                citations=[citation.model_dump() for citation in citations],
            )
        )
        db_session.add(
            RequestLogRecord(
                request_id=request_id,
                session_id=session_id,
                route=route,
                latency_ms=latency_ms,
                model_name=self.llm_client.model_name,
                input_risk_level=risk_level,
                reason_code=reason_code,
            )
        )
        db_session.add(
            RetrievalLogRecord(
                request_id=request_id,
                session_id=session_id,
                query=user_message,
                retrieved_chunk_ids=[chunk.chunk_id for chunk in retrieved_chunks],
                scores=[chunk.score for chunk in retrieved_chunks],
                route=route,
            )
        )

        await db_session.commit()

    async def _ensure_session(self, db_session: AsyncSession, session_id: str) -> None:
        session = await db_session.get(SessionRecord, session_id)
        if session is None:
            db_session.add(SessionRecord(session_id=session_id))
            await db_session.flush()
