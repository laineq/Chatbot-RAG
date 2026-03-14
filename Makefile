.PHONY: preflight infra-up infra-down backend-install frontend-install migrate seed backend-dev frontend-dev test

preflight:
	python3 scripts/preflight.py

infra-up:
	docker compose up -d

infra-down:
	docker compose down

backend-install:
	cd backend && uv sync --extra dev

frontend-install:
	cd frontend && npm install

migrate:
	cd backend && uv run alembic upgrade head

seed:
	cd backend && uv run python ../scripts/seed_knowledge_base.py

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload

frontend-dev:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest
	cd frontend && npm run test

