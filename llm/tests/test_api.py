"""
Unit tests for FastAPI endpoints (/health, /knowledge-base/status, /retrieve, /chat).
"""

import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.dependencies import (
    get_llm_client,
    get_rag_pipeline,
    get_retriever,
    get_vector_store,
)
from api.main import app
from llm.llama_cpp_client import GenerationResult, LlamaCppClient, LlamaCppConnectionError
from rag.pipeline import Citation, RAGAnswer, RAGPipeline
from rag.retriever import DocumentRetriever, RetrievedChunk
from rag.vector_store import VectorStore, VectorStoreError


class TestAPIEndpoints(unittest.TestCase):
    """Test suite for FastAPI endpoints."""

    def setUp(self):
        self.mock_store = MagicMock(spec=VectorStore)
        self.mock_llm = MagicMock(spec=LlamaCppClient)
        self.mock_retriever = MagicMock(spec=DocumentRetriever)
        self.mock_pipeline = MagicMock(spec=RAGPipeline)

        app.dependency_overrides[get_vector_store] = lambda: self.mock_store
        app.dependency_overrides[get_llm_client] = lambda: self.mock_llm
        app.dependency_overrides[get_retriever] = lambda: self.mock_retriever
        app.dependency_overrides[get_rag_pipeline] = lambda: self.mock_pipeline

        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_health_endpoint_healthy(self):
        """Test GET /health when database and LLM are reachable."""
        self.mock_store.check_health.return_value = {
            "reachable": True,
            "pgvector_installed": True,
            "tables_initialized": True,
            "target": "127.0.0.1:5432/plc_simulator",
        }
        self.mock_llm.check_health.return_value = {"status_code": 200}

        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["database"]["reachable"])
        self.assertTrue(data["llm"]["reachable"])

    def test_health_endpoint_degraded(self):
        """Test GET /health when LLM is unreachable."""
        self.mock_store.check_health.return_value = {
            "reachable": True,
            "pgvector_installed": True,
            "tables_initialized": True,
        }
        self.mock_llm.check_health.side_effect = LlamaCppConnectionError("Server offline")

        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "degraded")
        self.assertFalse(data["llm"]["reachable"])

    def test_kb_status_endpoint(self):
        """Test GET /knowledge-base/status returns document counts."""
        self.mock_store.get_status.return_value = {
            "health": {"reachable": True, "target": "127.0.0.1:5432/plc_simulator", "tables_initialized": True},
            "documents": 3,
            "chunks": 450,
        }

        resp = self.client.get("/knowledge-base/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["documents_count"], 3)
        self.assertEqual(data["chunks_count"], 450)
        self.assertTrue(data["pgvector_ready"])

    def test_retrieve_endpoint_success(self):
        """Test POST /retrieve returns retrieved passages."""
        mock_chunk = RetrievedChunk(
            chunk_id="c1",
            document_id="doc1",
            document_title="Logix 5000 General Instructions",
            publication_number="1756-RM003",
            page_number=12,
            end_page_number=12,
            content="TON timer description.",
            score=0.91,
            metadata={},
        )
        self.mock_retriever.retrieve.return_value = [mock_chunk]

        payload = {"query": "How does a TON timer work?", "top_k": 3}
        resp = self.client.post("/retrieve", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["chunk_id"], "c1")
        self.assertEqual(data["results"][0]["publication_number"], "1756-RM003")
        self.assertEqual(data["results"][0]["score"], 0.91)

    def test_retrieve_endpoint_validation_error(self):
        """Test POST /retrieve rejects empty query with HTTP 422."""
        resp = self.client.post("/retrieve", json={"query": ""})
        self.assertEqual(resp.status_code, 422)

    def test_chat_endpoint_success(self):
        """Test POST /chat returns grounded answer and citations."""
        citation = Citation(
            document_title="Logix 5000 General Instructions",
            publication_number="1756-RM003",
            page_number=45,
            end_page_number=45,
        )
        chunk = RetrievedChunk(
            chunk_id="c1",
            document_id="doc1",
            document_title="Logix 5000 General Instructions",
            publication_number="1756-RM003",
            page_number=45,
            end_page_number=45,
            content="XIC examines bit for on condition.",
            score=0.89,
            metadata={},
        )
        self.mock_pipeline.answer_question.return_value = RAGAnswer(
            answer="The XIC instruction examines if a bit is closed (1).",
            citations=[citation],
            retrieved_chunks=[chunk],
            latency_seconds=0.32,
            tokens_per_second=55.0,
            metrics_source="runtime",
        )

        payload = {
            "question": "What does XIC do?",
            "simulator_context": {
                "supported_instructions": ["XIC", "OTE"],
                "routine_name": "MainRoutine",
            },
        }

        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("XIC", data["answer"])
        self.assertEqual(len(data["citations"]), 1)
        self.assertEqual(data["citations"][0]["publication_number"], "1756-RM003")
        self.assertEqual(data["citations"][0]["page_number"], 45)
        self.assertEqual(data["latency_seconds"], 0.32)

    def test_chat_endpoint_database_error_503(self):
        """Test POST /chat returns 503 when vector search raises VectorStoreError."""
        self.mock_pipeline.answer_question.side_effect = VectorStoreError("DB unavailable")
        resp = self.client.post("/chat", json={"question": "What is XIC?"})
        self.assertEqual(resp.status_code, 503)

    def test_chat_endpoint_llm_error_502(self):
        """Test POST /chat returns 502 when LLM call fails."""
        self.mock_pipeline.answer_question.side_effect = LlamaCppConnectionError("LLM refused connection")
        resp = self.client.post("/chat", json={"question": "What is XIC?"})
        self.assertEqual(resp.status_code, 502)


if __name__ == "__main__":
    unittest.main()

