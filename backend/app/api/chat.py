from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ChatRequest, ChatResponse, SessionResponse
from app.db.postgres import get_db_session

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request, db_session: AsyncSession = Depends(get_db_session)) -> ChatResponse:
    return await request.app.state.chat_service.chat(db_session, payload)


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, request: Request, db_session: AsyncSession = Depends(get_db_session)) -> SessionResponse:
    return await request.app.state.chat_service.get_session_history(db_session, session_id)

