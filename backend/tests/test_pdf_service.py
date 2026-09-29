import fitz
import pytest

from app.services.pdf_service import clean_page_text, extract_pages


def _sample_pdf() -> bytes:
    document = fitz.open()
    first = document.new_page()
    first.insert_text((72, 72), "Attendance is at least 75 percent.")
    document.new_page()
    payload = document.tobytes()
    document.close()
    return payload


def test_clean_page_text_preserves_paragraphs_and_repairs_hyphenation() -> None:
    raw = "A require-\nment   applies.\n\nSecond paragraph."
    assert clean_page_text(raw) == "A requirement applies.\n\nSecond paragraph."


def test_extract_pages_keeps_real_page_number_and_skips_empty_page() -> None:
    pages, page_count = extract_pages(_sample_pdf())
    assert page_count == 2
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "Attendance" in pages[0].text


def test_extract_pages_rejects_invalid_pdf() -> None:
    with pytest.raises(ValueError, match="Unable to open"):
        extract_pages(b"not a pdf")
