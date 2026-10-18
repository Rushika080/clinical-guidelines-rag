from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Google Gemini (free)
    google_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Local embedding model (HuggingFace, no API key)
    embedding_model: str = "all-MiniLM-L6-v2"

    # Local reranking model (cross-encoder, no API key)
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ChromaDB (local)
    chroma_persist_dir: str = str(
        Path(__file__).resolve().parents[2] / "data" / "chroma_db"
)

    # LangSmith (optional)
    langchain_tracing_v2: str = "false"
    langchain_api_key: str = ""
    langchain_project: str = "clinical-guidelines-rag"

    # Retrieval
    vector_top_k: int = 15
    rerank_top_n: int = 5
    parent_chunk_size: int = 2000
    child_chunk_size: int = 400
    parent_chunk_overlap: int = 200
    child_chunk_overlap: int = 50

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()