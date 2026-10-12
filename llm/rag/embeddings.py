"""
Local sentence-transformers embedding generation for the PLC Chatbot RAG pipeline.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger("rag.embeddings")

_EMBEDDER_INSTANCE: Optional[LocalEmbedder] = None


class LocalEmbedder:
    """Wrapper around SentenceTransformer for generating normalized embeddings."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        """Initialize the local embedding model."""
        self.model_name = model_name
        self._model = None
        self._dimension: Optional[int] = None

    def _load_model(self):
        """Lazy load the sentence-transformers model."""
        if self._model is None:
            logger.info(f"Loading local embedding model: {self.model_name}...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Dimension: {self._dimension}")
        return self._model

    @property
    def dimension(self) -> int:
        """Return embedding vector dimension."""
        if self._dimension is None:
            self._load_model()
        return self._dimension or 384

    def embed_query(self, text: str) -> List[float]:
        """Generate a normalized embedding for a single query string."""
        model = self._load_model()
        embedding = model.encode(text, normalize_embeddings=True)
        if isinstance(embedding, np.ndarray):
            return embedding.tolist()
        return list(embedding)

    def embed_documents(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress_bar: bool = False,
    ) -> List[List[float]]:
        """Generate normalized embeddings for a list of document strings."""
        if not texts:
            return []

        model = self._load_model()
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=show_progress_bar,
        )
        if isinstance(embeddings, np.ndarray):
            return embeddings.tolist()
        return [list(vec) for vec in embeddings]


def get_embedder(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> LocalEmbedder:
    """Return a shared singleton instance of LocalEmbedder."""
    global _EMBEDDER_INSTANCE
    if _EMBEDDER_INSTANCE is None or _EMBEDDER_INSTANCE.model_name != model_name:
        _EMBEDDER_INSTANCE = LocalEmbedder(model_name=model_name)
    return _EMBEDDER_INSTANCE

