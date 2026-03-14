from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat import router as chat_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.schemas import (
    ChatResponse,
    Citation,
    FeedbackResponse,
    MessageView,
    SessionResponse,
)
from app.db.postgres import get_db_session


class DummyChatService:
    async def chat(self, db_session, payload):  # noqa: ANN001
        return ChatResponse(
            request_id="req-1234",
            route="rag",
            answer="Hotel reimbursement is capped at 250 USD per night [Travel Policy - Hotel Expenses].",
            citations=[
                Citation(
                    chunk_id=7,
                    source_name="Travel Policy",
                    section="Hotel Expenses",
                    snippet="Hotel reimbursement is capped at 250 USD per night before taxes.",
                )
            ],
        )

    async def get_session_history(self, db_session, session_id):  # noqa: ANN001
        return SessionResponse(
            session_id=session_id,
            messages=[
                MessageView(
                    id="msg-1",
                    role="assistant",
                    content="Hotel reimbursement is capped at 250 USD per night [Travel Policy - Hotel Expenses].",
                    request_id="req-1234",
                    route="rag",
                    citations=[
                        Citation(
                            chunk_id=7,
                            source_name="Travel Policy",
                            section="Hotel Expenses",
                            snippet="Hotel reimbursement is capped at 250 USD per night before taxes.",
                        )
                    ],
                    timestamp="2026-03-14T00:00:00Z",
                )
            ],
        )

    async def submit_feedback(self, db_session, payload):  # noqa: ANN001
        return FeedbackResponse(status="accepted")


class DummyHistoryStore:
    async def ping(self):
        return True, "reachable"


async def override_db_session():
    yield object()


def create_test_app(monkeypatch) -> FastAPI:  # noqa: ANN001
    app = FastAPI()
    app.include_router(chat_router)
    app.include_router(feedback_router)
    app.include_router(health_router)
    app.state.chat_service = DummyChatService()
    app.state.history_store = DummyHistoryStore()
    app.dependency_overrides[get_db_session] = override_db_session

    async def fake_postgres_health():
        return True, "reachable"

    monkeypatch.setattr("app.api.health.check_postgres_health", fake_postgres_health)
    return app


def test_chat_endpoint_contract(monkeypatch) -> None:
    app = create_test_app(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"session_id": "session-1234", "message": "What is the hotel reimbursement cap?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "rag"
    assert payload["request_id"] == "req-1234"
    assert payload["citations"][0]["source_name"] == "Travel Policy"


def test_session_endpoint_contract(monkeypatch) -> None:
    app = create_test_app(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/session/session-1234")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-1234"
    assert payload["messages"][0]["route"] == "rag"


def test_feedback_endpoint_contract(monkeypatch) -> None:
    app = create_test_app(monkeypatch)

    with TestClient(app) as client:
        response = client.post("/feedback", json={"request_id": "req-1234", "rating": "up"})

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


def test_health_endpoint_contract(monkeypatch) -> None:
    app = create_test_app(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["services"]["postgres"]["ok"] is True
    assert payload["services"]["redis"]["ok"] is True
