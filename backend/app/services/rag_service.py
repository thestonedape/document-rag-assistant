import asyncio
import logging
import re

import httpx

from ..config import Settings, get_settings
from ..models import RetrievedChunk
from ..prompts import (
    INSUFFICIENT_EVIDENCE_ANSWER,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from ..schemas import Citation

CITATION_PATTERN = re.compile(r"\[(S\d+(?:\s*,\s*S\d+)*)\]")
logger = logging.getLogger(__name__)
MAX_PROVIDER_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class RagService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @staticmethod
    def build_context(
        chunks: list[RetrievedChunk],
    ) -> tuple[str, dict[str, RetrievedChunk]]:
        sources: dict[str, RetrievedChunk] = {}
        blocks: list[str] = []

        for index, chunk in enumerate(chunks, start=1):
            source_id = f"S{index}"
            sources[source_id] = chunk
            blocks.append(
                f"[{source_id}]\n"
                f"Document: {chunk.document_title}\n"
                f"Page: {chunk.page_number}\n"
                f"Content:\n{chunk.text}"
            )

        return "\n\n".join(blocks), sources

    @staticmethod
    def validate_citations(
        answer: str,
        sources: dict[str, RetrievedChunk],
    ) -> tuple[str, list[Citation]]:
        used_source_ids: list[str] = []

        def replace_citation(match: re.Match[str]) -> str:
            valid_source_ids: list[str] = []
            for source_id in re.findall(r"S\d+", match.group(1)):
                if source_id not in sources:
                    continue
                if source_id not in used_source_ids:
                    used_source_ids.append(source_id)
                if source_id not in valid_source_ids:
                    valid_source_ids.append(source_id)
            return " ".join(f"[{source_id}]" for source_id in valid_source_ids)

        cleaned_answer = CITATION_PATTERN.sub(replace_citation, answer)
        cleaned_answer = re.sub(r" {2,}", " ", cleaned_answer).strip()

        citations = [
            Citation(
                source_id=source_id,
                document_id=sources[source_id].document_id,
                document_title=sources[source_id].document_title,
                page_number=sources[source_id].page_number,
                chunk_id=sources[source_id].chunk_id,
                text=sources[source_id].text,
                similarity=sources[source_id].similarity,
                source_url=sources[source_id].source_url,
            )
            for source_id in used_source_ids
        ]
        return cleaned_answer, citations

    async def _generate(self, question: str, context: str) -> str:
        self.settings.require_llm()
        endpoint = f"{self.settings.llm_api_base.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.llm_model,
            "temperature": self.settings.llm_temperature,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(
                        question=question,
                        context=context,
                    ),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(MAX_PROVIDER_ATTEMPTS):
                try:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()
                    break
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    status_code = (
                        exc.response.status_code
                        if isinstance(exc, httpx.HTTPStatusError)
                        else None
                    )
                    retryable = (
                        status_code is None
                        or status_code in RETRYABLE_STATUS_CODES
                    )
                    if not retryable or attempt == MAX_PROVIDER_ATTEMPTS - 1:
                        raise
                    delay = 2**attempt
                    logger.warning(
                        "Chat-completion request failed%s; retrying in %d "
                        "second(s).",
                        f" with HTTP {status_code}" if status_code else "",
                        delay,
                    )
                    await asyncio.sleep(delay)

        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("The LLM provider returned an invalid response.") from exc

    async def answer(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> tuple[str, list[Citation], bool]:
        if not chunks:
            return INSUFFICIENT_EVIDENCE_ANSWER, [], True

        context, sources = self.build_context(chunks)
        raw_answer = await self._generate(question, context)
        answer, citations = self.validate_citations(raw_answer, sources)
        insufficient = (
            INSUFFICIENT_EVIDENCE_ANSWER.lower() in answer.lower()
            or not citations
        )
        return answer, citations, insufficient
