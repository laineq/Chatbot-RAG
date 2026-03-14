# Enterprise RAG Chatbot Architecture

## Overview

This project is a local-demo-first enterprise-style chatbot with:

- A Next.js frontend for session-based chat, citation display, and feedback
- A FastAPI backend that owns orchestration, retrieval, guardrails, and persistence
- PostgreSQL with `pgvector` for documents, chunks, logs, and analytics
- Redis for short-term session memory
- OpenAI for generation and embeddings

## Request Flow

1. The frontend sends `session_id` and `message` to `POST /chat`.
2. The backend validates input and runs prompt-injection rules.
3. The orchestrator loads recent session history from Redis.
4. The router decides whether the message should use RAG or the general route.
5. If RAG is selected, the retriever embeds the query and searches chunk vectors in Postgres.
6. The prompt builder combines system instructions, recent memory, and retrieved chunks.
7. The LLM client generates an answer.
8. Output guardrails enforce evidence, citations, and leakage refusal.
9. The backend stores messages, logs, and feedback metadata in Postgres and refreshes Redis history.
10. The frontend renders the answer, route badge, and citations.

## Core Modules

- `backend/app/api`: FastAPI routers and request/response schemas
- `backend/app/orchestrator`: routing, prompt assembly, and end-to-end chat workflow
- `backend/app/rag`: chunking, embeddings, ingestion, and retrieval
- `backend/app/memory`: Redis-backed short-term session history
- `backend/app/guardrails`: rule-based input and output checks
- `backend/app/db`: SQLAlchemy models, database session setup, and vector search
- `frontend/components`: the chat shell and enterprise-style UI components

## Boundaries

Included in the MVP:

- Multi-turn chat
- RAG over pre-seeded documents
- Session persistence and logs
- Citations and feedback
- Basic rule-based guardrails

Explicitly excluded from the MVP:

- File upload
- SQL execution tools
- Reranking and hybrid search
- Authentication and permissions
- Agent workflows and tool orchestration

