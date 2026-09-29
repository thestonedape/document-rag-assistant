from app.config import Settings
from app.services.ingestion_service import mark_ingestion_failed


class FakeQuery:
    def __init__(self, client: "FakeClient", table: str) -> None:
        self.client = client
        self.table = table
        self.action = ""
        self.payload = None
        self.filters: dict[str, str] = {}

    def delete(self) -> "FakeQuery":
        self.action = "delete"
        return self

    def update(self, payload: dict) -> "FakeQuery":
        self.action = "update"
        self.payload = payload
        return self

    def eq(self, column: str, value: str) -> "FakeQuery":
        self.filters[column] = value
        return self

    def execute(self) -> None:
        self.client.executions.append(
            (self.table, self.action, self.payload, self.filters)
        )


class FakeBucket:
    def __init__(self, client: "FakeClient") -> None:
        self.client = client

    def remove(self, paths: list[str]) -> None:
        self.client.removed_paths.extend(paths)


class FakeStorage:
    def __init__(self, client: "FakeClient") -> None:
        self.client = client

    def from_(self, bucket: str) -> FakeBucket:
        self.client.bucket = bucket
        return FakeBucket(self.client)


class FakeClient:
    def __init__(self) -> None:
        self.executions: list[tuple] = []
        self.removed_paths: list[str] = []
        self.bucket = ""
        self.storage = FakeStorage(self)

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)


def test_failed_ingestion_removes_partial_data_and_keeps_failed_record() -> None:
    client = FakeClient()
    settings = Settings(supabase_storage_bucket="documents")

    mark_ingestion_failed(
        client,
        settings,
        "document-id",
        "document-id/file.pdf",
        "Processing failed.",
    )

    assert client.executions == [
        (
            "document_chunks",
            "delete",
            None,
            {"document_id": "document-id"},
        ),
        (
            "documents",
            "update",
            {
                "status": "failed",
                "error_message": "Processing failed.",
            },
            {"id": "document-id"},
        ),
    ]
    assert client.bucket == "documents"
    assert client.removed_paths == ["document-id/file.pdf"]
