from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import Settings


class OpenAILLMClient:
    def __init__(self, settings: Settings) -> None:
        self.model_name = settings.openai_chat_model
        self._client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def generate(self, prompt: str) -> str:
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        response = await self._client.responses.create(
            model=self.model_name,
            input=prompt,
        )
        return (response.output_text or "").strip()

