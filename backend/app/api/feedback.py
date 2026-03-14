from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import FeedbackRequest, FeedbackResponse
from app.db.postgres import get_db_session

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    payload: FeedbackRequest,
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> FeedbackResponse:
    return await request.app.state.chat_service.submit_feedback(db_session, payload)

