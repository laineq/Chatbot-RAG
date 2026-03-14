# Backend

FastAPI backend for the enterprise RAG chatbot MVP.

## Quickstart

Recommended:

1. Run the repo preflight:
   - `make preflight`
2. Start infrastructure:
   - `make infra-up`
3. Install backend dependencies:
   - `make backend-install`
4. Run migrations:
   - `make migrate`
5. Seed the knowledge base:
   - `make seed`
6. Start the API:
   - `make backend-dev`

Raw commands:

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

## Runtime Endpoints

- `GET /health`: service reachability, prompt/docs checks, and knowledge-base status
- `GET /ready`: returns `200` when the local demo path is ready, otherwise `503`
