import logging
import re

import fitz

from ..models import ExtractedPage

logger = logging.getLogger(__name__)


def clean_page_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    paragraphs = re.split(r"\n\s*\n", text)
    cleaned_paragraphs: list[str] = []

    for paragraph in paragraphs:
        cleaned = re.sub(r"\s+", " ", paragraph).strip()
        if cleaned:
            cleaned_paragraphs.append(cleaned)

    return "\n\n".join(cleaned_paragraphs)


def extract_pages(pdf_bytes: bytes) -> tuple[list[ExtractedPage], int]:
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError("Unable to open the uploaded PDF.") from exc

    pages: list[ExtractedPage] = []
    try:
        page_count = document.page_count
        for page_index in range(page_count):
            page = document.load_page(page_index)
            text = clean_page_text(page.get_text("text"))
            if not text:
                logger.info("Skipping PDF page %s because it contains no text.", page_index + 1)
                continue
            pages.append(ExtractedPage(page_number=page_index + 1, text=text))
    finally:
        document.close()

    if not pages:
        raise ValueError(
            "The PDF contains no extractable text. Scanned PDFs require OCR, "
            "which is not enabled in this version."
        )

    return pages, page_count

