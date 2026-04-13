from __future__ import annotations

import time
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    FeedbackRequest,
    FeedbackResponse,
    MessageView,
    SessionResponse,
)
from app.core.config import Settings
from app.core.logger import get_logger
from app.db.models import FeedbackRecord, MessageRecord, RequestLogRecord, RetrievalLogRecord, SessionRecord
from app.guardrails.input_guard import InputGuardError, inspect_message, validate_chat_payload
from app.guardrails.output_guard import (
    build_fallback_answer,
    build_refusal_answer,
    citations_from_chunks,
    enforce_output_guardrails,
)
from app.llm.client import LLMClient, ProviderError
from app.memory.redis_history import RedisHistoryStore
from app.orchestrator.prompt_builder import PromptBuilder
from app.orchestrator.query_rewriter import QueryRewriter
from app.orchestrator.router import decide_route
from app.rag.reranker import ChunkReranker
from app.rag.retriever import RAGRetriever, RetrievedChunk
from app.tools.tavily_search import TavilySearchService

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
        query_rewriter: QueryRewriter,
        reranker: ChunkReranker,
        tavily_search: TavilySearchService,
    ) -> None:
        self.settings = settings
        self.history_store = history_store
        self.llm_client = llm_client
        self.retriever = retriever
        self.prompt_builder = prompt_builder
        self.query_rewriter = query_rewriter
        self.reranker = reranker
        self.tavily_search = tavily_search
        self._trace_cache: dict[str, dict[str, object]] = {}

    async def chat_with_trace(self, db_session: AsyncSession, payload: ChatRequest) -> dict[str, object]:
        response = await self.chat(db_session, payload)
        trace = self._trace_cache.pop(response.request_id, None) or {}
        return {
            "request_id": response.request_id,
            "answer": response.answer,
            "route": response.route,
            "retrieved_doc_ids": trace.get("retrieved_doc_ids", []),
            "context": trace.get("context", ""),
            "citations": [citation.model_dump() for citation in response.citations],
        }

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
        citations: list[Citation] = []
        retrieved_chunks: list[RetrievedChunk] = []
        web_citations: list[Citation] = []
        reranked_local = False
        query_used_for_retrieval = normalized_message

        if guard_result.risk_level == "high":
            route = "refusal"
            answer = build_refusal_answer()
            reason_code = "prompt_injection_high"
        else:
            query_plan = await self.query_rewriter.rewrite(normalized_message, history)
            route_decision = decide_route(
                normalized_message,
                history,
                rewrite=query_plan,
                forced_rag=guard_result.risk_level == "medium",
            )
            route = route_decision.route
            reason_code = route_decision.reason_code
            query_used_for_retrieval = query_plan.local_query

            try:
                if route in {"rag_local", "rag_hybrid"}:
                    retrieved_chunks = await self.retriever.search(
                        db_session,
                        query_plan.local_query,
                        top_k=self.settings.local_retrieval_top_k,
                    )
                    if self.settings.enable_reranking and retrieved_chunks:
                        reranked_local = True
                        retrieved_chunks = await self.reranker.rerank(
                            query_plan.local_query,
                            retrieved_chunks,
                            top_n=self.settings.local_rerank_top_n,
                        )

                if route in {"rag_web", "rag_hybrid"}:
                    web_results = await self.tavily_search.search(
                        query_plan.web_query,
                        needs_recency=query_plan.needs_recency,
                    )
                    web_citations = [result.to_citation(index) for index, result in enumerate(web_results)]
                    query_used_for_retrieval = query_plan.web_query

                local_citations = citations_from_chunks(retrieved_chunks, limit=self.settings.local_rerank_top_n)
                evidence_citations = [*local_citations, *web_citations]

                if route == "rag_local":
                    if not retrieved_chunks or max(chunk.score for chunk in retrieved_chunks) < self.settings.retrieval_score_threshold:
                        route = "fallback"
                        answer = build_fallback_answer()
                        reason_code = "insufficient_local_evidence"
                    else:
                        answer, route, citations, reason_code = await self._generate_rag_answer(
                            message=normalized_message,
                            history=history,
                            route=route,
                            retrieved_chunks=retrieved_chunks,
                            web_citations=web_citations,
                            evidence_citations=evidence_citations,
                            reason_code=reason_code,
                        )
                elif route == "rag_web":
                    if not web_citations:
                        route = "fallback"
                        answer = build_fallback_answer()
                        reason_code = "missing_web_evidence"
                    else:
                        answer, route, citations, reason_code = await self._generate_rag_answer(
                            message=normalized_message,
                            history=history,
                            route=route,
                            retrieved_chunks=retrieved_chunks,
                            web_citations=web_citations,
                            evidence_citations=evidence_citations,
                            reason_code=reason_code,
                        )
                elif route == "rag_hybrid":
                    if not evidence_citations:
                        route = "fallback"
                        answer = build_fallback_answer()
                        reason_code = "insufficient_hybrid_evidence"
                    else:
                        answer, route, citations, reason_code = await self._generate_rag_answer(
                            message=normalized_message,
                            history=history,
                            route=route,
                            retrieved_chunks=retrieved_chunks,
                            web_citations=web_citations,
                            evidence_citations=evidence_citations,
                            reason_code=reason_code,
                        )
                elif route == "refusal":
                    answer = build_refusal_answer()
                elif route == "fallback":
                    answer = build_fallback_answer()
                else:
                    prompt = self.prompt_builder.build_general_prompt(message=normalized_message, history=history)
                    answer = await self.llm_client.generate(prompt)
                    output_decision = enforce_output_guardrails(
                        route="general",
                        answer=answer,
                        retrieved_chunks=[],
                        evidence_citations=None,
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

        reason_code = self._annotate_reason_code(reason_code, route=route, reranked_local=reranked_local, citations=citations)

        try:
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
                retrieval_query=query_used_for_retrieval,
                reason_code=reason_code,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
            )
        except Exception as exc:  # pragma: no cover - depends on runtime infrastructure
            logger.warning("chat persistence unavailable, continuing without DB logging: %s", exc)

        await self.history_store.append_messages(
            payload.session_id,
            [
                {"role": "user", "content": normalized_message},
                {"role": "assistant", "content": answer},
            ],
        )

        self._trace_cache[request_id] = {
            "retrieved_doc_ids": self._collect_retrieved_doc_ids(retrieved_chunks, web_citations),
            "context": self._build_retrieved_context(retrieved_chunks, web_citations),
        }
        return ChatResponse(request_id=request_id, route=route, answer=answer, citations=citations)

    @staticmethod
    def _collect_retrieved_doc_ids(retrieved_chunks: list[RetrievedChunk], web_citations: list[Citation]) -> list[str]:
        doc_ids: list[str] = []
        for chunk in retrieved_chunks:
            if chunk.doc_id:
                doc_ids.append(chunk.doc_id)
        for citation in web_citations:
            if citation.url:
                doc_ids.append(citation.url)
            elif citation.source_name:
                doc_ids.append(citation.source_name)
        return list(dict.fromkeys(doc_ids))

    @staticmethod
    def _build_retrieved_context(retrieved_chunks: list[RetrievedChunk], web_citations: list[Citation]) -> str:
        context_parts: list[str] = []
        for chunk in retrieved_chunks:
            if chunk.text.strip():
                context_parts.append(f"[local:{chunk.doc_id}] {chunk.text.strip()}")
        for citation in web_citations:
            snippet = citation.snippet.strip()
            source_id = citation.url or citation.source_name
            if snippet:
                context_parts.append(f"[web:{source_id}] {snippet}")
        return "\n\n".join(context_parts)

    async def _generate_rag_answer(
        self,
        *,
        message: str,
        history: list[dict[str, str]],
        route: str,
        retrieved_chunks: list[RetrievedChunk],
        web_citations: list[Citation],
        evidence_citations: list[Citation],
        reason_code: str | None,
    ) -> tuple[str, str, list[Citation], str | None]:
        prompt = self.prompt_builder.build_rag_prompt(
            message=message,
            history=history,
            retrieved_chunks=retrieved_chunks,
            web_citations=web_citations,
        )
        answer = await self.llm_client.generate(prompt)
        output_decision = enforce_output_guardrails(
            route=route,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            evidence_citations=evidence_citations,
            score_threshold=self.settings.retrieval_score_threshold,
            retry_allowed=True,
        )
        if output_decision.retry_required:
            strict_prompt = self.prompt_builder.build_rag_prompt(
                message=message,
                history=history,
                retrieved_chunks=retrieved_chunks,
                web_citations=web_citations,
                strict=True,
            )
            answer = await self.llm_client.generate(strict_prompt)
            output_decision = enforce_output_guardrails(
                route=route,
                answer=answer,
                retrieved_chunks=retrieved_chunks,
                evidence_citations=evidence_citations,
                score_threshold=self.settings.retrieval_score_threshold,
                retry_allowed=False,
            )

        return (
            output_decision.answer,
            output_decision.route,
            output_decision.citations,
            output_decision.reason_code or reason_code,
        )

    @staticmethod
    def _annotate_reason_code(
        reason_code: str | None,
        *,
        route: str,
        reranked_local: bool,
        citations: list[Citation],
    ) -> str | None:
        parts = [reason_code] if reason_code else []
        if route in {"rag_local", "rag_hybrid"}:
            parts.append("local_evidence")
        if route in {"rag_web", "rag_hybrid"}:
            parts.append("web_evidence")
        if reranked_local:
            parts.append("reranked_local")
        if not citations and route.startswith("rag"):
            parts.append("evidence_weak")
        return "|".join(dict.fromkeys(parts)) if parts else None

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
        citations: list[Citation],
        risk_level: str,
        retrieved_chunks: list[RetrievedChunk],
        retrieval_query: str,
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
                query=retrieval_query,
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
