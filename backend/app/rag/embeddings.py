from __future__ import annotations

from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings
from app.llm.client import ProviderError


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self.provider = settings.resolved_model_provider
        self.model_name = settings.active_embedding_model
        self.dimensions = settings.embedding_dimensions
        api_key = settings.resolved_api_key
        self._openai_client = AsyncOpenAI(api_key=api_key) if self.provider == "openai" and api_key else None
        self._gemini_client = genai.Client(api_key=api_key) if self.provider == "gemini" and api_key else None

    async def embed_text(self, text: str) -> list[float]:
        if self.provider == "gemini":
            return (await self._embed_gemini([text], task_type="RETRIEVAL_QUERY"))[0]
        return (await self.embed_many([text]))[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "openai":
            return await self._embed_openai(texts)
        if self.provider == "gemini":
            return await self._embed_gemini(texts, task_type="RETRIEVAL_DOCUMENT")

        raise ProviderError(
            "No supported AI API key is configured. Set OPENAI_API_KEY or GEMINI_API_KEY, "
            "or place a supported key in ./api or ./api.rtf."
        )

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        if self._openai_client is None or self.model_name is None:
            raise ProviderError(
                "OpenAI is not configured. Set OPENAI_API_KEY or place an OpenAI key in ./api or ./api.rtf."
            )

        try:
            response = await self._openai_client.embeddings.create(model=self.model_name, input=texts)
        except OpenAIError as exc:
            raise ProviderError(str(exc)) from exc

        return [item.embedding for item in response.data]

    async def _embed_gemini(self, texts: list[str], *, task_type: str) -> list[list[float]]:
        if self._gemini_client is None or self.model_name is None:
            raise ProviderError(
                "Gemini is not configured. Set GEMINI_API_KEY or place a Gemini key in ./api or ./api.rtf."
            )

        try:
            response = await self._gemini_client.aio.models.embed_content(
                model=self.model_name,
                contents=texts,
                config=genai_types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self.dimensions,
                ),
            )
        except Exception as exc:  # pragma: no cover - provider runtime dependent
            raise ProviderError(str(exc)) from exc

        return [embedding.values for embedding in response.embeddings]


OpenAIEmbeddingService = EmbeddingService
