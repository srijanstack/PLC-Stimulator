"""
Comprehensive health and integrity check for the PLC Chatbot knowledge base.

Checks source PDFs, extracted text files, metadata JSON completeness, page markers,
hash duplicates, and PostgreSQL vector index status.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.config import RAGConfig
from rag.vector_store import VectorStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("check_kb")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_ROOT / "knowledge_base" / "sources"
EXTRACTED_DIR = PROJECT_ROOT / "knowledge_base" / "extracted"
METADATA_DIR = PROJECT_ROOT / "knowledge_base" / "metadata"


def check_knowledge_base() -> int:
    """Execute complete validation of knowledge base artifacts."""
    print("=" * 70)
    print(" Knowledge Base Integrity & Readiness Report")
    print("=" * 70)

    pdf_files = sorted(list(SOURCES_DIR.glob("*.pdf"))) if SOURCES_DIR.exists() else []
    print(f" Source PDFs Found       : {len(pdf_files)}")

    issues_found = 0
    seen_hashes: Dict[str, str] = {}

    print("\n--- Document Verification ---")
    for pdf in pdf_files:
        stem = pdf.stem
        extracted_txt = EXTRACTED_DIR / f"{stem}.txt"
        
        # Find corresponding metadata file
        meta_candidates = list(METADATA_DIR.glob(f"*{stem.split('-')[0]}*{stem.split('-')[1]}*.json")) if "-" in stem else []
        meta_file = meta_candidates[0] if meta_candidates else (METADATA_DIR / f"{stem}-metadata.json")

        print(f"\n[Document] {pdf.name}")
        file_size_kb = round(pdf.stat().st_size / 1024, 1)
        print(f"  PDF Size             : {file_size_kb} KB")

        # Hash check
        sha256 = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if sha256 in seen_hashes:
            print(f"  [WARN] Duplicate Content: Matches {seen_hashes[sha256]}")
            issues_found += 1
        else:
            seen_hashes[sha256] = pdf.name

        # Extracted text check
        if not extracted_txt.exists():
            print(f"  [ERROR] Extracted text missing at: {extracted_txt.name}")
            issues_found += 1
        else:
            txt_content = extracted_txt.read_text(encoding="utf-8", errors="replace")
            char_count = len(txt_content)
            page_markers_count = txt_content.count("===== PDF PAGE")
            print(f"  Extracted Characters : {char_count:,} chars")
            print(f"  Page Markers Count   : {page_markers_count} pages tagged")

            if char_count < 1500 and "PM001" not in stem:
                print(f"  [WARN] Suspiciously short extraction ({char_count} chars).")
                issues_found += 1
            if page_markers_count == 0:
                print("  [WARN] Missing page boundary markers in extracted text.")
                issues_found += 1

        # Metadata check
        if not meta_file.exists():
            print(f"  [WARN] Metadata file missing: {meta_file.name}")
            issues_found += 1
        else:
            try:
                meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
                req_fields = ["document_id", "title", "publication_number", "sha256", "page_count"]
                missing_fields = [f for f in req_fields if not meta_data.get(f)]
                if missing_fields:
                    print(f"  [WARN] Incomplete metadata. Missing: {missing_fields}")
                    issues_found += 1
                else:
                    is_index = meta_data.get("is_index_only", False)
                    status_str = "Index-only catalog" if is_index else "Full Reference Manual"
                    print(f"  Classification       : {status_str}")
                    print(f"  Document ID          : {meta_data['document_id']}")
                    print(f"  Reported Pages       : {meta_data['page_count']}")
            except Exception as err:
                print(f"  [ERROR] Corrupted metadata JSON: {err}")
                issues_found += 1

    # Database & Vector Index Check
    print("\n--- Database & Vector Index Status ---")
    config = RAGConfig.from_env()
    print(f" Database Target        : {config.to_safe_dict()['database_url']}")

    try:
        store = VectorStore(config=config)
        health = store.check_health()
        if not health.get("reachable"):
            print(f"  [STATUS] PostgreSQL is unreachable: {health.get('error')}")
            print("  Note: PostgreSQL must be running and credentials configured in .env for vector search.")
        else:
            print("  [STATUS] PostgreSQL is reachable.")
            print(f"  pgvector Extension   : {'Installed (v' + str(health.get('pgvector_version')) + ')' if health.get('pgvector_installed') else 'NOT INSTALLED'}")
            print(f"  RAG Tables Ready     : {'YES' if health.get('tables_initialized') else 'NO'}")

            if health.get("tables_initialized"):
                status = store.get_status()
                print(f"  Indexed Documents    : {status.get('documents', 0)}")
                print(f"  Indexed Chunks       : {status.get('chunks', 0)}")
        store.close()
    except Exception as err:
        print(f"  [STATUS] Database check error: {err}")

    print("\n" + "=" * 70)
    print(f" Summary: Verification finished with {issues_found} warning(s)/error(s).")
    print("=" * 70)
    return 0 if issues_found == 0 else 1


def main() -> None:
    check_knowledge_base()


if __name__ == "__main__":
    main()
