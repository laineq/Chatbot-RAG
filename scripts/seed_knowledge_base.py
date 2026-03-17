from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.db.postgres import get_sessionmaker
from app.rag.chunker import MarkdownChunker
from app.rag.embeddings import EmbeddingService
from app.rag.ingestion_seed import ingest_seed_documents


async def main() -> None:
    settings = get_settings()
    embedding_service = EmbeddingService(settings)
    chunker = MarkdownChunker()

    async with get_sessionmaker()() as db_session:
        report = await ingest_seed_documents(
            db_session,
            docs_path=settings.knowledge_base_path,
            embedding_service=embedding_service,
            chunker=chunker,
        )
        print(f"Seeded {report['documents']} documents and {report['chunks']} chunks.")


if __name__ == "__main__":
    asyncio.run(main())
