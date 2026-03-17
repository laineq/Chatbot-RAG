from unittest.mock import AsyncMock, Mock

import pytest

from app.core.config import Settings
from app.db.models import SessionRecord
from app.orchestrator.chat_service import ChatService


def build_chat_service() -> ChatService:
    return ChatService(
        settings=Settings(),
        history_store=Mock(),
        llm_client=Mock(model_name="test-model"),
        retriever=Mock(),
        prompt_builder=Mock(),
    )


@pytest.mark.asyncio
async def test_ensure_session_flushes_new_session() -> None:
    service = build_chat_service()
    db_session = AsyncMock()
    db_session.add = Mock()
    db_session.get.return_value = None

    await service._ensure_session(db_session, "session-1234")

    added_record = db_session.add.call_args.args[0]
    assert isinstance(added_record, SessionRecord)
    assert added_record.session_id == "session-1234"
    db_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_session_skips_flush_for_existing_session() -> None:
    service = build_chat_service()
    db_session = AsyncMock()
    db_session.add = Mock()
    db_session.get.return_value = SessionRecord(session_id="session-1234")

    await service._ensure_session(db_session, "session-1234")

    db_session.add.assert_not_called()
    db_session.flush.assert_not_awaited()
