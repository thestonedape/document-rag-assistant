from ..config import Settings, get_settings
from ..models import ExtractedPage, TextChunk


class ChunkService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _split_text(self, text: str) -> list[str]:
        chunks: list[str] = []
        start = 0
        text_length = len(text)

        while start < text_length:
            maximum_end = min(start + self.settings.chunk_size, text_length)
            end = maximum_end

            if maximum_end < text_length:
                minimum_end = start + max(self.settings.chunk_size // 2, 1)
                candidates = [
                    text.rfind(separator, minimum_end, maximum_end)
                    for separator in ("\n\n", "\n", ". ", " ")
                ]
                boundary = max(candidates)
                if boundary >= minimum_end:
                    end = boundary + (2 if text[boundary : boundary + 2] == ". " else 1)

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= text_length:
                break

            next_start = max(end - self.settings.chunk_overlap, start + 1)
            start = next_start

        return chunks

    def create_chunks(self, pages: list[ExtractedPage]) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        chunk_index = 0

        for page in pages:
            for text in self._split_text(page.text):
                cleaned = text.strip()
                if not cleaned:
                    continue
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        page_number=page.page_number,
                        text=cleaned,
                        token_count=len(cleaned.split()),
                    )
                )
                chunk_index += 1

        if not chunks:
            raise ValueError("No text chunks could be created from the PDF.")
        return chunks
