from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.routes import chat as chat_routes
from app.routes import conversations as conversation_routes
from app.routes import documents as document_routes
from app.routes import feedback as feedback_routes


class MissingQuery:
    def select(self, _: str) -> "MissingQuery":
        return self

    def eq(self, _column: str, _value: str) -> "MissingQuery":
        return self

    def maybe_single(self) -> "MissingQuery":
        return self

    def execute(self) -> None:
        return None


class MissingClient:
    def table(self, _name: str) -> MissingQuery:
        return MissingQuery()


def _missing_client() -> MissingClient:
    return MissingClient()


def test_missing_document_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(document_routes, "get_supabase", _missing_client)

    response = TestClient(app).get(f"/api/documents/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}


def test_missing_chat_conversation_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(chat_routes, "get_supabase", _missing_client)

    response = TestClient(app).post(
        "/api/chat",
        json={
            "conversation_id": str(uuid4()),
            "question": "What does the document say?",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found."}


def test_missing_conversation_messages_return_404(monkeypatch) -> None:
    monkeypatch.setattr(conversation_routes, "get_supabase", _missing_client)

    response = TestClient(app).get(
        f"/api/conversations/{uuid4()}/messages"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found."}


def test_feedback_for_missing_message_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(feedback_routes, "get_supabase", _missing_client)

    response = TestClient(app).post(
        "/api/feedback",
        json={"message_id": str(uuid4()), "rating": "positive"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Message not found."}
