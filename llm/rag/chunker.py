"""
Document chunking with precise page attribution for Rockwell Automation manuals.

Splits text into chunks preserving PDF page numbers, avoiding cross-document
leakage, and generating deterministic, stable chunk identifiers and content hashes.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from rag.cleaning import clean_text


@dataclass
class DocumentChunk:
    """Represents a discrete semantic chunk of a document."""

    id: str
    """Stable, unique chunk ID, e.g. 'rockwell_1756_rm003_c0042'."""

    document_id: str
    """Foreign key referencing the parent document ID."""

    title: str
    """Title of the source manual."""

    publication_number: str
    """Publication number (e.g., 1756-RM003)."""

    source_filename: str
    """Original PDF or text filename."""

    page_number: int
    """Start page number in the original PDF."""

    end_page_number: int
    """End page number in the original PDF."""

    chunk_index: int
    """Sequential zero-based index of this chunk in the document."""

    content: str
    """Cleaned text content of the chunk."""

    content_hash: str
    """SHA-256 hash of the content string."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata dictionary."""


PAGE_MARKER_REGEX = re.compile(r"^=====\s*PDF\s*PAGE\s*(\d+)\s*=====$", re.MULTILINE)


def parse_pages_from_extracted_text(text: str) -> List[Tuple[int, str]]:
    """Parse extracted text with '===== PDF PAGE X =====' markers into (page_num, page_text) tuples."""
    matches = list(PAGE_MARKER_REGEX.finditer(text))
    if not matches:
        # Fallback if no page markers are present
        return [(1, text)]

    pages: List[Tuple[int, str]] = []
    for i, match in enumerate(matches):
        page_num = int(match.group(1))
        start_idx = match.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        page_content = text[start_idx:end_idx].strip()
        pages.append((page_num, page_content))

    return pages


class DocumentChunker:
    """Splits documents into overlapping chunks with precise PDF page tracking."""

    def __init__(
        self,
        chunk_size: int = 2400,
        chunk_overlap: int = 400,
        min_chunk_length: int = 80,
    ) -> None:
        """Initialize chunker.

        Args:
            chunk_size: Target maximum characters per chunk (approx. 600-700 tokens).
            chunk_overlap: Target overlap characters between consecutive chunks (approx. 100-120 tokens).
            min_chunk_length: Minimum character length to retain as a standalone chunk.
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_length = min_chunk_length

    def chunk_document(
        self,
        extracted_text: str,
        document_metadata: Dict[str, Any],
    ) -> List[DocumentChunk]:
        """Split a document into DocumentChunk objects with page ranges.

        Args:
            extracted_text: Raw or extracted text containing page markers.
            document_metadata: Dictionary with document_id, title, publication_number, etc.

        Returns:
            List of DocumentChunk objects.
        """
        doc_id = document_metadata.get("document_id", "unknown_doc")
        title = document_metadata.get("title", "")
        pub_num = document_metadata.get("publication_number", "")
        filename = document_metadata.get("file_name", "")

        pages = parse_pages_from_extracted_text(extracted_text)
        if not pages:
            return []

        # Build paragraph units with page tags
        # Each unit: (text, page_num)
        units: List[Tuple[str, int]] = []
        for page_num, raw_page_text in pages:
            cleaned_page = clean_text(raw_page_text)
            if not cleaned_page:
                continue

            # Split page by double newlines into paragraphs
            paragraphs = [p.strip() for p in cleaned_page.split("\n\n") if p.strip()]
            for para in paragraphs:
                units.append((para, page_num))

        if not units:
            return []

        chunks: List[DocumentChunk] = []
        chunk_idx = 0
        current_paragraphs: List[str] = []
        current_pages: List[int] = []
        current_len = 0

        for para, page_num in units:
            para_len = len(para)

            # If a single paragraph exceeds chunk_size, split by sentences or chunks
            if para_len > self.chunk_size:
                # Flush existing buffer first
                if current_paragraphs:
                    chunk = self._create_chunk(
                        doc_id=doc_id,
                        title=title,
                        pub_num=pub_num,
                        filename=filename,
                        chunk_idx=chunk_idx,
                        paragraphs=current_paragraphs,
                        pages=current_pages,
                    )
                    if chunk:
                        chunks.append(chunk)
                        chunk_idx += 1
                    current_paragraphs = []
                    current_pages = []
                    current_len = 0

                # Split the large paragraph into sub-slices
                sub_slices = self._split_large_text(para, self.chunk_size, self.chunk_overlap)
                for sub_slice in sub_slices:
                    chunk = self._create_chunk(
                        doc_id=doc_id,
                        title=title,
                        pub_num=pub_num,
                        filename=filename,
                        chunk_idx=chunk_idx,
                        paragraphs=[sub_slice],
                        pages=[page_num],
                    )
                    if chunk:
                        chunks.append(chunk)
                        chunk_idx += 1
                continue

            if current_len + para_len + 2 > self.chunk_size and current_paragraphs:
                # Buffer is full, emit chunk
                chunk = self._create_chunk(
                    doc_id=doc_id,
                    title=title,
                    pub_num=pub_num,
                    filename=filename,
                    chunk_idx=chunk_idx,
                    paragraphs=current_paragraphs,
                    pages=current_pages,
                )
                if chunk:
                    chunks.append(chunk)
                    chunk_idx += 1

                # Carry over overlap paragraphs
                overlap_paras: List[str] = []
                overlap_pages: List[int] = []
                overlap_len = 0

                for p, pg in reversed(list(zip(current_paragraphs, current_pages))):
                    if overlap_len + len(p) <= self.chunk_overlap:
                        overlap_paras.insert(0, p)
                        overlap_pages.insert(0, pg)
                        overlap_len += len(p) + 2
                    else:
                        break

                current_paragraphs = overlap_paras
                current_pages = overlap_pages
                current_len = overlap_len

            current_paragraphs.append(para)
            current_pages.append(page_num)
            current_len += para_len + 2

        # Emit any remaining text in buffer
        if current_paragraphs:
            chunk = self._create_chunk(
                doc_id=doc_id,
                title=title,
                pub_num=pub_num,
                filename=filename,
                chunk_idx=chunk_idx,
                paragraphs=current_paragraphs,
                pages=current_pages,
            )
            if chunk:
                chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        doc_id: str,
        title: str,
        pub_num: str,
        filename: str,
        chunk_idx: int,
        paragraphs: List[str],
        pages: List[int],
    ) -> Optional[DocumentChunk]:
        """Create a validated DocumentChunk object."""
        combined_text = "\n\n".join(paragraphs).strip()
        if len(combined_text) < self.min_chunk_length:
            return None

        start_page = min(pages) if pages else 1
        end_page = max(pages) if pages else 1
        chunk_id = f"{doc_id}_c{chunk_idx:05d}"
        content_hash = hashlib.sha256(combined_text.encode("utf-8")).hexdigest()

        return DocumentChunk(
            id=chunk_id,
            document_id=doc_id,
            title=title,
            publication_number=pub_num,
            source_filename=filename,
            page_number=start_page,
            end_page_number=end_page,
            chunk_index=chunk_idx,
            content=combined_text,
            content_hash=content_hash,
            metadata={
                "document_id": doc_id,
                "title": title,
                "publication_number": pub_num,
                "source_filename": filename,
                "start_page": start_page,
                "end_page": end_page,
                "char_length": len(combined_text),
            },
        )

    @staticmethod
    def _split_large_text(text: str, max_size: int, overlap: int) -> List[str]:
        """Slice large single blocks of text by sentence or character stride."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        slices: List[str] = []
        buf: List[str] = []
        buf_len = 0

        for s in sentences:
            if buf_len + len(s) + 1 > max_size and buf:
                slices.append(" ".join(buf).strip())
                buf = [buf[-1]] if overlap > 0 and len(buf[-1]) <= overlap else []
                buf_len = sum(len(x) + 1 for x in buf)

            buf.append(s)
            buf_len += len(s) + 1

        if buf:
            slices.append(" ".join(buf).strip())

        return slices

