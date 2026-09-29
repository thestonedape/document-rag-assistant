from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentStatus(str, Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_filename: str
    file_size: int | None = None
    page_count: int | None = None
    status: DocumentStatus
    error_message: str | None = None
    created_at: datetime


class DocumentStatusResponse(BaseModel):
    id: UUID
    status: DocumentStatus
    page_count: int | None = None
    error_message: str | None = None


class UploadResponse(BaseModel):
    document_id: UUID
    status: DocumentStatus
    message: str


class Citation(BaseModel):
    source_id: str
    document_id: UUID
    document_title: str
    page_number: int
    chunk_id: UUID
    text: str
    similarity: float
    source_url: str | None = None


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    question: str = Field(min_length=2, max_length=4000)
    document_ids: list[UUID] = Field(default_factory=list)
    top_k: int | None = Field(default=None, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty.")
        return value


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    citations: list[Citation]
    latency_ms: int
    insufficient_evidence: bool


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ConversationResponse(BaseModel):
    id: UUID
    title: str | None = None
    created_at: datetime


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    citations: list[Citation] = Field(default_factory=list)
    latency_ms: int | None = None
    created_at: datetime


class FeedbackRating(str, Enum):
    positive = "positive"
    negative = "negative"


class FeedbackCreate(BaseModel):
    message_id: UUID
    rating: FeedbackRating
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    id: UUID
    message_id: UUID
    rating: FeedbackRating
    comment: str | None = None
    created_at: datetime

