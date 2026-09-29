from time import perf_counter
from uuid import UUID

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from ..config import get_settings
from ..schemas import ChatRequest, ChatResponse
from ..services.rag_service import RagService
from ..services.retrieval_service import RetrievalService
from ..supabase_client import get_supabase

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _ensure_conversation(conversation_id: UUID | None, question: str) -> str:
    client = get_supabase()
    if conversation_id:
        response = (
            client.table("conversations")
            .select("id")
            .eq("id", str(conversation_id))
            .maybe_single()
            .execute()
        )
        if response is None or not response.data:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return str(conversation_id)

    response = (
        client.table("conversations")
        .insert({"title": question[:80]})
        .execute()
    )
    return response.data[0]["id"]


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    started_at = perf_counter()
    settings = get_settings()
    client = get_supabase()
    conversation_id = await run_in_threadpool(
        _ensure_conversation,
        request.conversation_id,
        request.question,
    )

    await run_in_threadpool(
        lambda: client.table("messages")
        .insert(
            {
                "conversation_id": conversation_id,
                "role": "user",
                "content": request.question,
                "citations": [],
            }
        )
        .execute()
    )

    try:
        chunks = await run_in_threadpool(
            RetrievalService().retrieve,
            request.question,
            request.document_ids,
            request.top_k or settings.top_k,
        )
        answer, citations, insufficient = await RagService().answer(
            request.question,
            chunks,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to generate an answer.",
        ) from exc

    latency_ms = round((perf_counter() - started_at) * 1000)
    assistant_response = await run_in_threadpool(
        lambda: client.table("messages")
        .insert(
            {
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": answer,
                "citations": [
                    citation.model_dump(mode="json") for citation in citations
                ],
                "latency_ms": latency_ms,
            }
        )
        .execute()
    )

    return ChatResponse(
        conversation_id=conversation_id,
        message_id=assistant_response.data[0]["id"],
        answer=answer,
        citations=citations,
        latency_ms=latency_ms,
        insufficient_evidence=insufficient,
    )
