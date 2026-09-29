import logging
import re
from uuid import UUID

from supabase import Client

from ..config import Settings, get_settings
from ..models import RetrievedChunk
from ..supabase_client import get_supabase
from .embedding_service import EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        client: Client | None = None,
        embedding_service: EmbeddingService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or get_supabase()
        self.embedding_service = embedding_service or get_embedding_service()

    @staticmethod
    def _keyword_score(question: str, text: str) -> float:
        # \w+ instead of [a-z0-9]+ so non-Latin scripts also contribute
        # keyword overlap instead of silently scoring zero.
        query_terms = {
            term
            for term in re.findall(r"\w+", question.lower())
            if len(term) > 2
        }
        if not query_terms:
            return 0.0
        text_terms = set(re.findall(r"\w+", text.lower()))
        return len(query_terms & text_terms) / len(query_terms)

    @staticmethod
    def _is_overview_question(question: str) -> bool:
        normalized = " ".join(re.findall(r"[a-z0-9]+", question.lower()))
        if re.search(r"\bs?ummar(?:y|ize|ise)\b|\boverview\b", normalized):
            return True

        document_terms = {
            "document",
            "documents",
            "pdf",
            "file",
            "paper",
            "source",
            "sources",
        }
        overview_terms = {
            "about",
            "conclusion",
            "conclusions",
            "cover",
            "covers",
            "idea",
            "ideas",
            "point",
            "points",
            "subject",
            "subjects",
            "theme",
            "themes",
            "topic",
            "topics",
        }
        terms = set(normalized.split())
        return bool(terms & document_terms and terms & overview_terms)

    def _filter_matches(self, question: str, rows: list[dict]) -> list[dict]:
        matches = [
            row
            for row in rows
            if float(row.get("similarity", 0.0)) >= self.settings.min_similarity
        ]
        if matches or not rows or not self._is_overview_question(question):
            return matches

        logger.info(
            "Using the nearest chunks for a document-overview question because "
            "none of %d candidates met MIN_SIMILARITY %.3f.",
            len(rows),
            self.settings.min_similarity,
        )
        return rows

    def _signed_url(self, storage_path: str | None) -> str | None:
        if not storage_path:
            return None
        try:
            payload = (
                self.client.storage.from_(self.settings.supabase_storage_bucket)
                .create_signed_url(storage_path, 3600)
            )
            return payload.get("signedURL") or payload.get("signedUrl")
        except Exception:
            return None

    def retrieve(
        self,
        question: str,
        document_ids: list[UUID],
        top_k: int,
    ) -> list[RetrievedChunk]:
        query_embedding = self.embedding_service.embed_query(question)
        rpc_count = top_k * 3 if self.settings.hybrid_search else top_k
        rpc_response = self.client.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": rpc_count,
                "filter_document_ids": (
                    [str(document_id) for document_id in document_ids]
                    if document_ids
                    else None
                ),
            },
        ).execute()

        rows = rpc_response.data or []
        matches = self._filter_matches(question, rows)
        if not matches:
            logger.info(
                "No document chunks met MIN_SIMILARITY %.3f for the question.",
                self.settings.min_similarity,
            )
            return []

        matched_document_ids = sorted({row["document_id"] for row in matches})
        document_response = (
            self.client.table("documents")
            .select("id,title,storage_path")
            .in_("id", matched_document_ids)
            .execute()
        )
        documents = {
            row["id"]: row for row in (document_response.data or [])
        }

        scored_rows: list[tuple[float, dict]] = []
        for row in matches:
            vector_score = float(row["similarity"])
            if self.settings.hybrid_search:
                keyword_score = self._keyword_score(question, row["text"])
                final_score = 0.8 * vector_score + 0.2 * keyword_score
            else:
                final_score = vector_score
            scored_rows.append((final_score, row))

        scored_rows.sort(key=lambda item: item[0], reverse=True)
        storage_urls: dict[str, str | None] = {}
        retrieved: list[RetrievedChunk] = []

        for _, row in scored_rows[:top_k]:
            document = documents.get(row["document_id"], {})
            storage_path = document.get("storage_path")
            if row["document_id"] not in storage_urls:
                storage_urls[row["document_id"]] = self._signed_url(storage_path)
            retrieved.append(
                RetrievedChunk(
                    chunk_id=row["id"],
                    document_id=row["document_id"],
                    document_title=document.get("title", "Untitled document"),
                    page_number=int(row["page_number"]),
                    text=row["text"],
                    similarity=float(row["similarity"]),
                    source_url=storage_urls[row["document_id"]],
                )
            )

        return retrieved
