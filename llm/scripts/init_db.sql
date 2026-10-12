-- =============================================================================
-- Database Initialization & Schema Migration for PLC Simulator RAG Assistant
-- Database: PostgreSQL with pgvector extension
-- =============================================================================

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Ingested Technical Documents (Parent Catalog)
CREATE TABLE IF NOT EXISTS rag_documents (
    id VARCHAR(128) PRIMARY KEY,
    title TEXT NOT NULL,
    publication_number VARCHAR(64),
    publisher TEXT DEFAULT 'Rockwell Automation',
    source_url TEXT,
    file_name VARCHAR(255) NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    page_count INT NOT NULL,
    is_index_only BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Document Chunks with Vector Embeddings (384-dim for all-MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS rag_document_chunks (
    id VARCHAR(160) PRIMARY KEY,
    document_id VARCHAR(128) NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
    page_number INT NOT NULL,
    end_page_number INT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding vector(384) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. B-Tree Indexes for fast filtering and joins
CREATE INDEX IF NOT EXISTS idx_rag_chunks_document_id ON rag_document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_page ON rag_document_chunks(page_number);
CREATE INDEX IF NOT EXISTS idx_rag_documents_sha256 ON rag_documents(sha256);

-- 5. HNSW Vector Similarity Index (Cosine metric)
-- Note: Uses vector_cosine_ops for cosine similarity search
CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding_hnsw 
ON rag_document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

