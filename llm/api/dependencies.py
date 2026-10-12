"""
FastAPI dependency injection providers for RAG and LLM components.
"""

from __future__ import annotations

from functools import lru_cache

from llm.llama_cpp_client import LlamaCppClient
from llm.model_config import ModelConfig
from rag.config import RAGConfig
from rag.embeddings import get_embedder
from rag.pipeline import RAGPipeline
from rag.retriever import DocumentRetriever
from rag.vector_store import VectorStore


@lru_cache()
def get_rag_config() -> RAGConfig:
    """Return cached RAG configuration."""
    return RAGConfig.from_env()


@lru_cache()
def get_model_config() -> ModelConfig:
    """Return cached LLM model configuration."""
    return ModelConfig.from_env()


def get_llm_client() -> LlamaCppClient:
    """Provide LlamaCppClient instance."""
    return LlamaCppClient(config=get_model_config())


def get_vector_store() -> VectorStore:
    """Provide VectorStore instance."""
    return VectorStore(config=get_rag_config())


def get_retriever() -> DocumentRetriever:
    """Provide DocumentRetriever instance."""
    config = get_rag_config()
    store = get_vector_store()
    embedder = get_embedder(model_name=config.embedding_model_name)
    return DocumentRetriever(vector_store=store, embedder=embedder, config=config)


def get_rag_pipeline() -> RAGPipeline:
    """Provide RAGPipeline instance."""
    config = get_rag_config()
    retriever = get_retriever()
    llm = get_llm_client()
    return RAGPipeline(retriever=retriever, llm_client=llm, config=config)

