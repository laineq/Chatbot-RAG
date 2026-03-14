from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.schemas import HealthResponse
from app.core.config import get_settings
from app.core.runtime_checks import collect_health_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    return await collect_health_response(request.app.state.history_store, get_settings())


@router.get("/ready")
async def readiness_check(request: Request) -> JSONResponse:
    payload = await collect_health_response(request.app.state.history_store, get_settings())
    status_code = 200 if payload.status == "ok" else 503
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))
