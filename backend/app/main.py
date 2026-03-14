from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.chat import router as chat_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.logger import configure_logging
from app.llm.client import OpenAILLMClient
from app.memory.redis_history import RedisHistoryStore
from app.orchestrator.chat_service import ChatService
from app.orchestrator.prompt_builder import PromptBuilder
from app.rag.embeddings import OpenAIEmbeddingService
from app.rag.retriever import RAGRetriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    history_store = RedisHistoryStore(settings.redis_url, max_messages=settings.memory_max_messages)
    llm_client = OpenAILLMClient(settings)
    embedding_service = OpenAIEmbeddingService(settings)
    retriever = RAGRetriever(embedding_service, top_k=settings.retrieval_top_k)
    prompt_builder = PromptBuilder(settings.prompt_dir)

    app.state.history_store = history_store
    app.state.chat_service = ChatService(
        settings=settings,
        history_store=history_store,
        llm_client=llm_client,
        retriever=retriever,
        prompt_builder=prompt_builder,
    )

    yield

    await history_store.close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(feedback_router)
    app.include_router(health_router)

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=settings.app_env == "development")


if __name__ == "__main__":
    run()

