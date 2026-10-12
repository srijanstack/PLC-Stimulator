"""
Semantic retriever connecting local embeddings with PostgreSQL + pgvector search.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rag.config import RAGConfig
from rag.embeddings import LocalEmbedder, get_embedder
from rag.vector_store import VectorStore

logger = logging.getLogger("rag.retriever")


@dataclass
class RetrievedChunk:
    """Represents a passage retrieved from the knowledge base with similarity scoring."""

    chunk_id: str
    document_id: str
    document_title: str
    publication_number: str
    page_number: int
    end_page_number: int
    content: str
    score: float
    metadata: Dict[str, Any]

    @property
    def citation(self) -> str:
        """Formatted human-readable citation string."""
        page_str = (
            f"p. {self.page_number}"
            if self.page_number == self.end_page_number or not self.end_page_number
            else f"pp. {self.page_number}-{self.end_page_number}"
        )
        if self.publication_number:
            return f"{self.document_title} ({self.publication_number}), {page_str}"
        return f"{self.document_title}, {page_str}"


class DocumentRetriever:
    """Coordinates embedding generation and vector database similarity search."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[LocalEmbedder] = None,
        config: Optional[RAGConfig] = None,
    ) -> None:
        """Initialize retriever."""
        self.config = config or RAGConfig.from_env()
        self.vector_store = vector_store or VectorStore(config=self.config)
        self.embedder = embedder or get_embedder(model_name=self.config.embedding_model_name)

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        document_filter: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """Retrieve the most relevant documentation passages for a query.

        Args:
            query: User's technical question.
            top_k: Optional override for max chunks to return.
            threshold: Optional override for minimum cosine similarity score.
            document_filter: Optional substring filter on document title, ID, or publisher.

        Returns:
            List of RetrievedChunk instances sorted descending by similarity score.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        k = top_k if top_k is not None else self.config.rag_top_k
        thresh = threshold if threshold is not None else self.config.rag_similarity_threshold

        # 1. Generate query embedding vector
        query_vector = self.embedder.embed_query(clean_query)

        # 2. Query PostgreSQL + pgvector
        raw_matches = self.vector_store.similarity_search(
            query_embedding=query_vector,
            top_k=k,
            threshold=thresh,
            document_filter=document_filter,
        )

        # 3. Format as RetrievedChunk objects
        chunks: List[RetrievedChunk] = []
        for match in raw_matches:
            chunks.append(
                RetrievedChunk(
                    chunk_id=match["chunk_id"],
                    document_id=match["document_id"],
                    document_title=match["document_title"],
                    publication_number=match["publication_number"],
                    page_number=match["page_number"],
                    end_page_number=match["end_page_number"],
                    content=match["content"],
                    score=match["score"],
                    metadata=match.get("metadata", {}),
                )
            )

        return chunks

