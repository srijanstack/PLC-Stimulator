# PLC Studio: Industrial Ladder Simulator & AI Assistant

A modern, local-first industrial automation suite combining a web-based **Ladder Logic Editor**, an **Interactive Hardware Breadboard Simulator**, a **Real-Time 50ms PLC Scan Engine**, and an **Offline-First Retrieval-Augmented Generation (RAG) AI Assistant** grounded in authoritative Rockwell Automation and Siemens technical manuals.

---

## 1. System Architecture

The project is structured into three decoupled, complementary components:

```text
                                  +------------------------------------------+
                                  |         PLC Studio Web Frontend          |
                                  |         (React 19 + TypeScript)          |
                                  |               Port: 5173                 |
                                  +--------------------+---------------------+
                                                       |
                         +-----------------------------+-----------------------------+
                         | State & Catalog (Port 8000)                               | Direct RAG Chat (Port 8001)
                         v                                                           v
+--------------------------------------------------+       +--------------------------------------------------+
|           PLC Studio Node.js Backend             |       |            Python FastAPI RAG Service            |
|         (Node.js 20+ Express 5 / TS)             |       |           (PyTorch / sentence-transformers)      |
|                  Port: 8000                      |       |                   Port: 8001                     |
|                                                  |       |                                                  |
|  - PostgreSQL State Persistence (JSONB)          |       |  - Authoritative Rockwell & Siemens Manuals      |
|  - Ladder Syntax & Address Validation            |       |  - Semantic Search (HNSW Cosine Similarity)      |
|  - Deterministic Hardware-vs-Ladder Checker      |       |  - Grounded Context & Citation Injection         |
|  - AI Process Supervisor (aiServiceManager.ts)   |       |  - Refusal when evidence is insufficient         |
+------------------------+-------------------------+       +------------------------+-------------------------+
                         |                                                          |
                         | (Project State)                                          | (384-d Vector Search)
                         v                                                          v
+-------------------------------------------------------------------------------------------------------------+
|                                             PostgreSQL Database                                             |
|                                        (Port: 5432 / pgvector extension)                                    |
|                                                                                                             |
|  - Database "plc_studio":    projects (JSONB ladder networks & hardware layout)                             |
|  - Database "plc_simulator": rag_documents & rag_document_chunks (HNSW vector index)                        |
+-------------------------------------------------------------------------------------------------------------+
                                                                                            ^
                                                                                            | Prompt + Chunks
                                                                                            v
                                                                   +------------------------------------------+
                                                                   |       Local Inference (llama.cpp)        |
                                                                   |      (Qwen3-1.7B-GGUF / CUDA GPU)        |
                                                                   |               Port: 8080                 |
                                                                   +------------------------------------------+
```

---

## 2. Component Directory & Documentation

Each component resides in its own folder with dedicated documentation:

| Component | Path | Technology | Detailed Docs |
| :--- | :--- | :--- | :--- |
| **Frontend** | [`frontend/`](file:///c:/Users/rawat/Desktop/PLC-Stimulator/frontend/) | React 19, Vite, TypeScript, Lucide Icons | [**Frontend README**](file:///c:/Users/rawat/Desktop/PLC-Stimulator/frontend/README.md) |
| **Backend** | [`backend-node/`](file:///c:/Users/rawat/Desktop/PLC-Stimulator/backend-node/) | Node.js 20+, Express 5, TypeScript, PostgreSQL | [**Backend README**](file:///c:/Users/rawat/Desktop/PLC-Stimulator/backend-node/README.md) |
| **AI / RAG** | [`llm/`](file:///c:/Users/rawat/Desktop/PLC-Stimulator/llm/) | Python 3.10+, FastAPI, PyTorch, pgvector, llama.cpp | [**LLM & RAG README**](file:///c:/Users/rawat/Desktop/PLC-Stimulator/llm/README.md) |

### Component Summaries

### 💻 1. [Frontend (Web UI & Simulation Engine)](file:///c:/Users/rawat/Desktop/PLC-Stimulator/frontend/README.md)
- **Ladder Logic Canvas**: Multi-network ladder editor with visual power rails, rung collapsing, and drag-and-drop instruction insertion.
- **Instruction Support**: Normally Open Contact (`--| |--`), Normally Closed Contact (`--|/|--`), Output Coil (`--( )--`), Set Bit (`--(S)--`), and Reset Bit (`--(R)--`).
- **Interactive Hardware Breadboard**: Virtual PLC chassis with terminal strips (`I0.0–I0.7` inputs, `Q0.0–Q0.7` outputs), momentary pushbuttons (NO/NC), latching toggle switches, E-Stops, limit switches, multi-color pilot lights, relays, motors, and buzzers.
- **Real-Time 50ms Scan Engine**: Cycles through input sampling, top-to-bottom network evaluation with immediate inter-network memory propagation, output latching, and power-flow rendering.
- **Embedded AI Chat Panel**: Inspects live rungs, hardware wiring, and I/O image tables to answer questions with cited manual references.

### ⚙️ 2. [Backend (Node.js & TypeScript API)](file:///c:/Users/rawat/Desktop/PLC-Stimulator/backend-node/README.md)
- **Project Persistence**: Stores projects in PostgreSQL (`projects` table with JSONB fields) and automatically migrates legacy `state.json` files.
- **Catalog & Rule Enforcement**: Serves instruction taxonomy and enforces contact-before-coil ordering and address boundary limits.
- **Deterministic Wiring Analyzer**: Pre-computes discrepancies between ladder rungs and physical hardware (e.g. unassigned terminals, missing coils, orphaned switches) and feeds them to the LLM as verified facts.
- **AI Process Supervisor**: Automatically discovers and launches `llama-server` and the Python FastAPI RAG service on startup.

### 🧠 3. [LLM & RAG Assistant (Python & Local AI)](file:///c:/Users/rawat/Desktop/PLC-Stimulator/llm/README.md)
- **Dual Knowledge Base**: Indexed official manuals for Rockwell Automation (Logix 5000 manuals `1756-RM003`, `1756-PM008`, `1756-PM001`) and Siemens S7-1200 system manuals.
- **Syntax-Preserving Vector Index**: Chunks manuals with page-boundary attribution (`===== PDF PAGE N =====`), generates 384-d normalized embeddings (`all-MiniLM-L6-v2`), and indexes them via PostgreSQL `pgvector` HNSW cosine similarity.
- **Grounded Chat Completion**: Formats prompts with active simulator context (routine, instructions, tags, bit states) and strictly derives answers with exact page citations.
- **Zero Cloud Dependencies**: Runs entirely offline on local hardware via `llama-server` (CUDA GPU or CPU).

---

## 3. Port & Service Matrix

| Service | Port | Protocol | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | `5173` | HTTP | Vite web development server |
| **Node.js Backend** | `8000` | HTTP | Express REST API (`/api/state`, `/api/archive`, `/api/health`) |
| **FastAPI RAG API** | `8001` | HTTP | Grounded retrieval and RAG chat (`/chat`, `/retrieve`, `/healthz`) |
| **llama-server** | `8080` | HTTP | Local OpenAI-compatible GGUF inference engine |
| **PostgreSQL** | `5432` | TCP | Relational state storage & `pgvector` similarity search |

---

## 4. Quickstart Guide

### Prerequisites
- **Node.js 20+** and **npm**
- **Python 3.10+** (with virtual environment capability)
- **PostgreSQL 16 or 17** with the **`pgvector`** extension installed
- *(Optional for AI)* NVIDIA GPU with CUDA for accelerated local LLM inference

---

### Step 1: Initialize Database & Vector Store
1. Open PowerShell and navigate to `llm`:
   ```powershell
   cd llm
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   Copy-Item .env.example .env     # Update your PostgreSQL password in .env
   python scripts/init_db.py       # Initializes database & pgvector tables
   python scripts/build_index.py   # Chunks and embeds manuals into PostgreSQL
   ```

---

### Step 2: Start the Backend & AI Supervisor
1. Open a terminal in `backend-node`:
   ```powershell
   cd backend-node
   npm install
   Copy-Item .env.example .env
   npm run dev
   ```
2. The Node backend starts on `http://127.0.0.1:8000`.  
   *(If configured, `aiServiceManager.ts` will automatically verify and spin up `llama-server` and the FastAPI RAG service).*

---

### Step 3: Start the Frontend Workbench
1. Open a terminal in `frontend`:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
2. Open your browser and navigate to:  
   👉 **http://127.0.0.1:5173**

---

## 5. End-to-End Simulation Workflow

```text
  1. Design Logic            2. Wire Hardware           3. Execute Cycle           4. Diagnose with AI
+------------------+       +------------------+       +------------------+       +-------------------+
| Place NO Contact |       | Place Pushbutton |       | Click "Run"      |       | Click "AI Agent"  |
| Add Output Coil  | ----> | Place Motor      | ----> | 50ms Scan Loop   | ----> | Ask: "Why is      |
| Set Addresses    |       | Wire to Terminals|       | Press Pushbutton |       | motor stopped?"   |
| (I0.0 -> Q0.0)   |       | (I0.0 -> Q0.0)   |       | Power Flow Lights|       | Cited Diagnostics |
+------------------+       +------------------+       +------------------+       +-------------------+
```

1. **Build a Ladder Rung**: From the Instruction catalog, insert a **Normally Open Contact** (`contact_no`) addressed to `I0.0` and an **Output Coil** (`coil_output`) addressed to `Q0.0`.
2. **Setup the Breadboard**: On the Hardware Canvas, place a **Pushbutton (NO)** assigned to terminal `I0.0` and an **AC Motor** assigned to `Q0.0`.
3. **Run the PLC**: Click **Run** on the top toolbar.
4. **Trigger Physical Inputs**: Click and hold the pushbutton. The `I0.0` LED illuminates on the PLC module, power flows across the rung, and the AC motor activates.
5. **Get AI Help**: Open the AI Agent panel to ask questions, verify address connections, or consult manual references on PLC execution rules.
