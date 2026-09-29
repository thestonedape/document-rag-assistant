from fastapi import APIRouter, HTTPException

from ..schemas import FeedbackCreate, FeedbackResponse
from ..supabase_client import get_supabase

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse, status_code=201)
def create_feedback(payload: FeedbackCreate) -> dict:
    client = get_supabase()
    message_response = (
        client.table("messages")
        .select("id,role")
        .eq("id", str(payload.message_id))
        .maybe_single()
        .execute()
    )
    if message_response is None or not message_response.data:
        raise HTTPException(status_code=404, detail="Message not found.")
    if message_response.data["role"] != "assistant":
        raise HTTPException(
            status_code=400,
            detail="Feedback can only be submitted for assistant messages.",
        )

    try:
        response = (
            client.table("feedback")
            .insert(
                {
                    "message_id": str(payload.message_id),
                    "rating": payload.rating.value,
                    "comment": payload.comment,
                }
            )
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to save feedback.",
        ) from exc
    return response.data[0]
