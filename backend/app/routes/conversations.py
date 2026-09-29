from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
)
from ..supabase_client import get_supabase

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _conversation_exists(conversation_id: UUID) -> None:
    response = (
        get_supabase()
        .table("conversations")
        .select("id")
        .eq("id", str(conversation_id))
        .maybe_single()
        .execute()
    )
    if response is None or not response.data:
        raise HTTPException(status_code=404, detail="Conversation not found.")


@router.post("", response_model=ConversationResponse, status_code=201)
def create_conversation(payload: ConversationCreate) -> dict:
    response = (
        get_supabase()
        .table("conversations")
        .insert({"title": payload.title or "New conversation"})
        .execute()
    )
    return response.data[0]


@router.get("", response_model=list[ConversationResponse])
def list_conversations() -> list[dict]:
    response = (
        get_supabase()
        .table("conversations")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def list_messages(conversation_id: UUID) -> list[dict]:
    _conversation_exists(conversation_id)
    response = (
        get_supabase()
        .table("messages")
        .select("*")
        .eq("conversation_id", str(conversation_id))
        .order("created_at")
        .execute()
    )
    return response.data or []


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID) -> None:
    _conversation_exists(conversation_id)
    try:
        (
            get_supabase()
            .table("conversations")
            .delete()
            .eq("id", str(conversation_id))
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to delete the conversation.",
        ) from exc
