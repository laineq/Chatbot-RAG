from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from app.rag.chunker import MarkdownChunker
from app.rag.ingestion_seed import ingest_seed_documents


@pytest.mark.asyncio
async def test_ingest_seed_documents_flushes_document_before_chunks(tmp_path: Path) -> None:
    docs_path = tmp_path / "docs"
    docs_path.mkdir()
    (docs_path / "travel_policy.md").write_text(
        "# Travel Policy\n\nHotel reimbursement is capped at 250 USD per night.",
        encoding="utf-8",
    )

    chunker = MarkdownChunker()
    chunk_drafts = chunker.chunk_document(
        doc_id="travel_policy",
        source_name="Travel Policy",
        content="# Travel Policy\n\nHotel reimbursement is capped at 250 USD per night.",
    )

    embedding_service = Mock()
    embedding_service.embed_many = AsyncMock(return_value=[[0.1] * 1536 for _ in chunk_drafts])

    db_session = AsyncMock()
    db_session.add = Mock()

    report = await ingest_seed_documents(
        db_session,
        docs_path=docs_path,
        embedding_service=embedding_service,
        chunker=chunker,
    )

    assert report == {"documents": 1, "chunks": len(chunk_drafts)}
    db_session.flush.assert_awaited_once()
    db_session.commit.assert_awaited_once()
