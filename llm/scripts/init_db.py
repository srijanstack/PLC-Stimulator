"""
Repeatable database initialization script for PostgreSQL + pgvector.

Creates the database if missing, enables the pgvector extension, and initializes
the RAG schema for documents and chunks.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.config import RAGConfig

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("init_db")

INIT_SQL_PATH = Path(__file__).resolve().parent / "init_db.sql"


def parse_db_url(database_url: str):
    """Parse PostgreSQL URL into connection parameters."""
    parsed = urlparse(database_url)
    dbname = parsed.path.lstrip("/") or "plc_simulator"
    user = parsed.username or "postgres"
    password = unquote(parsed.password or "")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    return {
        "dbname": dbname,
        "user": user,
        "password": password,
        "host": host,
        "port": port,
    }


def ensure_database_exists(params: dict) -> bool:
    """Connect to maintenance database ('postgres') and create target database if it does not exist."""
    target_dbname = params["dbname"]
    maint_params = dict(params)
    maint_params["dbname"] = "postgres"

    try:
        conn = psycopg2.connect(**maint_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_dbname,))
            exists = cur.fetchone() is not None
            if not exists:
                logger.info(f"Target database '{target_dbname}' does not exist. Creating...")
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_dbname)))
                logger.info(f"Database '{target_dbname}' created successfully.")
            else:
                logger.info(f"Target database '{target_dbname}' already exists.")
        conn.close()
        return True
    except psycopg2.OperationalError as err:
        logger.error(f"Could not connect to PostgreSQL server at {params['host']}:{params['port']}: {err}")
        return False


def initialize_schema(database_url: str) -> bool:
    """Run schema creation and extension enablement against the target database."""
    params = parse_db_url(database_url)

    print("=" * 70)
    print(" PostgreSQL + pgvector Database Initialization")
    print("=" * 70)
    print(f" Target Host     : {params['host']}:{params['port']}")
    print(f" Target Database : {params['dbname']}")
    print(f" Target User     : {params['user']}")
    print("=" * 70)

    # 1. Ensure database exists
    logger.info("Checking database existence...")
    if not ensure_database_exists(params):
        print("\n[ERROR] Connection to PostgreSQL failed.")
        print("Troubleshooting steps:")
        print("  1. Verify the PostgreSQL service is running on Windows (e.g. Services -> postgresql-x64-17).")
        print("  2. Verify credentials and port in DATABASE_URL in your .env file.")
        print("  3. Ensure user has permission to create databases.")
        return False

    # 2. Connect to target database and execute initialization SQL
    try:
        conn = psycopg2.connect(**params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    except psycopg2.OperationalError as err:
        logger.error(f"Failed to connect to target database '{params['dbname']}': {err}")
        return False

    try:
        with conn.cursor() as cur:
            # Step 2a: Enable vector extension
            logger.info("Enabling pgvector extension ('CREATE EXTENSION IF NOT EXISTS vector')...")
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                logger.info("[OK] pgvector extension enabled.")
            except psycopg2.Error as err:
                logger.error(f"Failed to enable 'vector' extension: {err}")
                print("\n[BLOCKED] pgvector extension is not installed in your PostgreSQL instance.")
                print("Windows Installation Guide for pgvector:")
                print("  Option A (Precompiled binaries for Windows):")
                print("    1. Download the pgvector release zip matching your PostgreSQL version (PG 17 / 18).")
                print("    2. Copy vector.dll to: C:\\Program Files\\PostgreSQL\\<version>\\lib")
                print("    3. Copy vector.control and vector--*.sql to: C:\\Program Files\\PostgreSQL\\<version>\\share\\extension")
                print("  Option B (Build from source with Visual Studio / C++):")
                print("    git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git")
                print("    nmake /F Makefile.win")
                print("    nmake /F Makefile.win install")
                conn.close()
                return False

            # Step 2b: Read and execute init_db.sql
            if not INIT_SQL_PATH.exists():
                logger.error(f"SQL file not found at {INIT_SQL_PATH}")
                return False

            with open(INIT_SQL_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            logger.info("Executing RAG table and index creation...")
            cur.execute(schema_sql)
            logger.info("[OK] Tables and indexes created successfully:")
            logger.info("     - rag_documents")
            logger.info("     - rag_document_chunks (embedding vector(384))")
            logger.info("     - idx_rag_chunks_embedding_hnsw")

        conn.close()
        print("\n" + "=" * 70)
        print(" Database initialization complete! RAG foundation is ready.")
        print("=" * 70)
        return True

    except Exception as err:
        logger.error(f"Error during schema initialization: {err}")
        conn.close()
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize PostgreSQL database and pgvector schema.")
    parser.add_argument("--db-url", type=str, default=None, help="Override DATABASE_URL")
    args = parser.parse_args()

    config = RAGConfig.from_env()
    db_url = args.db_url or config.database_url

    success = initialize_schema(db_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
