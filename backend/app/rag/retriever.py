from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.vector_store import search_chunks
from app.rag.embeddings import EmbeddingService


class RetrievedChunk(BaseModel):
    chunk_id: int
    doc_id: str
    source_name: str
    section: str
    text: str
    score: float


class RAGRetriever:
    def __init__(self, embedding_service: EmbeddingService, *, top_k: int) -> None:
        self.embedding_service = embedding_service
        self.top_k = top_k

    async def search(self, db_session: AsyncSession, query: str) -> list[RetrievedChunk]:
        query_embedding = await self.embedding_service.embed_text(query)
        rows = await search_chunks(db_session, query_embedding, top_k=self.top_k)
        return [RetrievedChunk(**row) for row in rows]
