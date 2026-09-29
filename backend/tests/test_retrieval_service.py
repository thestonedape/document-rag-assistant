from app.config import Settings
from app.services.retrieval_service import RetrievalService


def _service(min_similarity: float = 0.35) -> RetrievalService:
    service = object.__new__(RetrievalService)
    service.settings = Settings(min_similarity=min_similarity)
    return service


def test_specific_question_still_requires_similarity_threshold() -> None:
    service = _service()
    rows = [{"id": "low", "similarity": 0.21}]

    assert service._filter_matches("What is the stated accuracy?", rows) == []


def test_summary_question_uses_nearest_chunks_below_threshold() -> None:
    service = _service()
    rows = [
        {"id": "best", "similarity": 0.28},
        {"id": "next", "similarity": 0.22},
    ]

    assert service._filter_matches(
        "Summarize the key ideas in these documents.",
        rows,
    ) == rows


def test_pdf_topic_question_uses_nearest_chunks_below_threshold() -> None:
    service = _service()
    rows = [{"id": "best", "similarity": 0.19}]

    assert service._filter_matches("What's the topic this PDF covers?", rows) == rows


def test_overview_question_prefers_only_threshold_matches_when_available() -> None:
    service = _service()
    rows = [
        {"id": "strong", "similarity": 0.51},
        {"id": "weak", "similarity": 0.20},
    ]

    assert service._filter_matches("Give an overview of the document.", rows) == [
        rows[0]
    ]
