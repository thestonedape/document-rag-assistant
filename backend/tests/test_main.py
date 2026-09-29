from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main as main_module


class FakeQuery:
    def select(self, _: str) -> "FakeQuery":
        return self

    def limit(self, _: int) -> "FakeQuery":
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=[])


class FakeSupabase:
    def table(self, name: str) -> FakeQuery:
        assert name == "documents"
        return FakeQuery()


def test_readiness_confirms_supabase_access(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "get_supabase", lambda: FakeSupabase())
    response = TestClient(main_module.app).get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_readiness_fails_when_supabase_is_unavailable(monkeypatch) -> None:
    def unavailable() -> None:
        raise RuntimeError("unavailable")

    monkeypatch.setattr(main_module, "get_supabase", unavailable)
    response = TestClient(main_module.app).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Supabase connection is unavailable."}
