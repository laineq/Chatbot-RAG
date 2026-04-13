from __future__ import annotations

import json
from typing import Any
import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisHistoryStore:
    def __init__(self, redis_url: str, *, max_messages: int) -> None:
        self._client = Redis.from_url(redis_url, decode_responses=True)
        self.max_messages = max_messages
        self._memory_store: dict[str, list[dict[str, Any]]] = {}

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}:history"

    async def get_history(self, session_id: str) -> list[dict[str, Any]]:
        try:
            raw = await self._client.get(self._key(session_id))
            if not raw:
                return []
            return json.loads(raw)
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("redis history unavailable, using in-memory fallback: %s", exc)
            return list(self._memory_store.get(session_id, []))

    async def append_messages(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        history = await self.get_history(session_id)
        history.extend(messages)
        trimmed = history[-self.max_messages :]
        try:
            await self._client.set(self._key(session_id), json.dumps(trimmed))
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("redis history unavailable, writing in-memory fallback: %s", exc)
            self._memory_store[session_id] = trimmed

    async def ping(self) -> tuple[bool, str]:
        try:
            await self._client.ping()
            return True, "reachable"
        except Exception as exc:  # pragma: no cover - environment dependent
            return False, str(exc)

    async def close(self) -> None:
        await self._client.aclose()

