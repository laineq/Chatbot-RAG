# Backend

FastAPI backend for the enterprise RAG chatbot MVP.

## Quickstart

1. Start infrastructure from the repo root:
   - `docker compose up -d`
2. Create a local environment file:
   - `cp .env.example .env`
3. Install Python dependencies:
   - `cd backend && uv sync --extra dev`
4. Run migrations:
   - `uv run alembic upgrade head`
5. Seed the knowledge base:
   - `uv run python ../scripts/seed_knowledge_base.py`
6. Start the API:
   - `uv run uvicorn app.main:app --reload`

## Tests

- `uv run pytest`

