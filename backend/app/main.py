import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .routes import chat, conversations, documents, feedback
from .services.ingestion_service import mark_ingestion_failed
from .supabase_client import get_supabase

settings = get_settings()
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def fail_interrupted_ingestions() -> None:
    """Mark documents stuck in 'processing' as failed.

    Ingestion runs in-process; a Render free-tier spin-down or deploy
    kills it mid-flight, which would otherwise leave the document
    showing 'processing' forever.
    """
    try:
        client = get_supabase()
        response = (
            client
            .table("documents")
            .select("id,storage_path")
            .eq("status", "processing")
            .execute()
        )
        interrupted_documents = response.data or []
        for document in interrupted_documents:
            mark_ingestion_failed(
                client,
                settings,
                document["id"],
                document.get("storage_path"),
                (
                    "Processing was interrupted by a server restart. "
                    "Please upload the document again."
                ),
            )
        if interrupted_documents:
            logger.warning(
                "Cleaned up and marked %d interrupted ingestion(s) as failed.",
                len(interrupted_documents),
            )
    except Exception:
        logger.exception("Unable to reconcile interrupted ingestions at startup.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.supabase_url and settings.supabase_service_role_key:
        fail_interrupted_ingestions()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(feedback.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/ready")
def readiness() -> dict[str, str]:
    try:
        (
            get_supabase()
            .table("documents")
            .select("id")
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Supabase readiness check failed.")
        raise HTTPException(
            status_code=503,
            detail="Supabase connection is unavailable.",
        ) from exc
    return {"status": "ready", "service": settings.app_name}


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logging.getLogger(__name__).exception(
        "Unhandled error while processing %s",
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )
