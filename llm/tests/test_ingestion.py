"""
Unit tests for PDF ingestion and metadata management.
"""

import json
import tempfile
import unittest
from pathlib import Path

import pypdf

from knowledge_base.ingest_pdf import (
    calculate_sha256,
    detect_document_id,
    extract_pdf,
    is_likely_index_document,
)


class TestPDFIngestion(unittest.TestCase):
    """Test suite for PDF extraction and metadata tracking."""

    def test_calculate_sha256(self):
        """Test SHA-256 calculation on sample content."""
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"Rockwell Automation Logix 5000 Instructions")
            temp_path = Path(tf.name)

        try:
            h = calculate_sha256(temp_path)
            self.assertEqual(len(h), 64)
            self.assertIsInstance(h, str)
        finally:
            temp_path.unlink()

    def test_detect_document_id(self):
        """Test clean document ID generation from filenames."""
        doc_id = detect_document_id("1756-RM003-General-Instructions-Reference.pdf")
        self.assertEqual(doc_id, "rockwell_1756_rm003_general_instructions_reference")

    def test_is_likely_index_document(self):
        """Test detection of index-only catalogs vs full programming manuals."""
        # 1-page catalog listing publication numbers
        catalog_text = "Logix 5000 Controllers Common Procedures. Links to a collection of programming manuals. Add-On Instructions 1756-PM010."
        is_index, reason = is_likely_index_document(page_count=1, extracted_text=catalog_text)
        self.assertTrue(is_index)
        self.assertIn("index", reason.lower())

        # Full manual (e.g. 927 pages)
        full_text = "This manual describes general instructions for Logix 5000 controllers..."
        is_full_index, _ = is_likely_index_document(page_count=927, extracted_text=full_text)
        self.assertFalse(is_full_index)

    def test_page_markers_and_metadata_preservation(self):
        """Test that extract_pdf writes page boundary markers and preserves curated metadata."""
        # Create a tiny 2-page PDF in memory
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.add_blank_page(width=72, height=72)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            pdf_path = tmp_root / "test-manual.pdf"
            with open(pdf_path, "wb") as f:
                writer.write(f)

            # Pre-seed a curated metadata file
            meta_dir = tmp_root / "metadata"
            meta_dir.mkdir()
            curated_meta_file = meta_dir / "test-manual-metadata.json"
            curated_meta = {
                "document_id": "custom_curated_id_123",
                "title": "Manually Verified Title",
                "publisher": "Rockwell Automation, Inc.",
                "curated_note": "Do not overwrite me",
            }
            curated_meta_file.write_text(json.dumps(curated_meta), encoding="utf-8")

            # Patch project paths
            from unittest.mock import patch
            with patch("knowledge_base.ingest_pdf.EXTRACTED_DIR", tmp_root / "extracted"), \
                 patch("knowledge_base.ingest_pdf.METADATA_DIR", meta_dir):
                
                result = extract_pdf(pdf_path, force=True)

                self.assertEqual(result["status"], "extracted")
                self.assertEqual(result["page_count"], 2)

                # Verify extracted text contains markers
                extracted_txt = (tmp_root / "extracted" / "test-manual.txt").read_text(encoding="utf-8")
                self.assertIn("===== PDF PAGE 1 =====", extracted_txt)
                self.assertIn("===== PDF PAGE 2 =====", extracted_txt)

                # Verify curated metadata was preserved
                updated_meta = json.loads(curated_meta_file.read_text(encoding="utf-8"))
                self.assertEqual(updated_meta["document_id"], "custom_curated_id_123")
                self.assertEqual(updated_meta["title"], "Manually Verified Title")
                self.assertEqual(updated_meta["curated_note"], "Do not overwrite me")
                self.assertEqual(updated_meta["page_count"], 2)


if __name__ == "__main__":
    unittest.main()

