import logging
import math
import time
from functools import lru_cache

import httpx

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)
MAX_PROVIDER_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class EmbeddingService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self.settings.embedding_batch_size):
            batch = texts[start : start + self.settings.embedding_batch_size]
            embeddings.extend(self._embed(batch))
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        query_text = query.strip()
        if not query_text:
            raise ValueError("The embedding query cannot be empty.")
        return self._embed([query_text])[0]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        self.settings.require_embeddings()
        endpoint = f"{self.settings.llm_api_base.rstrip('/')}/embeddings"
        request_kwargs = {
            "headers": {
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            "json": {
                "model": self.settings.embedding_model,
                "input": texts,
                "dimensions": self.settings.embedding_dimensions,
                "encoding_format": "float",
            },
            "timeout": 60.0,
        }

        for attempt in range(MAX_PROVIDER_ATTEMPTS):
            try:
                response = httpx.post(endpoint, **request_kwargs)
                response.raise_for_status()
                break
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                status_code = (
                    exc.response.status_code
                    if isinstance(exc, httpx.HTTPStatusError)
                    else None
                )
                retryable = (
                    status_code is None or status_code in RETRYABLE_STATUS_CODES
                )
                if not retryable or attempt == MAX_PROVIDER_ATTEMPTS - 1:
                    raise
                delay = 2**attempt
                logger.warning(
                    "Embedding request failed%s; retrying in %d second(s).",
                    f" with HTTP {status_code}" if status_code else "",
                    delay,
                )
                time.sleep(delay)

        try:
            items = sorted(response.json()["data"], key=lambda item: item["index"])
            vectors = [item["embedding"] for item in items]
        except (KeyError, TypeError) as exc:
            raise RuntimeError(
                "The embedding provider returned an invalid response."
            ) from exc

        if len(vectors) != len(texts):
            raise RuntimeError("The embedding provider returned an incomplete batch.")

        return [self._normalize(vector) for vector in vectors]

    def _normalize(self, vector: list[float]) -> list[float]:
        if len(vector) != self.settings.embedding_dimensions:
            raise RuntimeError(
                "The embedding dimension does not match the Supabase vector schema."
            )
        magnitude = math.sqrt(sum(float(value) ** 2 for value in vector))
        if magnitude == 0:
            raise RuntimeError("The embedding provider returned a zero vector.")
        return [float(value) / magnitude for value in vector]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
