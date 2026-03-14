from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import Settings


class OpenAIEmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self.model_name = settings.openai_embedding_model
        self._client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_many([text]))[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        response = await self._client.embeddings.create(model=self.model_name, input=texts)
        return [item.embedding for item in response.data]

