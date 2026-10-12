"""
Build or update the PostgreSQL + pgvector knowledge base index.

Workflow:
1. Ingest/verify PDFs in `knowledge_base/sources/`.
2. Load extracted text and metadata.
3. Identify skipped documents (e.g., index-only catalogs like 1756-PM001).
4. Clean and chunk valid manuals with exact PDF page attribution.
5. Generate dense vector embeddings using local SentenceTransformer.
6. Persist documents, chunks, and embeddings idempotently into PostgreSQL.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from knowledge_base.ingest_pdf import ingest_all_sources
from rag.chunker import DocumentChunk, DocumentChunker
from rag.config import RAGConfig
from rag.embeddings import get_embedder
from rag.vector_store import VectorStore, VectorStoreError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("build_index")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = PROJECT_ROOT / "knowledge_base" / "extracted"
METADATA_DIR = PROJECT_ROOT / "knowledge_base" / "metadata"


def build_knowledge_base_index(
    force_reindex: bool = False,
    batch_size: int = 64,
) -> int:
    """Build or incrementally update the PostgreSQL + pgvector index.

    Returns:
        0 on success, 1 on error.
    """
    config = RAGConfig.from_env()

    print("=" * 70)
    print(" Building Knowledge Base Vector Index (PostgreSQL + pgvector)")
    print("=" * 70)
    print(f" Database Target : {config.to_safe_dict()['database_url']}")
    print(f" Embedding Model : {config.embedding_model_name} (dim: {config.embedding_dimension})")
    print(f" Chunk Size      : {config.chunk_size} chars | Overlap: {config.chunk_overlap} chars")
    print("=" * 70)

    # 1. Run PDF ingestion to ensure text and metadata are up-to-date
    print("\n[1/5] Ingesting and verifying source PDFs...")
    ingest_all_sources(force=False)

    # 2. Check VectorStore connectivity and schema
    print("\n[2/5] Connecting to PostgreSQL vector store...")
    vector_store = VectorStore(config=config)
    health = vector_store.check_health()
    if not health.get("reachable"):
        print(f"\n[ERROR] Could not connect to PostgreSQL: {health.get('error')}")
        print("Please ensure PostgreSQL is running and DATABASE_URL is configured in .env.")
        return 1

    if not health.get("tables_initialized"):
        print("\n[ERROR] Vector tables are not initialized in PostgreSQL.")
        print("Please run: python scripts/init_db.py")
        return 1

    # 3. Load metadata files and determine which documents to index
    print("\n[3/5] Inspecting extracted documents and metadata...")
    metadata_files = sorted(list(METADATA_DIR.glob("*.json")))
    if not metadata_files:
        print("[ERROR] No metadata files found in knowledge_base/metadata/.")
        return 1

    chunker = DocumentChunker(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )
    embedder = get_embedder(model_name=config.embedding_model_name)

    total_docs_indexed = 0
    total_chunks_indexed = 0
    skipped_docs: List[Dict[str, str]] = []

    for meta_file in metadata_files:
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as err:
            logger.error(f"Could not load metadata from {meta_file}: {err}")
            continue

        doc_id = meta.get("document_id")
        file_name = meta.get("file_name", meta_file.stem)
        page_count = meta.get("page_count", 0)
        is_index_only = meta.get("is_index_only", False)

        # Skip catalog/index-only manuals
        if is_index_only:
            reason = meta.get("index_warning", "Marked as index-only catalog")
            skipped_docs.append({"file": file_name, "reason": reason})
            logger.info(f"Skipping {file_name} from vector indexing: {reason}")
            # Still record document in catalog table so system knows it was processed
            vector_store.upsert_document(meta)
            continue

        extracted_rel_path = meta.get("extracted_text")
        if not extracted_rel_path:
            skipped_docs.append({"file": file_name, "reason": "No extracted_text path in metadata"})
            continue

        extracted_full_path = PROJECT_ROOT / extracted_rel_path
        if not extracted_full_path.exists():
            skipped_docs.append({"file": file_name, "reason": f"Extracted text file missing: {extracted_rel_path}"})
            continue

        # Check existing document hash in DB
        existing_doc = vector_store.get_document(doc_id)
        if existing_doc and existing_doc["sha256"] == meta["sha256"] and not force_reindex:
            logger.info(f"Document '{file_name}' already indexed with matching SHA-256. Skipping chunking.")
            continue

        print(f"\nProcessing: {meta.get('title', file_name)} ({page_count} pages)")
        with open(extracted_full_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # Chunk document
        chunks = chunker.chunk_document(raw_text, meta)
        print(f"  Generated {len(chunks)} chunks.")
        if not chunks:
            logger.warning(f"No valid chunks generated for {file_name}.")
            continue

        # Upsert parent document entry
        vector_store.upsert_document(meta)

        # 4. Generate embeddings and batch upsert
        print(f"  Generating embeddings in batches of {batch_size}...")
        all_chunk_texts = [c.content for c in chunks]

        # Process in batches to control memory
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_texts = all_chunk_texts[i : i + batch_size]
            batch_embeddings = embedder.embed_documents(batch_texts, batch_size=batch_size)

            vector_store.upsert_chunks(batch_chunks, batch_embeddings)
            print(f"    Indexed chunks {i + 1} to {min(i + batch_size, len(chunks))} / {len(chunks)}...")

        total_docs_indexed += 1
        total_chunks_indexed += len(chunks)

    # 5. Summary Report
    print("\n" + "=" * 70)
    print(" Indexing Complete")
    print("=" * 70)
    print(f" Documents Indexed   : {total_docs_indexed}")
    print(f" Chunks Stored       : {total_chunks_indexed}")

    if skipped_docs:
        print("\nSkipped Documents:")
        for s in skipped_docs:
            print(f"  - {s['file']}: {s['reason']}")

    status = vector_store.get_status()
    print(f"\nTotal Knowledge Base in DB:")
    print(f"  Total Catalog Documents : {status.get('documents', 0)}")
    print(f"  Total Indexed Chunks    : {status.get('chunks', 0)}")
    print("=" * 70)

    vector_store.close()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Build knowledge base vector index in PostgreSQL.")
    parser.add_argument("--force", action="store_true", help="Force reindexing of all documents.")
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding batch size (default: 64).")
    args = parser.parse_args()

    sys.exit(build_knowledge_base_index(force_reindex=args.force, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
