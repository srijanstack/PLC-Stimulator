"""
Unit tests for text cleaning, chunking, and PDF page attribution.
"""

import unittest

from rag.chunker import DocumentChunker, parse_pages_from_extracted_text
from rag.cleaning import clean_text


class TestCleaningAndChunking(unittest.TestCase):
    """Test suite for document cleaning and chunking."""

    def test_clean_text_preserves_plc_instructions(self):
        """Verify that instruction names, operands, and publication numbers are preserved."""
        raw = "The  XIC (Examine If Closed) and   OTE (Output Energize) instructions.\n\n" \
              "See publication 1756-RM003 for details. Tag: Motor_Start_PB [BOOL]."

        cleaned = clean_text(raw)
        self.assertIn("XIC (Examine If Closed)", cleaned)
        self.assertIn("OTE (Output Energize)", cleaned)
        self.assertIn("1756-RM003", cleaned)
        self.assertIn("Motor_Start_PB [BOOL]", cleaned)
        # Verify excess whitespace was collapsed
        self.assertNotIn("  XIC", cleaned)

    def test_parse_pages_from_extracted_text(self):
        """Test parsing text containing PDF page boundary markers."""
        sample = (
            "===== PDF PAGE 1 =====\n"
            "This is content on page one.\n\n"
            "===== PDF PAGE 2 =====\n"
            "This is content on page two.\n\n"
            "===== PDF PAGE 3 =====\n"
            "Final page content.\n"
        )
        pages = parse_pages_from_extracted_text(sample)
        self.assertEqual(len(pages), 3)
        self.assertEqual(pages[0][0], 1)
        self.assertIn("page one", pages[0][1])
        self.assertEqual(pages[1][0], 2)
        self.assertIn("page two", pages[1][1])
        self.assertEqual(pages[2][0], 3)
        self.assertIn("Final page", pages[2][1])

    def test_chunker_page_attribution_and_metadata(self):
        """Verify chunk boundaries, page attribution, and stable IDs."""
        sample_doc = (
            "===== PDF PAGE 10 =====\n"
            "Paragraph A describing TON timer parameters: PRE (Preset), ACC (Accumulator).\n\n"
            "Paragraph B detailing timer status bits: EN, TT, DN.\n\n"
            "===== PDF PAGE 11 =====\n"
            "Paragraph C explaining reset behavior with the RES instruction.\n\n"
            "Paragraph D explaining ladder rung false condition effects."
        )

        doc_meta = {
            "document_id": "rockwell_1756_rm003",
            "title": "Logix 5000 General Instructions",
            "publication_number": "1756-RM003",
            "file_name": "1756-RM003.pdf",
        }

        # Set small chunk size to trigger multi-chunk output
        chunker = DocumentChunker(chunk_size=150, chunk_overlap=30, min_chunk_length=30)
        chunks = chunker.chunk_document(sample_doc, doc_meta)

        self.assertGreater(len(chunks), 1)
        for i, c in enumerate(chunks):
            # Verify stable ID pattern
            self.assertEqual(c.id, f"rockwell_1756_rm003_c{i:05d}")
            self.assertEqual(c.document_id, "rockwell_1756_rm003")
            self.assertEqual(c.title, "Logix 5000 General Instructions")
            self.assertEqual(c.publication_number, "1756-RM003")
            self.assertGreaterEqual(c.page_number, 10)
            self.assertLessEqual(c.end_page_number, 11)
            self.assertGreaterEqual(len(c.content), 30)
            self.assertEqual(len(c.content_hash), 64)

    def test_chunker_overlap_validation(self):
        """Verify that overlap >= chunk_size raises ValueError."""
        with self.assertRaises(ValueError):
            DocumentChunker(chunk_size=500, chunk_overlap=500)

        with self.assertRaises(ValueError):
            DocumentChunker(chunk_size=500, chunk_overlap=600)

    def test_chunker_empty_input(self):
        """Verify empty text produces no chunks without error."""
        chunker = DocumentChunker()
        chunks = chunker.chunk_document("", {"document_id": "doc1"})
        self.assertEqual(chunks, [])


if __name__ == "__main__":
    unittest.main()

