import math

import httpx

from app.config import Settings
from app.services.embedding_service import EmbeddingService


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "data": [
                {"index": 1, "embedding": [0.0, 3.0, 4.0]},
                {"index": 0, "embedding": [1.0, 0.0, 0.0]},
            ]
        }


def test_openrouter_embeddings_are_ordered_and_normalized(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url: str, **kwargs) -> FakeResponse:
        captured["url"] = url
        captured["json"] = kwargs["json"]
        captured["authorization"] = kwargs["headers"]["Authorization"]
        return FakeResponse()

    monkeypatch.setattr("app.services.embedding_service.httpx.post", fake_post)
    settings = Settings(
        llm_api_key="test-key",
        llm_model="provider/chat-model",
        embedding_dimensions=3,
        embedding_batch_size=2,
    )

    embeddings = EmbeddingService(settings).embed_documents(["first", "second"])

    assert captured["url"] == "https://openrouter.ai/api/v1/embeddings"
    assert captured["authorization"] == "Bearer test-key"
    assert captured["json"]["dimensions"] == 3
    assert embeddings[0] == [1.0, 0.0, 0.0]
    assert math.isclose(embeddings[1][1], 0.6)
    assert math.isclose(embeddings[1][2], 0.8)


def test_embedding_request_retries_transient_http_errors(monkeypatch) -> None:
    attempts = 0
    delays: list[int] = []

    def fake_post(url: str, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                request=httpx.Request("POST", url),
            )
        return FakeResponse()

    monkeypatch.setattr("app.services.embedding_service.httpx.post", fake_post)
    monkeypatch.setattr(
        "app.services.embedding_service.time.sleep",
        delays.append,
    )
    settings = Settings(
        llm_api_key="test-key",
        embedding_dimensions=3,
    )

    embeddings = EmbeddingService(settings).embed_documents(["retry me", "now"])

    assert attempts == 2
    assert delays == [1]
    assert len(embeddings) == 2
