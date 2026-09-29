import logging
import re
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from ..config import get_settings
from ..schemas import (
    DocumentResponse,
    DocumentStatusResponse,
    UploadResponse,
)
from ..services.chunk_service import ChunkService
from ..services.embedding_service import get_embedding_service
from ..services.ingestion_service import mark_ingestion_failed
from ..services.pdf_service import extract_pages
from ..supabase_client import get_supabase

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)
PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}
READ_SIZE = 1024 * 1024


def _safe_stem(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-_")
    return cleaned[:80] or "document"


def _document_or_404(document_id: UUID) -> dict:
    response = (
        get_supabase()
        .table("documents")
        .select("*")
        .eq("id", str(document_id))
        .maybe_single()
        .execute()
    )
    if response is None or not response.data:
        raise HTTPException(status_code=404, detail="Document not found.")
    return response.data


def process_document(document_id: str, pdf_bytes: bytes, storage_path: str) -> None:
    client = get_supabase()
    try:
        pages, page_count = extract_pages(pdf_bytes)
        chunks = ChunkService().create_chunks(pages)
        embeddings = get_embedding_service().embed_documents(
            [chunk.text for chunk in chunks]
        )

        records = [
            {
                "document_id": document_id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "embedding": embedding,
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        for start in range(0, len(records), 100):
            client.table("document_chunks").insert(
                records[start : start + 100]
            ).execute()

        (
            client.table("documents")
            .update(
                {
                    "status": "completed",
                    "page_count": page_count,
                    "error_message": None,
                }
            )
            .eq("id", document_id)
            .execute()
        )
    except Exception:
        logger.exception("Document ingestion failed for %s.", document_id)
        mark_ingestion_failed(
            client,
            get_settings(),
            document_id,
            storage_path,
            "Unable to process the uploaded PDF.",
        )


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
) -> UploadResponse:
    settings = get_settings()
    filename = file.filename or ""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if suffix != "pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    if file.content_type not in PDF_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Invalid PDF MIME type.")

    data = bytearray()
    try:
        while chunk := await file.read(READ_SIZE):
            data.extend(chunk)
            if len(data) > settings.max_pdf_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"PDF exceeds the {settings.max_pdf_size_mb} MB limit.",
                )
    finally:
        await file.close()

    pdf_bytes = bytes(data)
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

    client = get_supabase()
    document_id = uuid4()
    storage_path = (
        f"{document_id}/{_safe_stem(filename)}-{uuid4().hex[:8]}.pdf"
    )
    document_title = (title or filename.rsplit(".", 1)[0]).strip()
    if not document_title:
        document_title = "Untitled document"

    try:
        (
            client.storage.from_(settings.supabase_storage_bucket)
            .upload(
                path=storage_path,
                file=pdf_bytes,
                file_options={"content-type": "application/pdf", "upsert": "false"},
            )
        )
        (
            client.table("documents")
            .insert(
                {
                    "id": str(document_id),
                    "title": document_title[:200],
                    "original_filename": filename,
                    "storage_path": storage_path,
                    "file_size": len(pdf_bytes),
                    "status": "processing",
                }
            )
            .execute()
        )
    except Exception as exc:
        try:
            client.storage.from_(settings.supabase_storage_bucket).remove([storage_path])
        except Exception:
            logger.warning("Unable to clean up failed upload %s.", storage_path)
        raise HTTPException(
            status_code=502,
            detail="Unable to store the uploaded PDF.",
        ) from exc

    background_tasks.add_task(
        process_document,
        str(document_id),
        pdf_bytes,
        storage_path,
    )
    return UploadResponse(
        document_id=document_id,
        status="processing",
        message="Document uploaded and processing started.",
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents() -> list[dict]:
    response = (
        get_supabase()
        .table("documents")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID) -> dict:
    return _document_or_404(document_id)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(document_id: UUID) -> dict:
    document = _document_or_404(document_id)
    return {
        "id": document["id"],
        "status": document["status"],
        "page_count": document.get("page_count"),
        "error_message": document.get("error_message"),
    }


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: UUID) -> None:
    settings = get_settings()
    client = get_supabase()
    document = _document_or_404(document_id)

    try:
        client.storage.from_(settings.supabase_storage_bucket).remove(
            [document["storage_path"]]
        )
        (
            client.table("documents")
            .delete()
            .eq("id", str(document_id))
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to delete the document.",
        ) from exc
