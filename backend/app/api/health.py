from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.schemas import HealthResponse, HealthServiceStatus
from app.db.postgres import check_postgres_health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    postgres_ok, postgres_detail = await check_postgres_health()
    redis_ok, redis_detail = await request.app.state.history_store.ping()
    services = {
        "postgres": HealthServiceStatus(ok=postgres_ok, detail=postgres_detail),
        "redis": HealthServiceStatus(ok=redis_ok, detail=redis_detail),
    }
    status = "ok" if all(service.ok for service in services.values()) else "degraded"
    return HealthResponse(status=status, services=services)

