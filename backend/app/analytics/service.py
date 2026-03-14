from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AnalyticsOverviewResponse, AnalyticsSummary, MetricCount, RecentRequestMetric
from app.db.models import (
    ChunkRecord,
    DocumentRecord,
    FeedbackRecord,
    MessageRecord,
    RequestLogRecord,
    RetrievalLogRecord,
    SessionRecord,
)


class AnalyticsService:
    async def get_overview(self, db_session: AsyncSession) -> AnalyticsOverviewResponse:
        total_sessions = await self._count_rows(db_session, SessionRecord)
        total_messages = await self._count_rows(db_session, MessageRecord)
        total_requests = await self._count_rows(db_session, RequestLogRecord)
        total_feedback = await self._count_rows(db_session, FeedbackRecord)
        negative_feedback = await self._count_feedback(db_session, "down")
        fallback_requests = await self._count_requests_by_route(db_session, "fallback")
        refusal_requests = await self._count_requests_by_route(db_session, "refusal")
        seeded_documents = await self._count_rows(db_session, DocumentRecord)
        total_chunks = await self._count_rows(db_session, ChunkRecord)

        average_latency_ms = await db_session.scalar(select(func.avg(RequestLogRecord.latency_ms)))

        route_breakdown = await self._group_counts(db_session, RequestLogRecord.route)
        risk_breakdown = await self._group_counts(db_session, RequestLogRecord.input_risk_level)
        feedback_breakdown = await self._group_counts(db_session, FeedbackRecord.rating)
        reason_breakdown = await self._group_counts(
            db_session,
            RequestLogRecord.reason_code,
            exclude_nulls=True,
            limit=6,
        )
        recent_requests = await self._recent_requests(db_session)
        top_sources = await self._top_sources(db_session)

        return AnalyticsOverviewResponse(
            summary=AnalyticsSummary(
                total_sessions=total_sessions,
                total_messages=total_messages,
                total_requests=total_requests,
                total_feedback=total_feedback,
                negative_feedback=negative_feedback,
                average_latency_ms=float(average_latency_ms) if average_latency_ms is not None else None,
                fallback_requests=fallback_requests,
                refusal_requests=refusal_requests,
                seeded_documents=seeded_documents,
                total_chunks=total_chunks,
            ),
            route_breakdown=route_breakdown,
            risk_breakdown=risk_breakdown,
            feedback_breakdown=feedback_breakdown,
            reason_breakdown=reason_breakdown,
            top_sources=top_sources,
            recent_requests=recent_requests,
        )

    async def _count_rows(self, db_session: AsyncSession, model) -> int:  # noqa: ANN001
        return int((await db_session.scalar(select(func.count()).select_from(model))) or 0)

    async def _count_feedback(self, db_session: AsyncSession, rating: str) -> int:
        return int(
            (
                await db_session.scalar(
                    select(func.count()).select_from(FeedbackRecord).where(FeedbackRecord.rating == rating)
                )
            )
            or 0
        )

    async def _count_requests_by_route(self, db_session: AsyncSession, route: str) -> int:
        return int(
            (
                await db_session.scalar(
                    select(func.count()).select_from(RequestLogRecord).where(RequestLogRecord.route == route)
                )
            )
            or 0
        )

    async def _group_counts(
        self,
        db_session: AsyncSession,
        column,
        *,
        exclude_nulls: bool = False,
        limit: int | None = None,
    ) -> list[MetricCount]:
        statement = select(column.label("label"), func.count().label("count")).group_by(column).order_by(func.count().desc())
        if exclude_nulls:
            statement = statement.where(column.is_not(None))
        if limit is not None:
            statement = statement.limit(limit)
        rows = (await db_session.execute(statement)).all()
        return [MetricCount(label=str(row.label), count=int(row.count)) for row in rows if row.label is not None]

    async def _recent_requests(self, db_session: AsyncSession) -> list[RecentRequestMetric]:
        request_rows = (
            await db_session.execute(
                select(RequestLogRecord)
                .order_by(RequestLogRecord.created_at.desc())
                .limit(8)
            )
        ).scalars().all()

        request_ids = [row.request_id for row in request_rows]
        retrieval_rows = (
            await db_session.execute(
                select(RetrievalLogRecord).where(RetrievalLogRecord.request_id.in_(request_ids))
            )
        ).scalars().all() if request_ids else []
        retrieval_by_request = {row.request_id: row for row in retrieval_rows}

        return [
            RecentRequestMetric(
                request_id=row.request_id,
                session_id=row.session_id,
                route=row.route,
                risk_level=row.input_risk_level,
                reason_code=row.reason_code,
                latency_ms=row.latency_ms,
                created_at=row.created_at,
                retrieved_chunk_count=len(retrieval_by_request[row.request_id].retrieved_chunk_ids)
                if row.request_id in retrieval_by_request
                else 0,
                top_score=max(retrieval_by_request[row.request_id].scores)
                if row.request_id in retrieval_by_request and retrieval_by_request[row.request_id].scores
                else None,
            )
            for row in request_rows
        ]

    async def _top_sources(self, db_session: AsyncSession) -> list[MetricCount]:
        retrieval_rows = (
            await db_session.execute(
                select(RetrievalLogRecord)
                .order_by(RetrievalLogRecord.created_at.desc())
                .limit(100)
            )
        ).scalars().all()

        chunk_ids = sorted({chunk_id for row in retrieval_rows for chunk_id in row.retrieved_chunk_ids})
        if not chunk_ids:
            return []

        chunk_source_rows = (
            await db_session.execute(
                select(ChunkRecord.chunk_id, DocumentRecord.source_name)
                .join(DocumentRecord, DocumentRecord.doc_id == ChunkRecord.doc_id)
                .where(ChunkRecord.chunk_id.in_(chunk_ids))
            )
        ).all()
        chunk_to_source = {row.chunk_id: row.source_name for row in chunk_source_rows}
        source_counter = Counter(
            chunk_to_source[chunk_id]
            for row in retrieval_rows
            for chunk_id in row.retrieved_chunk_ids
            if chunk_id in chunk_to_source
        )

        return [
            MetricCount(label=label, count=count)
            for label, count in source_counter.most_common(5)
        ]
