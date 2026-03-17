from __future__ import annotations

from google import genai
from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings


class ProviderError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.provider = settings.resolved_model_provider
        self.model_name = settings.active_chat_model
        api_key = settings.resolved_api_key
        self._openai_client = AsyncOpenAI(api_key=api_key) if self.provider == "openai" and api_key else None
        self._gemini_client = genai.Client(api_key=api_key) if self.provider == "gemini" and api_key else None

    async def generate(self, prompt: str) -> str:
        if self.provider == "openai":
            return await self._generate_openai(prompt)
        if self.provider == "gemini":
            return await self._generate_gemini(prompt)

        raise ProviderError(
            "No supported AI API key is configured. Set OPENAI_API_KEY or GEMINI_API_KEY, "
            "or place a supported key in ./api or ./api.rtf."
        )

    async def _generate_openai(self, prompt: str) -> str:
        if self._openai_client is None or self.model_name is None:
            raise ProviderError(
                "OpenAI is not configured. Set OPENAI_API_KEY or place an OpenAI key in ./api or ./api.rtf."
            )

        try:
            response = await self._openai_client.responses.create(
                model=self.model_name,
                input=prompt,
            )
        except OpenAIError as exc:
            raise ProviderError(str(exc)) from exc

        return (response.output_text or "").strip()

    async def _generate_gemini(self, prompt: str) -> str:
        if self._gemini_client is None or self.model_name is None:
            raise ProviderError(
                "Gemini is not configured. Set GEMINI_API_KEY or place a Gemini key in ./api or ./api.rtf."
            )

        try:
            response = await self._gemini_client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
        except Exception as exc:  # pragma: no cover - provider runtime dependent
            raise ProviderError(str(exc)) from exc

        return (getattr(response, "text", "") or "").strip()


OpenAILLMClient = LLMClient
