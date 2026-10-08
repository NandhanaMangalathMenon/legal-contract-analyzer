from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = Field(default="mock")
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.0-flash")
    embedding_model: str = Field(default="text-embedding-004")

    model_temperature: float = Field(default=0.2)
    model_frequency_penalty: float = Field(default=0.0)
    model_presence_penalty: float = Field(default=0.0)
    model_max_output_tokens: int = Field(default=4096)

    embedding_cache_dir: Path = Field(default=ROOT_DIR / "data" / ".cache" / "embeddings")
    vector_store_backend: str = Field(default="memory")
    chroma_persist_dir: Path = Field(default=ROOT_DIR / "data" / ".cache" / "chroma")
    contract_collection: str = Field(default="contract_store")
    legal_collection: str = Field(default="legal_store")

    human_review_confidence_threshold: float = Field(default=0.55)
    max_dependency_hops: int = Field(default=2)
    max_context_clauses: int = Field(default=24)
    log_level: str = Field(default="INFO")

    legal_knowledge_dir: Path = Field(default=ROOT_DIR / "data" / "legal_knowledge")
    sample_contract_dir: Path = Field(default=ROOT_DIR / "data" / "sample_contracts")
    processed_dir: Path = Field(default=ROOT_DIR / "data" / "processed")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.embedding_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.legal_knowledge_dir.mkdir(parents=True, exist_ok=True)
    return settings
