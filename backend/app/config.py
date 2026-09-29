from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Document Intelligence RAG Assistant"
    debug: bool = False

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "documents"

    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dimensions: int = Field(default=384, ge=1, le=4096)
    embedding_batch_size: int = Field(default=16, ge=1, le=128)

    chunk_size: int = Field(default=1000, ge=200, le=5000)
    chunk_overlap: int = Field(default=150, ge=0, le=1000)

    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.35, ge=-1.0, le=1.0)
    hybrid_search: bool = False

    llm_api_base: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)

    frontend_url: str = "http://localhost:5173"
    max_pdf_size_mb: int = Field(default=25, ge=1, le=100)

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_value(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"development", "dev"}:
                return True
        return value

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, value: int, info) -> int:
        chunk_size = info.data.get("chunk_size", 1000)
        if value >= chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return value

    @property
    def max_pdf_size_bytes(self) -> int:
        return self.max_pdf_size_mb * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.frontend_url.split(",")
            if origin.strip()
        ]

    def require_supabase(self) -> None:
        if not self.supabase_url or not self.supabase_service_role_key:
            raise RuntimeError("Supabase backend credentials are not configured.")

    def require_llm(self) -> None:
        if not self.llm_api_base or not self.llm_api_key or not self.llm_model:
            raise RuntimeError("The OpenAI-compatible LLM provider is not configured.")

    def require_embeddings(self) -> None:
        if not self.llm_api_base or not self.llm_api_key or not self.embedding_model:
            raise RuntimeError("The OpenRouter embedding provider is not configured.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
