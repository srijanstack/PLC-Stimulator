# PLC Studio Backend (Node.js + TypeScript)

The core backend service for **PLC Studio**, built with **Node.js (>=20)**, **Express 5**, and **TypeScript**.

It provides REST API services for ladder project persistence, industrial instruction catalogs, deterministic ladder syntax and wiring validation, and local AI process supervision with an OpenAI-compatible assistant proxy.

---

## 1. Responsibilities & Architecture

```text
               +----------------------------------+
               |     PLC Studio Frontend (Vite)   |
               +-----------------+----------------+
                                 |
                          REST API (Port 8000)
                                 v
+-------------------------------------------------------------------+
|                     Node.js Express 5 Backend                     |
|                                                                   |
|  [ /api/health ]    [ /api/archive ]    [ /api/state ]            |
|         |                   |                  |                  |
|         v                   v                  v                  |
|   Database Ping     Catalog Definition   PostgreSQL StateStore    |
|   (PostgreSQL)      (Bits, Timers...)    (JSONB Project Canvas)   |
|                                                                   |
|  [ /api/agent/chat ]                                              |
|         |                                                         |
|         +--> 1. Deterministic Wiring Checks (wiring.ts)           |
|         +--> 2. Untrusted State Sanitization                      |
|         +--> 3. Grounded Prompt Formulation (prompt.ts)           |
|         +--> 4. Forward to Local LLM (Ollama / llama-server)       |
+-------------------------------------------------------------------+
        |                                        |
        v (aiServiceManager.ts)                  v
+-------------------------------+      +----------------------------+
|   Local llama.cpp Server      |      |   PostgreSQL Database      |
|   (Port 8080 - GPU/CUDA)      |      |   (Port 5432 - plc_studio) |
+-------------------------------+      +----------------------------+
```

### Core Capabilities
1. **Project Persistence (`stateStore.ts`)**: Saves the active project name, multi-network ladder definitions, and virtual hardware breadboard layouts into a dedicated PostgreSQL table (`projects`) with JSONB fields. Automatically migrates legacy file-based `state.json` on startup.
2. **Instruction Catalog & Taxonomy (`catalog.ts`)**: Serves standard industrial ladder logic instructions organized into hierarchical categories (Bits, Timers, Counters, Comparators, Math, Function Blocks).
3. **Ladder Syntax & Address Validation (`validate.ts`)**: Validates rung ordering and enforce strict PLC rules:
   - Input contacts (`contact_no`, `contact_nc`) must precede output coils.
   - Restricts digital addresses to valid boundaries (`I0.0–I0.7` for inputs, `Q0.0–Q0.7` for outputs).
4. **Deterministic Hardware-Ladder Wiring Verification (`agent/wiring.ts`)**: High-speed deterministic algorithm that cross-checks the virtual hardware board against the ladder program. Identifies:
   - Unwired hardware components.
   - Ladder contacts referencing input addresses with no physical switch or sensor on the board.
   - Ladder coils driving outputs with no connected pilot lights, relays, or motors.
   - Rungs missing output coils.
   *These issues are provided to the LLM as factual grounding constraints.*
5. **AI Service Supervisor (`aiServiceManager.ts`)**: Automatically checks the health of `llama-server` (Port 8080) and the FastAPI RAG service (Port 8001). If not running, launches them with GPU acceleration (NVIDIA CUDA) or CPU fallback and awaits readiness.
6. **Robust AI Chat Proxy (`agent/router.ts`, `agent/llm.ts`)**: Accepts chat prompts, sanitizes user tags and project descriptions, formats the context snapshot, and talks to any OpenAI-compatible server. Returns human-readable error messages if the model is offline.

---

## 2. Directory Structure

```
backend-node/
├── package.json                 # Project dependencies & scripts
├── tsconfig.json                # TypeScript compiler configuration
├── tsconfig.build.json          # Production build configuration
├── .env.example                 # Template for environment settings
├── src/
│   ├── server.ts                # Server entrypoint (launches AI services & Express)
│   ├── app.ts                   # Express application setup, routes, error handlers
│   ├── config.ts                # Environment configuration loader
│   ├── catalog.ts               # Instruction definitions & catalog taxonomy
│   ├── validate.ts              # Ladder validation rules & HttpError class
│   ├── stateStore.ts            # PostgreSQL persistence & legacy migration
│   ├── aiServiceManager.ts      # Process manager for local llama-server & FastAPI RAG
│   └── agent/
│       ├── router.ts            # POST /api/agent/chat endpoint
│       ├── llm.ts               # LlmClient interface & OpenAI HTTP client
│       ├── prompt.ts            # System prompt assembler & context formatter
│       ├── schemas.ts           # Zod validation schemas for agent requests
│       └── wiring.ts            # Deterministic ladder vs. hardware analyzer
└── test/
    ├── api.test.ts              # REST API route integration tests
    ├── agent.test.ts            # Agent prompt & wiring analysis unit tests
    └── helpers.ts               # Test mocks and fixtures
```

---

## 3. Getting Started

### Prerequisites
- **Node.js**: version `20.0.0` or higher
- **PostgreSQL**: version 16 or 17 running on port `5432`

### Installation
Open a terminal in the `backend-node` directory:

```powershell
cd backend-node
npm install
```

### Environment Configuration
Copy `.env.example` to create your local `.env`:

```powershell
Copy-Item .env.example .env
```

Ensure the configuration matches your local environment (see table below).

### Running in Development Mode
```powershell
npm run dev
```

The backend server starts on:  
👉 **http://127.0.0.1:8000**

Health check endpoint:  
👉 **http://127.0.0.1:8000/api/health**

### Running Tests & Typechecks
```powershell
# Run the test suite (Vitest)
npm test

# Run TypeScript compiler verification
npm run typecheck

# Build compiled JavaScript
npm run build
```

---

## 4. Configuration Reference

All settings can be configured via environment variables in `backend-node/.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port for the Express server. |
| `HOST` | `127.0.0.1` | Host interface to bind to. |
| `CORS_ORIGINS` | `http://127.0.0.1:5173,http://localhost:5173` | Allowed CORS origins for the frontend. |
| `DATABASE_URL` | `postgres://postgres:postgres@127.0.0.1:5432/plc_studio` | PostgreSQL connection string for project persistence. |
| `DATA_DIR` | `../data` | Directory checked for legacy `state.json` file to migrate. |
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | OpenAI-compatible endpoint (Ollama, LM Studio, or llama-server). |
| `LLM_MODEL` | `qwen2.5:7b-instruct` | Name of the language model to invoke. |
| `LLM_API_KEY` | *(empty)* | Optional API key if using a hosted provider. |
| `LLM_TIMEOUT_MS` | `120000` | Maximum time in ms to wait for LLM completion (2 minutes). |
| `LLM_TEMPERATURE` | `0.2` | Generation temperature (lower values ensure precise factual answers). |

---

## 5. API Reference

### Health & Connectivity
- **`GET /api/health`**  
  Returns service liveness and checks PostgreSQL database connectivity.  
  **Response:**
  ```json
  {
    "status": "ok",
    "service": "plc-archive-backend",
    "database": true
  }
  ```

### Instruction Catalog
- **`GET /api/archive`**  
  Returns the complete hierarchical instruction catalog and folder taxonomy.

### Project State Persistence
- **`GET /api/state`**  
  Retrieves the saved project state (project name, ladder instructions/networks, hardware parts).
- **`PUT /api/state`**  
  Validates and updates the saved project state in PostgreSQL.  
  **Request Body:**
  ```json
  {
    "project_name": "Conveyor Belt Automation",
    "instructions": [
      { "instanceId": "n1", "instructionId": "contact_no", "address": "I0.0", "name": "Start_PB" },
      { "instanceId": "n2", "instructionId": "coil_output", "address": "Q0.0", "name": "Motor_Run" }
    ],
    "hardware": [
      { "id": "h1", "type": "push_no", "address": "I0.0", "label": "Start_PB", "x": 100, "y": 80 },
      { "id": "h2", "type": "motor", "address": "Q0.0", "label": "Motor_Run", "x": 300, "y": 80 }
    ]
  }
  ```

### AI Engineering Assistant
- **`POST /api/agent/chat`**  
  Generates context-aware diagnostic replies.  
  **Request Body:**
  ```json
  {
    "message": "Why does the motor not start when I press the pushbutton?",
    "history": [],
    "context": {
      "project": "Conveyor Belt Automation",
      "running": true,
      "ladder": [
        { "instructionId": "contact_no", "address": "I0.0", "name": "Start_PB", "kind": "contact" },
        { "instructionId": "coil_output", "address": "Q0.0", "name": "Motor_Run", "kind": "coil" }
      ],
      "hardware": [
        { "label": "Start_PB", "type": "push_no", "kind": "input", "address": "I0.0", "signal": false }
      ],
      "inputs": { "I0.0": false },
      "outputs": { "Q0.0": false }
    }
  }
  ```
  **Response:**
  ```json
  {
    "reply": "Your ladder rung requires input address I0.0 to evaluate to True. Because the Pushbutton (NO) is currently released, I0.0 is False, breaking rung continuity before reaching coil Q0.0."
  }
  ```

---

## 6. Local LLM Options

The backend can connect to any OpenAI-compatible inference engine:

1. **Ollama (Easiest)**:
   - Install from [ollama.com](https://ollama.com).
   - Pull a model: `ollama pull qwen2.5:7b-instruct` (or `qwen2.5:3b-instruct` for smaller GPUs).
   - Leave `LLM_BASE_URL=http://127.0.0.1:11434/v1` and set `LLM_MODEL=qwen2.5:7b-instruct`.
2. **Built-in `llama-server` (High Performance)**:
   - Automatically supervised by [`src/aiServiceManager.ts`](file:///c:/Users/rawat/Desktop/PLC-Stimulator/backend-node/src/aiServiceManager.ts).
   - Offloads model layers directly to NVIDIA GPU via CUDA.
3. **LM Studio / vLLM / Hosted APIs**:
   - Set `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` accordingly in `.env`.
