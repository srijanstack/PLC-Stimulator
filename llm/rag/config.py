"""
Centralized configuration for the RAG pipeline, PostgreSQL + pgvector database, and API.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RAGConfig(BaseModel):
    """Configuration for RAG embedding, PostgreSQL vector storage, and API services."""

    model_config = ConfigDict(protected_namespaces=())

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@127.0.0.1:5432/plc_simulator",
        description="PostgreSQL connection string. Single DB for RAG and future simulator.",
    )

    # Embedding Model
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Local Sentence Transformers embedding model name or path.",
    )
    embedding_dimension: int = Field(
        default=384,
        gt=0,
        description="Vector embedding dimension (384 for all-MiniLM-L6-v2).",
    )

    # Retrieval
    rag_top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of relevant chunks to retrieve per query.",
    )
    rag_similarity_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold. Chunks with score below this are discarded.",
    )

    # Chunking
    chunk_size: int = Field(
        default=2400,
        gt=100,
        description="Target maximum characters per chunk.",
    )
    chunk_overlap: int = Field(
        default=400,
        ge=0,
        description="Overlap characters between adjacent chunks.",
    )

    # API Server
    api_host: str = Field(
        default="127.0.0.1",
        description="FastAPI host interface (127.0.0.1 for local privacy).",
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="FastAPI port.",
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
        description="Allowed CORS origins for the future PLC simulator frontend.",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL scheme."""
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("database_url must begin with postgresql:// or postgres://")
        return v

    @classmethod
    def from_env(cls, env_file: Optional[Path | str] = None) -> RAGConfig:
        """Load configuration from environment and optional .env file."""
        if env_file:
            env_path = Path(env_file)
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
        else:
            default_env = Path(".env")
            if default_env.exists():
                load_dotenv(dotenv_path=default_env)

        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/plc_simulator")
        emb_model = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
        emb_dim = int(os.getenv("EMBEDDING_DIMENSION", "384"))
        top_k = int(os.getenv("RAG_TOP_K", "5"))
        sim_threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.35"))
        c_size = int(os.getenv("RAG_CHUNK_SIZE", "2400"))
        c_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "400"))
        api_h = os.getenv("API_HOST", "127.0.0.1")
        api_p = int(os.getenv("API_PORT", "8000"))

        cors_raw = os.getenv("CORS_ORIGINS")
        if cors_raw:
            cors_list = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]
        else:
            cors_list = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
            ]

        return cls(
            database_url=db_url,
            embedding_model_name=emb_model,
            embedding_dimension=emb_dim,
            rag_top_k=top_k,
            rag_similarity_threshold=sim_threshold,
            chunk_size=c_size,
            chunk_overlap=c_overlap,
            api_host=api_h,
            api_port=api_p,
            cors_origins=cors_list,
        )

    def to_safe_dict(self) -> Dict[str, Any]:
        """Return configuration dictionary with password in database_url masked."""
        data = self.model_dump()
        try:
            parsed = urlparse(self.database_url)
            if parsed.password:
                safe_netloc = f"{parsed.username}:********@{parsed.hostname}"
                if parsed.port:
                    safe_netloc += f":{parsed.port}"
                data["database_url"] = self.database_url.replace(parsed.netloc, safe_netloc)
        except Exception:
            data["database_url"] = "postgresql://********"
        return data

    def __repr__(self) -> str:
        return f"RAGConfig({self.to_safe_dict()})"

