from app.config import Settings
from app.models import ExtractedPage
from app.services.chunk_service import ChunkService


def test_chunks_never_cross_page_boundaries() -> None:
    settings = Settings(chunk_size=200, chunk_overlap=20)
    pages = [
        ExtractedPage(page_number=2, text="Alpha sentence. " * 40),
        ExtractedPage(page_number=7, text="Beta sentence. " * 40),
    ]

    chunks = ChunkService(settings).create_chunks(pages)

    assert len(chunks) > 2
    assert {chunk.page_number for chunk in chunks} == {2, 7}
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.token_count > 0 for chunk in chunks)
    assert all(not ("Alpha" in chunk.text and "Beta" in chunk.text) for chunk in chunks)
