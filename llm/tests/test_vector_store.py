"""
Unit tests for the PostgreSQL + pgvector vector store using mocked database connections.
"""

import unittest
from unittest.mock import MagicMock, patch

from rag.chunker import DocumentChunk
from rag.config import RAGConfig
from rag.vector_store import (
    VectorStore,
    VectorStoreConnectionError,
    VectorStoreError,
)


class TestVectorStore(unittest.TestCase):
    """Test suite for VectorStore using mocked psycopg2."""

    def setUp(self):
        self.config = RAGConfig(
            database_url="postgresql://test_user:secret_pwd@127.0.0.1:5432/test_db",
        )
        self.store = VectorStore(config=self.config)

    def tearDown(self):
        self.store.close()

    def test_safe_host_str_masks_credentials(self):
        """Verify that connection string logging never exposes credentials."""
        safe_str = self.store._safe_host_str()
        self.assertNotIn("secret_pwd", safe_str)
        self.assertIn("127.0.0.1:5432/test_db", safe_str)

    @patch("rag.vector_store.pool.SimpleConnectionPool")
    def test_check_health_unreachable(self, mock_pool_cls):
        """Verify check_health handles connection failure gracefully."""
        import psycopg2
        mock_pool_cls.side_effect = psycopg2.OperationalError("Connection refused")

        health = self.store.check_health()
        self.assertFalse(health["reachable"])
        self.assertIn("Connection refused", health["error"])

    @patch("rag.vector_store.register_vector")
    @patch("rag.vector_store.pool.SimpleConnectionPool")
    def test_check_health_success(self, mock_pool_cls, mock_reg_vec):
        """Verify check_health returns true when database and extension are ready."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()

        # Queries: SELECT 1; extversion; table_name in public
        mock_cur.fetchone.return_value = ["0.8.0"]  # pgvector installed
        mock_cur.fetchall.return_value = [("rag_documents",), ("rag_document_chunks",)]

        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_pool.getconn.return_value = mock_conn
        mock_pool_cls.return_value = mock_pool

        health = self.store.check_health()
        self.assertTrue(health["reachable"])
        self.assertTrue(health["pgvector_installed"])
        self.assertEqual(health["pgvector_version"], "0.8.0")
        self.assertTrue(health["tables_initialized"])

    @patch("rag.vector_store.pool.SimpleConnectionPool")
    def test_upsert_document_success(self, mock_pool_cls):
        """Verify upsert_document executes parameterized SQL."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()

        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_pool.getconn.return_value = mock_conn
        mock_pool_cls.return_value = mock_pool

        doc_meta = {
            "document_id": "doc_rm003",
            "title": "General Instructions",
            "publication_number": "1756-RM003",
            "publisher": "Rockwell Automation",
            "source_url": "http://example.com/doc.pdf",
            "file_name": "1756-RM003.pdf",
            "sha256": "abc123hash",
            "page_count": 927,
            "is_index_only": False,
        }

        success = self.store.upsert_document(doc_meta)
        self.assertTrue(success)
        mock_cur.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("rag.vector_store.register_vector")
    @patch("rag.vector_store.execute_batch")
    @patch("rag.vector_store.pool.SimpleConnectionPool")
    def test_upsert_chunks_success(self, mock_pool_cls, mock_batch, mock_reg_vec):
        """Verify upsert_chunks executes batch insert with vector embeddings."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()

        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_pool.getconn.return_value = mock_conn
        mock_pool_cls.return_value = mock_pool

        chunks = [
            DocumentChunk(
                id="c1",
                document_id="doc1",
                title="Doc 1",
                publication_number="1756-RM003",
                source_filename="doc1.pdf",
                page_number=1,
                end_page_number=1,
                chunk_index=0,
                content="Chunk 1 content",
                content_hash="hash1",
            )
        ]
        embeddings = [[0.1] * 384]

        count = self.store.upsert_chunks(chunks, embeddings)
        self.assertEqual(count, 1)
        mock_batch.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("rag.vector_store.register_vector")
    @patch("rag.vector_store.pool.SimpleConnectionPool")
    def test_similarity_search_success(self, mock_pool_cls, mock_reg_vec):
        """Verify similarity_search returns sorted matches with cosine similarity scores."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()

        # Simulated row: chunk_id, document_id, page_number, end_page_number, chunk_index,
        # content, title, publication_number, file_name, metadata, score
        mock_cur.fetchall.return_value = [
            (
                "c1",
                "doc_rm003",
                45,
                45,
                0,
                "XIC instruction examines if closed",
                "Logix 5000 General Instructions",
                "1756-RM003",
                "1756-RM003.pdf",
                '{"section": "relay"}',
                0.885,
            )
        ]

        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_pool.getconn.return_value = mock_conn
        mock_pool_cls.return_value = mock_pool

        query_vec = [0.1] * 384
        results = self.store.similarity_search(query_vec, top_k=5, threshold=0.35)

        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res["chunk_id"], "c1")
        self.assertEqual(res["document_title"], "Logix 5000 General Instructions")
        self.assertEqual(res["page_number"], 45)
        self.assertEqual(res["score"], 0.885)
        self.assertIn("XIC", res["content"])


if __name__ == "__main__":
    unittest.main()

