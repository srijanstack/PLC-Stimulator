# PLC Simulator Embedded AI Assistant (RAG + llama.cpp + pgvector)

A modular, offline-first Retrieval-Augmented Generation (RAG) assistant backend for industrial PLC simulation, supporting **Allen-Bradley / Rockwell Logix 5000** and **Siemens S7-1200** controllers.

The system answers engineering questions regarding industrial automation, ladder logic instructions (`XIC`, `XIO`, `OTE`, `TON`, `CTU`, `NO Contact`, `NC Contact`, `Output Coil`, etc.), memory addressing, and troubleshooting based strictly on authoritative reference manuals. It runs entirely on local hardware with zero cloud dependencies.

---

## 1. System Architecture

```text
                                  +---------------------------------------+
                                  |     PLC Studio Frontend / Backend     |
                                  |   (React 19 / TypeScript / Node.js)   |
                                  +-------------------+-------------------+
                                                      |
                                            REST API (Port 8001)
                                                      v
+-----------------------------------------------------------------------------------------+
|                              FastAPI Embedded RAG Service                               |
|                                     (Port: 8001)                                        |
|                                                                                         |
|  +------------------+   +----------------------+   +---------------------------------+  |
|  | GET /health(z)   |   | GET /knowledge-base  |   | POST /retrieve   | POST /chat   |  |
|  +--------+---------+   +----------+-----------+   +--------+-----------------+------+  |
|           |                        |                        |                 |         |
+-----------|------------------------|------------------------|-----------------|---------+
            |                        |                        |                 |
            v                        v                        v                 |
+----------------------------------------------------------------+              |
|                     PostgreSQL Database                        |              |
|                 (Port: 5432 / pgvector extension)              |              |
|                                                                |              |
|  - rag_documents: Metadata, publication codes, page counts     |              |
|  - rag_document_chunks: Text chunks, page ranges, HNSW index   |              |
+----------------------------------------------------------------+              |
            ^                                                                   |
            | (Generates 384-d normalized embeddings)                          |
+-----------+-----------------------+                                           |
|       Local Embedding Model       |                                           |
|  (all-MiniLM-L6-v2 via PyTorch)   |                                           |
+-----------------------------------+                                           |
                                                                                |
                                     (Grounded Prompt + Context)                |
                                     v                                          v
+-----------------------------------------------------------------------------------------+
|                           Local Inference Server (llama.cpp)                            |
|                     (Port: 8080 - ggml-org/Qwen3-1.7B-GGUF:Q4_K_M)                      |
|                                                                                         |
|  - GPU-offloaded to NVIDIA RTX (or CPU fallback)                                        |
|  - Fast token generation with thinking-mode suppression support                         |
+-----------------------------------------------------------------------------------------+
```

### Core Subsystems
1. **API Service (`api/`)**: FastAPI application providing `/health`, `/healthz`, `/knowledge-base/status`, `/retrieve`, and `/chat` endpoints with full CORS support.
2. **Knowledge Base Ingestion & Chunking (`knowledge_base/`, `rag/`)**: Extracts page-tagged text from Rockwell and Siemens reference PDFs, normalizes ladder logic syntax, and chunks text with precise page attribution (`===== PDF PAGE N =====`).
3. **Vector Database (`rag/vector_store.py`)**: Uses PostgreSQL with `pgvector` to store 384-dimensional dense vectors with HNSW cosine distance indexing (`vector_cosine_ops`) for sub-millisecond retrieval.
4. **Local Embedding Engine (`rag/embeddings.py`)**: Singleton `sentence-transformers/all-MiniLM-L6-v2` generating 384-dimensional normalized vector embeddings on CPU/GPU.
5. **RAG Pipeline (`rag/pipeline.py`)**: Retrieves top-$k$ semantically relevant chunks, validates against similarity thresholds, injects active simulator context (tags, rungs, hardware), and formats strict grounding prompts for the LLM.
6. **Local LLM Client (`llm/`)**: Modular, streaming-capable HTTP client communicating with `llama-server` over OpenAI-compatible endpoints.

---

## 2. Hardware Profile & System Requirements

- **Operating System**: Windows 10/11 (64-bit)
- **Python**: Python 3.10+ (tested with Python 3.10.11)
- **Target Hardware**:
  - **GPU**: NVIDIA GeForce RTX (e.g. RTX 2050 / 3060+ with CUDA support) or multi-core CPU
  - **System RAM**: 16 GB recommended
- **Database**: PostgreSQL 16 or 17 (x64) with the `pgvector` extension
- **Inference Runtime**: `llama.cpp` (`llama-server`) build with CUDA or Vulkan acceleration, or Ollama
- **Default Model**: `ggml-org/Qwen3-1.7B-GGUF` (`Q4_K_M` quantization, ~1.3 GB VRAM)

---

## 3. PostgreSQL & pgvector Setup on Windows

The assistant stores document embeddings in a shared PostgreSQL instance.

### Step 1: Install PostgreSQL
1. Download the PostgreSQL Windows installer (version 16 or 17) from [EnterpriseDB](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads).
2. Set an administrative password for the `postgres` user (default port `5432`).
3. Verify the Windows Service is running:
   ```powershell
   Get-Service -Name "postgresql*"
   ```

### Step 2: Install the pgvector Extension
1. Download the release zip corresponding to your PostgreSQL version from [pgvector releases](https://github.com/pgvector/pgvector/releases).
2. Extract the files into your PostgreSQL installation folder (e.g., `C:\Program Files\PostgreSQL\17`):
   - Copy `vector.dll` into `C:\Program Files\PostgreSQL\17\lib\`
   - Copy `vector.control` and `vector--*.sql` into `C:\Program Files\PostgreSQL\17\share\extension\`
3. Verify installation files:
   ```powershell
   Test-Path "C:\Program Files\PostgreSQL\17\lib\vector.dll"
   Test-Path "C:\Program Files\PostgreSQL\17\share\extension\vector.control"
   ```

---

## 4. Environment Configuration

Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

Configure settings in `llm/.env`:
```ini
# PostgreSQL Shared Database Configuration
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/plc_simulator
DB_POOL_MIN_CONNS=2
DB_POOL_MAX_CONNS=10

# Embedding Configuration
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
EMBEDDING_DEVICE=cpu

# RAG Retrieval Configuration
RAG_SIMILARITY_THRESHOLD=0.35
RAG_TOP_K=4
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=150

# Local LLM Server (llama.cpp)
LLM_BASE_URL=http://127.0.0.1:8080
LLM_MODEL_NAME=ggml-org/Qwen3-1.7B-GGUF:Q4_K_M
LLM_ENABLE_THINKING=false
LLM_MAX_TOKENS=512
LLM_TEMPERATURE=0.1
LLM_TOP_P=0.9
LLM_CONNECT_TIMEOUT=5.0
LLM_GENERATION_TIMEOUT=120.0

# API Settings
API_HOST=127.0.0.1
API_PORT=8001
API_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000","http://localhost:5173","http://127.0.0.1:5173"]
```

---

## 5. Database Initialization

Execute the database initialization script to create the database, enable `pgvector`, and set up the schema:

```powershell
python scripts/init_db.py
```

### Schema Architecture
The migration executes `scripts/init_db.sql`:
1. `CREATE EXTENSION IF NOT EXISTS vector;`
2. `rag_documents`: Tracks indexed manuals, publication codes, page counts, SHA-256 source hashes, and indexing timestamps.
3. `rag_document_chunks`: Stores text chunks with exact starting and ending page references, SHA-256 chunk hashes, and a 384-dimensional vector column (`embedding vector(384)`).
4. `HNSW Index`: Creates `idx_rag_chunks_embedding_hnsw` using cosine distance (`vector_cosine_ops`) for sub-millisecond similarity search.

---

## 6. Knowledge Base Ingestion & Indexing

The knowledge base includes official industrial documentation:
- **Rockwell Automation**:
  - `1756-RM003-General-Instructions-Reference.pdf` (927 pages: arithmetic, timers, counters, comparisons, bit logic)
  - `1756-PM008-Ladder-Diagram.pdf` (24 pages: ladder logic programming reference)
  - `1756-PM001-Logix-5000-Controllers-Common-Procedures.pdf` (Catalog and procedures reference)
- **Siemens S7-1200**:
  - `s71200_system_manual_en-US.pdf` (Comprehensive S7-1200 system manual)
  - HTML Reference modules in `knowledge_base/siemens_s7_1200/` (bit logic, timers, counters, comparators, math, LAD)

### Step 1: Ingest & Extract Text with Page Markers
```powershell
python knowledge_base/ingest_pdf.py
```
*Extracts text page-by-page, inserting exact page markers (`===== PDF PAGE N =====`) and generating metadata JSON files.*

### Step 2: Validate Knowledge Base Integrity
```powershell
python scripts/check_knowledge_base.py
```
*Verifies PDF integrity, extraction completeness, and database connection readiness.*

### Step 3: Chunk, Embed, and Populate Vector Index
```powershell
python scripts/build_index.py
```
*Chunks documents with preserved PLC symbols, generates 384-dim normalized embeddings using `sentence-transformers`, and batch-upserts chunks into PostgreSQL.*

---

## 7. Starting the Services

### Option A: Automated Startup via Node Backend
If you start the Node backend (`npm run dev` in `backend-node`), its built-in `aiServiceManager.ts` will automatically launch `llama-server` on port 8080 and this FastAPI RAG service on port 8001!

### Option B: Manual Startup
Open two separate terminals:

**Terminal 1: Start `llama-server`**
```powershell
llama-server -hf ggml-org/Qwen3-1.7B-GGUF:Q4_K_M --host 127.0.0.1 --port 8080 -ngl 99 -c 2048
```

**Terminal 2: Start the FastAPI Service**
```powershell
# From the llm directory
python -m uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload
```

Interactive Swagger documentation is available at:  
👉 **http://127.0.0.1:8001/docs**

---

## 8. API Endpoint Specification

### 1. Health & Readiness (`GET /health`, `GET /healthz`)
Verifies connectivity to PostgreSQL and `llama-server`.

**Response:**
```json
{
  "status": "ok",
  "database": {
    "reachable": true,
    "target": "PostgreSQL 17.2",
    "pgvector_installed": true,
    "tables_initialized": true,
    "documents_count": 2,
    "chunks_count": 486
  },
  "llm": {
    "reachable": true,
    "status_code": 200,
    "base_url": "http://127.0.0.1:8080",
    "model_name": "ggml-org/Qwen3-1.7B-GGUF:Q4_K_M"
  },
  "version": "0.1.0"
}
```

### 2. Knowledge Base Status (`GET /knowledge-base/status`)
Reports document count, chunk count, and vector database status.

### 3. Semantic Retrieval (`POST /retrieve`)
Debug endpoint to inspect raw retrieved text passages and cosine similarity scores.

**Request:**
```json
{
  "query": "How does the TON timer On Delay instruction work?",
  "top_k": 3,
  "threshold": 0.35
}
```

### 4. Grounded Chat Assistant (`POST /chat`)
Generates grounded answers derived strictly from indexed documentation, with active simulator context.

**Request:**
```json
{
  "question": "Why is motor output Q0.0 not energizing?",
  "simulator_context": {
    "controller_model": "Siemens S7-1200",
    "routine_name": "Main [OB1]",
    "supported_instructions": ["NO Contact", "NC Contact", "Output Coil"],
    "extra_context": {
      "project": "Motor Control Project",
      "simulation_running": true,
      "input_bits": { "I0.0": false },
      "output_bits": { "Q0.0": false }
    }
  },
  "top_k": 4
}
```

**Response:**
```json
{
  "question": "Why is motor output Q0.0 not energizing?",
  "answer": "In Siemens S7-1200 ladder logic, a Normally Open (NO) contact requires its assigned address to be True (1) to establish power continuity. Because input address I0.0 is currently 0 (False), the contact does not conduct, preventing power from reaching Output Coil Q0.0.",
  "citations": [
    {
      "document_title": "SIMATIC S7-1200 System Manual",
      "publication_number": "s71200_system_manual",
      "page_number": 242,
      "end_page_number": 243,
      "citation_str": "[s71200_system_manual pp. 242-243]"
    }
  ],
  "latency_seconds": 1.25,
  "tokens_per_second": 52.4,
  "metrics_source": "calculated"
}
```

---

## 9. Running Tests

The test suite covers:
- API endpoint validation, serialization, and error handling (`tests/test_api.py`)
- Ladder syntax preservation and text cleaning (`tests/test_chunking.py`)
- PDF ingestion and page boundary tagging (`tests/test_ingestion.py`)
- RAG pipeline retrieval, grounding refusal, and citation formatting (`tests/test_rag_pipeline.py`)
- PostgreSQL vector store operations, pooling, and cosine querying (`tests/test_vector_store.py`)
- Configuration and model client unit tests (`tests/test_model_config.py`, `tests/test_llama_cpp_client.py`)

Run tests with pytest:
```powershell
pytest tests
```
*All 53 unit tests run with mocked database and LLM fixtures, enabling 100% offline testing without active background services.*

---

## 10. Performance Benchmarking

Evaluate raw inference throughput on your local GPU or CPU:
```powershell
# Standard 3-run benchmark
python benchmark_model.py --runs 3

# Streaming benchmark (measures Time-To-First-Token)
python benchmark_model.py --runs 3 --stream

# Non-thinking mode benchmark
python benchmark_model.py --runs 3 --no-thinking
```

---

## 11. Directory Layout

```
llm/
├── api/
│   ├── dependencies.py          # FastAPI dependency injection singletons
│   ├── main.py                  # API routes & middleware
│   └── schemas.py               # Pydantic request/response schemas
├── knowledge_base/
│   ├── Sources/                 # Authoritative Rockwell & Siemens PDFs
│   ├── extracted/               # Page-tagged plain text extracts
│   ├── metadata/                # Document metadata JSON files
│   ├── siemens_s7_1200/         # Siemens HTML instruction modules
│   └── ingest_pdf.py            # PDF text extraction script
├── llm/
│   ├── llama_cpp_client.py      # HTTP client for llama-server / OpenAI API
│   └── model_config.py          # LLM configuration dataclass
├── rag/
│   ├── chunker.py               # Ladder-syntax aware text chunker
│   ├── cleaning.py              # Text cleaning & mnemonic normalization
│   ├── config.py                # RAG configuration settings
│   ├── embeddings.py            # SentenceTransformer embeddings engine
│   ├── pipeline.py              # Retrieval & grounding pipeline
│   ├── retriever.py             # Vector similarity retriever
│   └── vector_store.py          # PostgreSQL pgvector repository
├── scripts/
│   ├── build_index.py           # Chunking, embedding & vector upsert script
│   ├── check_knowledge_base.py  # Knowledge base diagnostic check
│   ├── init_db.py               # Database initialization script
│   └── init_db.sql              # Schema & HNSW index migration script
├── tests/                       # 53 offline unit tests
├── benchmark_model.py           # LLM performance benchmarking script
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment configuration template
```

---

## 12. Troubleshooting & Diagnostics

### 1. `PostgreSQL password authentication failed for user "postgres"`
- **Fix**: Update the password in `llm/.env`:
  ```ini
  DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/plc_simulator
  ```

### 2. `Extension "vector" is not available`
- **Fix**: Ensure `vector.dll` exists in `C:\Program Files\PostgreSQL\<version>\lib` and `vector.control` exists in `C:\Program Files\PostgreSQL\<version>\share\extension`. Restart the PostgreSQL Windows Service.

### 3. `Could not connect to llama.cpp server at http://127.0.0.1:8080`
- **Fix**: Launch `llama-server` in a separate terminal:
  ```powershell
  llama-server -hf ggml-org/Qwen3-1.7B-GGUF:Q4_K_M --host 127.0.0.1 --port 8080 -ngl 99 -c 2048
  ```

### 4. `Health check returned HTTP 503 (loading)`
- **Fix**: The model GGUF weights are currently loading into memory. Wait until the console logs `HTTP server listening`.