"""
Pydantic schemas for the PLC Simulator AI Assistant API.

Defines the contract between the standalone assistant backend and any future
simulator frontend or external client.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthResponse(BaseModel):
    """System health check response schema."""
    model_config = ConfigDict(protected_namespaces=())

    status: str = Field(description="'ok' if services are reachable, 'degraded' otherwise.")
    database: Dict[str, Any] = Field(description="PostgreSQL and pgvector connectivity and schema status.")
    llm: Dict[str, Any] = Field(description="Local llama.cpp inference server status.")
    version: str = Field(default="0.1.0", description="API version.")


class KnowledgeBaseStatusResponse(BaseModel):
    """Knowledge base indexing status schema."""
    model_config = ConfigDict(protected_namespaces=())

    documents_count: int = Field(description="Number of ingested parent documents.")
    chunks_count: int = Field(description="Total number of indexed semantic chunks.")
    database_target: str = Field(description="PostgreSQL host/database identifier (no secrets).")
    pgvector_ready: bool = Field(description="True if pgvector extension and tables are initialized.")


class RetrieveRequest(BaseModel):
    """Request payload for semantic document search."""
    model_config = ConfigDict(protected_namespaces=())

    query: str = Field(
        min_length=1,
        max_length=2000,
        description="Search query or technical question.",
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Optional limit on number of passages to return.",
    )
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional minimum cosine similarity threshold.",
    )


class RetrievedChunkSchema(BaseModel):
    """Schema for an individual retrieved documentation chunk."""
    model_config = ConfigDict(protected_namespaces=())

    chunk_id: str
    document_title: str
    publication_number: str
    page_number: int
    end_page_number: int
    content: str
    score: float
    citation: str


class RetrieveResponse(BaseModel):
    """Response payload containing retrieved passages."""
    model_config = ConfigDict(protected_namespaces=())

    query: str
    count: int
    results: List[RetrievedChunkSchema]


class SimulatorContext(BaseModel):
    """Optional context payload provided by a future PLC simulator frontend."""
    model_config = ConfigDict(protected_namespaces=())

    active_tags: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Tags defined in the active simulator project.",
    )
    supported_instructions: Optional[List[str]] = Field(
        default=None,
        description="List of instruction mnemonics supported by the simulator.",
    )
    controller_model: Optional[str] = Field(
        default=None,
        description="Simulated controller type (e.g. 1756-L85E, 5069-L330ER).",
    )
    routine_name: Optional[str] = Field(
        default=None,
        description="Active routine or program context.",
    )
    extra_context: Optional[Union[Dict[str, Any], str]] = Field(
        default=None,
        description="Any additional simulator telemetry or environment data.",
    )

    @field_validator("extra_context", mode="before")
    @classmethod
    def parse_extra_context(cls, v: Any) -> Any:
        """Coerce JSON string into a dictionary if needed."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return v


class ChatRequest(BaseModel):
    """Request payload for RAG chat generation."""
    model_config = ConfigDict(protected_namespaces=())

    question: str = Field(
        min_length=1,
        max_length=2000,
        description="Technical question about PLC programming, instructions, or ladder logic.",
    )
    simulator_context: Optional[SimulatorContext] = Field(
        default=None,
        description="Optional runtime state from the simulator.",
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Override for max retrieved passages.",
    )
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override for minimum similarity threshold.",
    )


class CitationSchema(BaseModel):
    """Schema for a verified document citation."""
    model_config = ConfigDict(protected_namespaces=())

    document_title: str
    publication_number: str
    page_number: int
    end_page_number: int
    citation_str: str


class ChatResponse(BaseModel):
    """Response payload for RAG chat generation."""
    model_config = ConfigDict(protected_namespaces=())

    question: str
    answer: str
    citations: List[CitationSchema]
    retrieved_chunks: List[RetrievedChunkSchema]
    latency_seconds: float
    tokens_per_second: Optional[float] = None
    metrics_source: str = "unavailable"

