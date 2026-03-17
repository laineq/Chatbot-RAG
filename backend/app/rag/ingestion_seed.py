from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChunkRecord, DocumentRecord
from app.rag.chunker import MarkdownChunker
from app.rag.embeddings import EmbeddingService


def extract_source_name(content: str, fallback: str) -> str:
    for line in content.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return fallback.replace("_", " ").title()


async def ingest_seed_documents(
    db_session: AsyncSession,
    *,
    docs_path: Path,
    embedding_service: EmbeddingService,
    chunker: MarkdownChunker,
) -> dict[str, int]:
    doc_paths = sorted(docs_path.glob("*.md"))
    doc_ids = [path.stem for path in doc_paths]

    if doc_ids:
        await db_session.execute(delete(ChunkRecord).where(ChunkRecord.doc_id.in_(doc_ids)))
        await db_session.execute(delete(DocumentRecord).where(DocumentRecord.doc_id.in_(doc_ids)))

    total_chunks = 0
    total_documents = 0

    for path in doc_paths:
        content = path.read_text(encoding="utf-8")
        doc_id = path.stem
        source_name = extract_source_name(content, doc_id)
        db_session.add(DocumentRecord(doc_id=doc_id, source_name=source_name, doc_type="seed_markdown"))
        await db_session.flush()

        chunk_drafts = chunker.chunk_document(doc_id=doc_id, source_name=source_name, content=content)
        embeddings = await embedding_service.embed_many([draft.text for draft in chunk_drafts])

        for draft, embedding in zip(chunk_drafts, embeddings, strict=True):
            db_session.add(
                ChunkRecord(
                    doc_id=draft.doc_id,
                    section=draft.section,
                    chunk_index=draft.chunk_index,
                    chunk_text=draft.text,
                    token_count=draft.token_count,
                    embedding=embedding,
                )
            )

        total_documents += 1
        total_chunks += len(chunk_drafts)

    await db_session.commit()
    return {"documents": total_documents, "chunks": total_chunks}
