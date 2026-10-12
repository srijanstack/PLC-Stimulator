"""
PostgreSQL + pgvector persistent vector store for the PLC Simulator RAG Assistant.

Manages documents, chunks, embeddings, and semantic similarity search using
the PostgreSQL vector extension.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_batch

from pgvector.psycopg2 import register_vector

from rag.chunker import DocumentChunk
from rag.config import RAGConfig

logger = logging.getLogger("rag.vector_store")


def _to_vector_literal(embedding: List[float]) -> str:
    """Convert an embedding to pgvector's text format, e.g. '[0.1,0.2,0.3]'."""
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


class VectorStoreError(Exception):
    """Base exception for vector store operations."""


class VectorStoreConnectionError(VectorStoreError):
    """Raised when connecting to PostgreSQL fails."""


class VectorStoreSchemaError(VectorStoreError):
    """Raised when required tables or pgvector are missing."""


class VectorStore:
    """PostgreSQL vector store using pgvector and cosine similarity search."""

    def __init__(self, config: Optional[RAGConfig] = None) -> None:
        self.config = config or RAGConfig.from_env()
        self._database_url = self.config.database_url
        self._pool: Optional[pool.SimpleConnectionPool] = None

    def _get_pool(self) -> pool.SimpleConnectionPool:
        """Lazily initialize the PostgreSQL connection pool."""
        if self._pool is None:
            try:
                self._pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=self._database_url,
                )
            except psycopg2.OperationalError as err:
                raise VectorStoreConnectionError(
                    f"Could not connect to PostgreSQL at "
                    f"{self._safe_host_str()}: {err}"
                ) from err
        return self._pool

    def _safe_host_str(self) -> str:
        """Return database host information without credentials."""
        try:
            parsed = urlparse(self._database_url)
            return (
                f"{parsed.hostname}:{parsed.port or 5432}/"
                f"{parsed.path.lstrip('/')}"
            )
        except Exception:
            return "PostgreSQL"

    @staticmethod
    def _register_vector(conn: psycopg2.extensions.connection) -> None:
        """Register pgvector adapters for this database connection."""
        register_vector(conn)

    def close(self) -> None:
        """Close all pooled connections."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None

    def check_health(self) -> Dict[str, Any]:
        """Check database connectivity, pgvector, and required tables."""
        try:
            conn_pool = self._get_pool()
            conn = conn_pool.getconn()
            try:
                self._register_vector(conn)

                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.execute(
                        "SELECT extversion FROM pg_extension "
                        "WHERE extname = 'vector';"
                    )
                    ext_row = cur.fetchone()

                    cur.execute(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name IN (
                              'rag_documents',
                              'rag_document_chunks'
                          );
                        """
                    )
                    tables = [row[0] for row in cur.fetchall()]

                return {
                    "reachable": True,
                    "pgvector_installed": ext_row is not None,
                    "pgvector_version": ext_row[0] if ext_row else None,
                    "tables_initialized": len(tables) == 2,
                    "target": self._safe_host_str(),
                }
            finally:
                conn_pool.putconn(conn)
        except Exception as err:
            logger.exception("Vector store health check failed")
            return {
                "reachable": False,
                "error": str(err),
                "target": self._safe_host_str(),
            }

    def is_healthy(self) -> bool:
        """Return whether the database and required tables are available."""
        health = self.check_health()
        return (
            health.get("reachable", False)
            and health.get("pgvector_installed", False)
            and health.get("tables_initialized", False)
        )

    def get_status(self) -> Dict[str, Any]:
        """Return health information and indexed document/chunk counts."""
        health = self.check_health()
        if not health.get("reachable") or not health.get("tables_initialized"):
            return {"health": health, "documents": 0, "chunks": 0}

        conn_pool = self._get_pool()
        conn = conn_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM rag_documents;")
                doc_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM rag_document_chunks;")
                chunk_count = cur.fetchone()[0]

            return {
                "health": health,
                "documents": doc_count,
                "chunks": chunk_count,
            }
        finally:
            conn_pool.putconn(conn)

    def upsert_document(self, metadata: Dict[str, Any]) -> bool:
        """Insert or update document metadata."""
        doc_id = metadata["document_id"]

        query = """
            INSERT INTO rag_documents (
                id, title, publication_number, publisher, source_url,
                file_name, sha256, page_count, is_index_only, updated_at
            ) VALUES (
                %(id)s, %(title)s, %(pub_num)s, %(publisher)s, %(source_url)s,
                %(file_name)s, %(sha256)s, %(page_count)s, %(is_index)s,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                publication_number = EXCLUDED.publication_number,
                publisher = EXCLUDED.publisher,
                source_url = EXCLUDED.source_url,
                sha256 = EXCLUDED.sha256,
                page_count = EXCLUDED.page_count,
                is_index_only = EXCLUDED.is_index_only,
                updated_at = CURRENT_TIMESTAMP;
        """

        params = {
            "id": doc_id,
            "title": metadata.get("title", ""),
            "pub_num": metadata.get("publication_number", ""),
            "publisher": metadata.get("publisher", "Rockwell Automation"),
            "source_url": metadata.get("source_url", ""),
            "file_name": metadata.get("file_name", ""),
            "sha256": metadata.get("sha256", ""),
            "page_count": metadata.get("page_count", 0),
            "is_index": metadata.get("is_index_only", False),
        }

        conn_pool = self._get_pool()
        conn = conn_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
            conn.commit()
            return True
        except Exception as err:
            conn.rollback()
            raise VectorStoreError(
                f"Error upserting document '{doc_id}': {err}"
            ) from err
        finally:
            conn_pool.putconn(conn)

    def upsert_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> int:
        """Insert or update chunks and their embeddings."""
        if not chunks:
            return 0
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks and {len(embeddings)} embeddings"
            )

        query = """
            INSERT INTO rag_document_chunks (
                id, document_id, page_number, end_page_number, chunk_index,
                content, content_hash, embedding, metadata
            ) VALUES (
                %(id)s, %(doc_id)s, %(page_num)s, %(end_page_num)s,
                %(chunk_idx)s, %(content)s, %(hash)s, %(embedding)s::vector,
                %(metadata)s
            )
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                content_hash = EXCLUDED.content_hash,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata;
        """

        data = []
        for chunk, embedding in zip(chunks, embeddings):
            data.append(
                {
                    "id": chunk.id,
                    "doc_id": chunk.document_id,
                    "page_num": chunk.page_number,
                    "end_page_num": chunk.end_page_number,
                    "chunk_idx": chunk.chunk_index,
                    "content": chunk.content,
                    "hash": chunk.content_hash,
                    "embedding": _to_vector_literal(embedding),
                    "metadata": json.dumps(chunk.metadata),
                }
            )

        conn_pool = self._get_pool()
        conn = conn_pool.getconn()
        try:
            with conn.cursor() as cur:
                execute_batch(cur, query, data, page_size=100)
            conn.commit()
            return len(chunks)
        except Exception as err:
            conn.rollback()
            raise VectorStoreError(
                f"Error batch upserting chunks: {err}"
            ) from err
        finally:
            conn_pool.putconn(conn)

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.35,
        document_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search chunks by cosine similarity with optional document/platform filter."""
        base_query = """
            SELECT
                c.id,
                c.document_id,
                c.page_number,
                c.end_page_number,
                c.chunk_index,
                c.content,
                d.title,
                d.publication_number,
                d.file_name,
                c.metadata,
                (1 - (c.embedding <=> %(query_vector)s::vector)) AS score
            FROM rag_document_chunks c
            JOIN rag_documents d ON c.document_id = d.id
            WHERE (1 - (c.embedding <=> %(query_vector)s::vector)) >= %(threshold)s
        """

        conn_pool = self._get_pool()
        conn = conn_pool.getconn()
        try:
            params: Dict[str, Any] = {
                "query_vector": _to_vector_literal(query_embedding),
                "threshold": threshold,
                "top_k": top_k,
            }

            rows = []
            if document_filter:
                filter_query = (
                    base_query
                    + " AND (d.id ILIKE %(doc_filter)s OR d.publisher ILIKE %(doc_filter)s OR d.title ILIKE %(doc_filter)s)"
                    + " ORDER BY c.embedding <=> %(query_vector)s::vector LIMIT %(top_k)s;"
                )
                params["doc_filter"] = f"%{document_filter}%"
                with conn.cursor() as cur:
                    cur.execute(filter_query, params)
                    rows = cur.fetchall()

            # If no document filter was passed, or filtered search found nothing, run standard query
            if not rows and not document_filter:
                unfiltered_query = (
                    base_query
                    + " ORDER BY c.embedding <=> %(query_vector)s::vector LIMIT %(top_k)s;"
                )
                with conn.cursor() as cur:
                    cur.execute(unfiltered_query, params)
                    rows = cur.fetchall()

            results = []
            for row in rows:
                metadata = row[9]
                if isinstance(metadata, str):
                    metadata = json.loads(metadata or "{}")
                elif metadata is None:
                    metadata = {}

                results.append(
                    {
                        "chunk_id": row[0],
                        "document_id": row[1],
                        "page_number": row[2],
                        "end_page_number": row[3],
                        "chunk_index": row[4],
                        "content": row[5],
                        "document_title": row[6],
                        "publication_number": row[7],
                        "source_filename": row[8],
                        "metadata": metadata,
                        "score": round(float(row[10]), 4),
                    }
                )
            return results
        except Exception as err:
            conn.rollback()
            logger.exception("Vector similarity search failed")
            raise VectorStoreError(
                f"Error during similarity search: {err}"
            ) from err
        finally:
            conn_pool.putconn(conn)

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        conn_pool = self._get_pool()
        conn = conn_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id, title, publication_number, publisher, source_url,
                        file_name, sha256, page_count, is_index_only,
                        created_at, updated_at
                    FROM rag_documents
                    WHERE id = %s;
                    """,
                    (doc_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None

                return {
                    "id": row[0],
                    "title": row[1],
                    "publication_number": row[2],
                    "publisher": row[3],
                    "source_url": row[4],
                    "file_name": row[5],
                    "sha256": row[6],
                    "page_count": row[7],
                    "is_index_only": row[8],
                    "created_at": str(row[9]),
                    "updated_at": str(row[10]),
                }
        finally:
            conn_pool.putconn(conn)