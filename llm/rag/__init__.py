"""
RAG pipeline and PostgreSQL + pgvector knowledge base package.
"""

from rag.chunker import DocumentChunk, DocumentChunker
from rag.cleaning import clean_text
from rag.config import RAGConfig
from rag.embeddings import LocalEmbedder, get_embedder
from rag.pipeline import Citation, RAGAnswer, RAGPipeline
from rag.retriever import DocumentRetriever, RetrievedChunk
from rag.vector_store import (
    VectorStore,
    VectorStoreConnectionError,
    VectorStoreError,
    VectorStoreSchemaError,
)

__all__ = [
    "clean_text",
    "DocumentChunk",
    "DocumentChunker",
    "RAGConfig",
    "LocalEmbedder",
    "get_embedder",
    "VectorStore",
    "VectorStoreError",
    "VectorStoreConnectionError",
    "VectorStoreSchemaError",
    "DocumentRetriever",
    "RetrievedChunk",
    "Citation",
    "RAGAnswer",
    "RAGPipeline",
]

