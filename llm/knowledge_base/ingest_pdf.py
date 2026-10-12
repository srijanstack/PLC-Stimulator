"""
Deterministic PDF ingestion script for the PLC Chatbot knowledge base.

Extracts text page-by-page from PDFs in `knowledge_base/sources/`, inserts
clear page boundary markers, computes cryptographic hashes, and updates
document metadata in `knowledge_base/metadata/` while strictly preserving
any manually curated metadata fields.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdf

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("ingest_pdf")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_ROOT / "knowledge_base" / "sources"
EXTRACTED_DIR = PROJECT_ROOT / "knowledge_base" / "extracted"
METADATA_DIR = PROJECT_ROOT / "knowledge_base" / "metadata"


def calculate_sha256(filepath: Path) -> str:
    """Calculate the SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def detect_document_id(filename: str) -> str:
    """Generate a clean document ID from the filename if none exists."""
    stem = Path(filename).stem.lower().replace("-", "_").replace(" ", "_")
    return f"rockwell_{stem}"


def is_likely_index_document(page_count: int, extracted_text: str) -> Tuple[bool, str]:
    """Detect whether a document is merely an index or summary catalog.
    
    A document is flagged if it has 1-2 pages or explicitly describes itself
    as a manual index/links collection.
    """
    text_lower = extracted_text.lower()
    if page_count <= 2:
        if "collection of programming manuals" in text_lower or "publication number" in text_lower:
            return True, "Single/dual-page index listing manual publication numbers."
        return True, f"Suspiciously short document ({page_count} page(s))."
    
    if len(extracted_text.strip()) < 2000 and page_count <= 3:
        return True, "Extracted content is under 2000 characters."

    return False, ""


def extract_pdf(
    pdf_path: Path,
    force: bool = False,
) -> Dict[str, Any]:
    """Extract text from a single PDF and update metadata.
    
    Returns a report dictionary describing extraction results and warnings.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    file_name = pdf_path.name
    stem = pdf_path.stem
    sha256_hash = calculate_sha256(pdf_path)

    
    # Output file paths
    extracted_txt_path = EXTRACTED_DIR / f"{stem}.txt"
    metadata_json_path = METADATA_DIR / f"{stem}-metadata.json"

    # Support the existing legacy metadata naming convention for older PDFs.
    # Prefer an exact match first to avoid selecting the wrong document metadata.
    if not metadata_json_path.exists() and "-" in stem:
        parts = stem.split("-")
        legacy_name = f"{parts[0]}-{parts[1]}-metadata.json"
        legacy_path = METADATA_DIR / legacy_name
        if legacy_path.exists():
            metadata_json_path = legacy_path

    existing_metadata: Dict[str, Any] = {}
    if metadata_json_path.exists():
        try:
            with open(metadata_json_path, "r", encoding="utf-8-sig") as f:
                existing_metadata = json.load(f)
        except Exception as err:
            logger.warning(
                f"Could not read existing metadata at {metadata_json_path}: {err}"
            )


    # Check if re-extraction is needed
    already_extracted = extracted_txt_path.exists()
    hash_matches = existing_metadata.get("sha256") == sha256_hash

    if already_extracted and hash_matches and not force:
        logger.info(f"Skipping {file_name}: already extracted and SHA-256 matches.")
        return {
            "file_name": file_name,
            "status": "skipped",
            "reason": "already_extracted_matching_hash",
            "page_count": existing_metadata.get("page_count", 0),
            "sha256": sha256_hash,
            "is_index_only": existing_metadata.get("is_index_only", False),
        }

    logger.info(f"Extracting {file_name}...")
    reader = pypdf.PdfReader(str(pdf_path))
    page_count = len(reader.pages)
    pages_text: List[str] = []
    empty_pages: List[int] = []

    for idx, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ""
        except Exception as err:
            logger.warning(f"Error extracting page {idx} from {file_name}: {err}")
            txt = ""

        if not txt.strip():
            empty_pages.append(idx)

        # Page boundary marker
        pages_text.append(f"===== PDF PAGE {idx} =====\n{txt.strip()}\n")

    full_extracted_text = "\n".join(pages_text)

    # Save extracted text
    with open(extracted_txt_path, "w", encoding="utf-8") as f:
        f.write(full_extracted_text)

    # Detect if document is index-only
    is_index, index_reason = is_likely_index_document(page_count, full_extracted_text)

    # Update metadata while preserving manually curated fields
    updated_metadata: Dict[str, Any] = {
        "document_id": existing_metadata.get("document_id") or detect_document_id(file_name),
        "title": existing_metadata.get("title") or stem.replace("-", " "),
        "publication_number": existing_metadata.get("publication_number") or (stem.split("-")[0] + "-" + stem.split("-")[1] if "-" in stem else ""),
        "publisher": existing_metadata.get("publisher", "Rockwell Automation"),
        "source_url": existing_metadata.get("source_url", ""),
        "file_name": file_name,
        "sha256": sha256_hash,
        "page_count": page_count,
        "extracted_text": (
            str(extracted_txt_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if extracted_txt_path.is_relative_to(PROJECT_ROOT)
            else str(extracted_txt_path).replace("\\", "/")
        ),
        "character_count": len(full_extracted_text),
        "extraction_library": "pypdf",
        "is_index_only": is_index,
        "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    # Preserve any other manually added keys in existing_metadata
    for k, v in existing_metadata.items():
        if k not in updated_metadata and v is not None:
            updated_metadata[k] = v

    if is_index and index_reason:
        updated_metadata["index_warning"] = index_reason

    with open(metadata_json_path, "w", encoding="utf-8") as f:
        json.dump(updated_metadata, f, indent=2)

    return {
        "file_name": file_name,
        "status": "extracted",
        "page_count": page_count,
        "char_count": len(full_extracted_text),
        "empty_pages": empty_pages,
        "is_index_only": is_index,
        "index_reason": index_reason,
        "metadata_file": (
            str(metadata_json_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if metadata_json_path.is_relative_to(PROJECT_ROOT)
            else str(metadata_json_path).replace("\\", "/")
        ),
        "sha256": sha256_hash,
    }


def ingest_all_sources(force: bool = False) -> List[Dict[str, Any]]:
    """Scan knowledge_base/sources/ and ingest all PDF files."""
    if not SOURCES_DIR.exists():
        logger.error(f"Sources directory does not exist: {SOURCES_DIR}")
        return []

    pdf_files = sorted(list(SOURCES_DIR.glob("*.pdf")))
    if not pdf_files:
        logger.warning(f"No PDF files found in {SOURCES_DIR}")
        return []

    results: List[Dict[str, Any]] = []
    seen_hashes: Dict[str, str] = {}

    print("=" * 70)
    print(" Knowledge Base PDF Ingestion")
    print("=" * 70)

    for pdf in pdf_files:
        res = extract_pdf(pdf, force=force)
        sha = res["sha256"]
        if sha in seen_hashes:
            res["duplicate_of"] = seen_hashes[sha]
            logger.warning(f"Duplicate content detected: {pdf.name} matches {seen_hashes[sha]}")
        else:
            seen_hashes[sha] = pdf.name

        results.append(res)
        print(f"File: {res['file_name']}")
        print(f"  Status       : {res['status']}")
        print(f"  Pages        : {res['page_count']}")
        if res.get("is_index_only"):
            print(f"  [FLAG]       : Marked as index-only / catalog ({res.get('index_reason')})")
        if res.get("empty_pages"):
            print(f"  Empty Pages  : {len(res['empty_pages'])} page(s)")
        print(f"  SHA-256      : {res['sha256'][:16]}...")
        print("-" * 70)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest PDFs for the PLC RAG Knowledge Base.")
    parser.add_argument("--force", action="store_true", help="Force re-extraction even if SHA-256 matches.")
    args = parser.parse_args()
    ingest_all_sources(force=args.force)


if __name__ == "__main__":
    main()
