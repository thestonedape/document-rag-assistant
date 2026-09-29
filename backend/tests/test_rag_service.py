import asyncio
from uuid import UUID

import httpx

from app.config import Settings
from app.models import RetrievedChunk
from app.services.rag_service import RagService


def _chunk(chunk_id: str, title: str, page: int) -> RetrievedChunk:
    ordinal = 1 if chunk_id == "one" else 2
    return RetrievedChunk(
        chunk_id=str(UUID(int=ordinal)),
        document_id=str(UUID(int=ordinal + 10)),
        document_title=title,
        page_number=page,
        text=f"Evidence from {title}.",
        similarity=0.8,
        source_url="https://example.com/source.pdf",
    )


def test_context_assigns_stable_source_ids() -> None:
    context, sources = RagService.build_context(
        [_chunk("one", "Rules", 4), _chunk("two", "Handbook", 9)]
    )

    assert list(sources) == ["S1", "S2"]
    assert "[S1]" in context
    assert "Document: Rules" in context
    assert "Page: 9" in context


def test_validation_removes_unknown_citations_and_returns_only_used_sources() -> None:
    chunks = [_chunk("one", "Rules", 4), _chunk("two", "Handbook", 9)]
    _, sources = RagService.build_context(chunks)

    answer, citations = RagService.validate_citations(
        "The threshold applies [S2]. Unknown claim [S99]. Repeated [S2].",
        sources,
    )

    assert "[S99]" not in answer
    assert [citation.source_id for citation in citations] == ["S2"]
    assert citations[0].page_number == 9


def test_validation_expands_grouped_citations_and_removes_unknown_sources() -> None:
    chunks = [_chunk("one", "Rules", 4), _chunk("two", "Handbook", 9)]
    _, sources = RagService.build_context(chunks)

    answer, citations = RagService.validate_citations(
        "The documents agree [S1, S2, S99].",
        sources,
    )

    assert answer == "The documents agree [S1] [S2]."
    assert [citation.source_id for citation in citations] == ["S1", "S2"]


def test_chat_completion_retries_transient_http_errors(monkeypatch) -> None:
    attempts = 0
    delays: list[int] = []

    class FakeAsyncClient:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, url: str, **_kwargs) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            request = httpx.Request("POST", url)
            if attempts == 1:
                return httpx.Response(502, request=request)
            return httpx.Response(
                200,
                request=request,
                json={"choices": [{"message": {"content": "Answer [S1]."}}]},
            )

    async def fake_sleep(delay: int) -> None:
        delays.append(delay)

    monkeypatch.setattr(
        "app.services.rag_service.httpx.AsyncClient",
        FakeAsyncClient,
    )
    monkeypatch.setattr("app.services.rag_service.asyncio.sleep", fake_sleep)
    settings = Settings(
        llm_api_key="test-key",
        llm_model="provider/chat-model",
    )

    answer = asyncio.run(RagService(settings)._generate("Question", "Context"))

    assert answer == "Answer [S1]."
    assert attempts == 2
    assert delays == [1]
