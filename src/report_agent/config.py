"""Environment-backed application settings."""

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_environment(path: str | Path = ".env") -> bool:
    """Load local secrets without overriding deployment environment variables."""

    return load_dotenv(dotenv_path=path, override=False)


load_environment()


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REPORT_AGENT_",
        extra="ignore",
    )

    model: str = "openai/gpt-4.1-mini"
    evaluator_model: str = "openai/gpt-4.1-mini"
    max_agent_iterations: int = Field(default=8, ge=1, le=30)
    max_evaluation_retries: int = Field(default=2, ge=0, le=5)
    max_parallel_searches: int = Field(default=4, ge=1, le=20)
    max_queries_per_section: int = Field(default=3, ge=1, le=8)
    max_sources_per_section: int = Field(default=8, ge=1, le=20)
    minimum_source_score: float = Field(default=0.45, ge=0, le=1)
    request_timeout_seconds: float = Field(default=30, gt=0, le=120)
    max_api_retries: int = Field(default=3, ge=1, le=8)
    retry_base_delay_seconds: float = Field(default=1.0, ge=0.1, le=10)
    max_fetch_bytes: int = Field(default=1_000_000, ge=10_000, le=5_000_000)
    max_fetch_redirects: int = Field(default=3, ge=0, le=10)
    workspace: Path = Path("workspace")

    # Optional Neo4j GraphRAG. Existing web-only installations keep this disabled.
    rag_enabled: bool = False
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    rag_embedding_model: str = "openai/text-embedding-3-small"
    rag_vector_index: str = "report_chunk_embeddings"
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_chunk_size: int = Field(default=1200, ge=200, le=8000)
    rag_chunk_overlap: int = Field(default=200, ge=0, le=2000)
    rag_retrieval_mode: Literal["vector", "hybrid"] = "hybrid"

    @property
    def rag_configured(self) -> bool:
        """Return whether GraphRAG is enabled and has usable connection settings."""

        return bool(
            self.rag_enabled
            and self.neo4j_uri.strip()
            and self.neo4j_username.strip()
            and self.neo4j_password
        )
