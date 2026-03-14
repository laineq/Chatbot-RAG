from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AnalyticsOverviewResponse
from app.db.postgres import get_db_session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def analytics_overview(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> AnalyticsOverviewResponse:
    return await request.app.state.analytics_service.get_overview(db_session)
