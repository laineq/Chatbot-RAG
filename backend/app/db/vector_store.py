from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChunkRecord, DocumentRecord


async def search_chunks(
    db_session: AsyncSession,
    query_embedding: list[float],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    distance = ChunkRecord.embedding.cosine_distance(query_embedding)
    score = (1 - distance).label("score")

    statement = (
        select(
            ChunkRecord.chunk_id,
            ChunkRecord.doc_id,
            DocumentRecord.source_name,
            ChunkRecord.section,
            ChunkRecord.chunk_text,
            score,
        )
        .join(DocumentRecord, DocumentRecord.doc_id == ChunkRecord.doc_id)
        .order_by(distance)
        .limit(top_k)
    )

    rows = (await db_session.execute(statement)).all()
    return [
        {
            "chunk_id": row.chunk_id,
            "doc_id": row.doc_id,
            "source_name": row.source_name,
            "section": row.section,
            "text": row.chunk_text,
            "score": float(row.score),
        }
        for row in rows
    ]

