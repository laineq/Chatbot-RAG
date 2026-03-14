from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

from app.api.schemas import HealthResponse, HealthServiceStatus, KnowledgeBaseStatus, SetupCheckStatus
from app.core.config import Settings
from app.db.postgres import check_postgres_health, get_engine


def _required_file_check(path: Path, detail: str) -> SetupCheckStatus:
    exists = path.exists()
    return SetupCheckStatus(ok=exists, detail=detail if exists else f"Missing: {path}", required=True)


def _optional_check(ok: bool, detail: str) -> SetupCheckStatus:
    return SetupCheckStatus(ok=ok, detail=detail, required=False)


async def collect_knowledge_base_status(settings: Settings, postgres_ok: bool) -> KnowledgeBaseStatus:
    docs_path = settings.knowledge_base_path
    markdown_docs = sorted(docs_path.glob("*.md")) if docs_path.exists() else []

    if not postgres_ok:
        return KnowledgeBaseStatus(
            seeded=False,
            detail=f"Found {len(markdown_docs)} seed document files locally, but PostgreSQL is not reachable.",
        )

    try:
        async with get_engine().connect() as connection:
            document_count = int((await connection.execute(text("SELECT COUNT(*) FROM documents"))).scalar_one())
            chunk_count = int((await connection.execute(text("SELECT COUNT(*) FROM chunks"))).scalar_one())
    except Exception as exc:  # pragma: no cover - runtime infra dependent
        return KnowledgeBaseStatus(
            seeded=False,
            detail=f"Could not inspect knowledge base tables: {exc}",
        )

    seeded = document_count > 0 and chunk_count > 0
    detail = (
        f"Knowledge base ready with {document_count} documents and {chunk_count} chunks."
        if seeded
        else f"Knowledge base tables are empty. Found {len(markdown_docs)} local seed files; run migrations and the seed script."
    )
    return KnowledgeBaseStatus(
        seeded=seeded,
        document_count=document_count,
        chunk_count=chunk_count,
        detail=detail,
    )


async def collect_health_response(history_store, settings: Settings) -> HealthResponse:
    postgres_ok, postgres_detail = await check_postgres_health()
    redis_ok, redis_detail = await history_store.ping()

    services = {
        "postgres": HealthServiceStatus(ok=postgres_ok, detail=postgres_detail),
        "redis": HealthServiceStatus(ok=redis_ok, detail=redis_detail),
    }

    setup_checks = {
        "python_version": SetupCheckStatus(
            ok=sys.version_info >= (3, 11),
            detail=f"Running Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            required=True,
        ),
        "openai_api_key": _optional_check(bool(settings.openai_api_key), "OPENAI_API_KEY configured" if settings.openai_api_key else "OPENAI_API_KEY is not set."),
        "general_prompt": _required_file_check(settings.prompt_dir / "general_v1.txt", "General prompt found"),
        "rag_prompt": _required_file_check(settings.prompt_dir / "rag_answer_v1.txt", "RAG prompt found"),
        "seed_docs_path": _required_file_check(settings.knowledge_base_path, "Seed docs directory found"),
    }

    knowledge_base = await collect_knowledge_base_status(settings, postgres_ok)

    warnings = [check.detail for check in setup_checks.values() if not check.ok and not check.required]
    if not knowledge_base.seeded:
        warnings.append(knowledge_base.detail)

    required_ok = all(service.ok for service in services.values()) and all(
        check.ok for check in setup_checks.values() if check.required
    )
    status = "ok" if required_ok and knowledge_base.seeded else "degraded"

    return HealthResponse(
        status=status,
        services=services,
        setup_checks=setup_checks,
        knowledge_base=knowledge_base,
        warnings=warnings,
    )
