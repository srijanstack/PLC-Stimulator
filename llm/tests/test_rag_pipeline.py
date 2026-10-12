"""
Unit tests for the RAG pipeline with mocked LLM client and retriever.
"""

import unittest
from unittest.mock import MagicMock

from llm.llama_cpp_client import GenerationResult, LlamaCppClient
from rag.pipeline import Citation, RAGPipeline
from rag.retriever import DocumentRetriever, RetrievedChunk


class TestRAGPipeline(unittest.TestCase):
    """Test suite for RAGPipeline."""

    def setUp(self):
        self.mock_retriever = MagicMock(spec=DocumentRetriever)
        self.mock_llm = MagicMock(spec=LlamaCppClient)
        self.pipeline = RAGPipeline(
            retriever=self.mock_retriever,
            llm_client=self.mock_llm,
        )

    def test_citation_string_representation(self):
        """Test citation formatting for single-page and multi-page spans."""
        c1 = Citation("General Instructions", "1756-RM003", 45, 45)
        self.assertEqual(str(c1), "General Instructions (1756-RM003), p. 45")

        c2 = Citation("Ladder Diagram", "1756-PM008", 12, 14)
        self.assertEqual(str(c2), "Ladder Diagram (1756-PM008), pp. 12-14")

    def test_answer_question_with_retrieved_evidence(self):
        """Test complete answer generation when relevant passages are found."""
        mock_chunk = RetrievedChunk(
            chunk_id="chunk_1",
            document_id="doc_rm003",
            document_title="Logix 5000 General Instructions",
            publication_number="1756-RM003",
            page_number=45,
            end_page_number=45,
            content="The XIC instruction examines if the bit is closed (1).",
            score=0.88,
            metadata={},
        )
        self.mock_retriever.retrieve.return_value = [mock_chunk]

        self.mock_llm.generate.return_value = GenerationResult(
            content="An XIC instruction checks if a bit is 1. (1756-RM003, p. 45)",
            elapsed_seconds=0.45,
            tokens_per_second=42.0,
            metrics_source="runtime",
        )

        result = self.pipeline.answer_question("What does an XIC instruction do?")

        self.assertIn("XIC", result.answer)
        self.assertEqual(len(result.citations), 1)
        self.assertEqual(result.citations[0].publication_number, "1756-RM003")
        self.assertEqual(result.citations[0].page_number, 45)
        self.assertEqual(len(result.retrieved_chunks), 1)
        self.assertEqual(result.latency_seconds, 0.45)
        self.mock_llm.generate.assert_called_once()

    def test_answer_question_no_evidence_found(self):
        """Verify that when no chunks match, pipeline returns refusal without calling LLM."""
        self.mock_retriever.retrieve.return_value = []

        result = self.pipeline.answer_question("How do I configure quantum teleportation in Studio 5000?")

        self.assertIn("do not contain sufficient evidence", result.answer)
        self.assertEqual(len(result.citations), 0)
        self.assertEqual(len(result.retrieved_chunks), 0)
        # Crucial requirement: LLM must NOT be called to invent unsupported answers
        self.mock_llm.generate.assert_not_called()

    def test_answer_question_with_simulator_context(self):
        """Verify simulator context is appended to the prompt."""
        mock_chunk = RetrievedChunk(
            chunk_id="c1",
            document_id="doc1",
            document_title="Ladder Diagram",
            publication_number="1756-PM008",
            page_number=10,
            end_page_number=10,
            content="Rung execution order.",
            score=0.82,
            metadata={},
        )
        self.mock_retriever.retrieve.return_value = [mock_chunk]
        self.mock_llm.generate.return_value = GenerationResult(
            content="Answer incorporating simulator context.",
            elapsed_seconds=0.3,
        )

        sim_ctx = {
            "supported_instructions": ["XIC", "OTE", "TON"],
            "controller_model": "1756-L85E",
        }

        self.pipeline.answer_question("Explain rung order", simulator_context=sim_ctx)

        call_args = self.mock_llm.generate.call_args
        prompt = call_args.kwargs["prompt"]
        self.assertIn("[SIMULATOR RUNTIME CONTEXT]", prompt)
        self.assertIn("1756-L85E", prompt)

    def test_empty_question_raises_value_error(self):
        """Verify empty question raises ValueError."""
        with self.assertRaises(ValueError):
            self.pipeline.answer_question("   ")


if __name__ == "__main__":
    unittest.main()
