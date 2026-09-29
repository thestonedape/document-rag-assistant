import logging

from supabase import Client

from ..config import Settings

logger = logging.getLogger(__name__)


def mark_ingestion_failed(
    client: Client,
    settings: Settings,
    document_id: str,
    storage_path: str | None,
    error_message: str,
) -> None:
    try:
        (
            client.table("document_chunks")
            .delete()
            .eq("document_id", document_id)
            .execute()
        )
    except Exception:
        logger.exception(
            "Unable to delete partial chunks for document %s.",
            document_id,
        )

    if storage_path:
        try:
            client.storage.from_(settings.supabase_storage_bucket).remove(
                [storage_path]
            )
        except Exception:
            logger.exception(
                "Unable to delete the stored PDF for document %s.",
                document_id,
            )

    try:
        (
            client.table("documents")
            .update(
                {
                    "status": "failed",
                    "error_message": error_message,
                }
            )
            .eq("id", document_id)
            .execute()
        )
    except Exception:
        logger.exception("Unable to mark document %s as failed.", document_id)
