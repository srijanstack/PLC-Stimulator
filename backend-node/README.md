# PLC Studio backend (Node + TypeScript)

Replaces the FastAPI backend. Same routes, same port (8000), so the frontend needs no URL change.

## Run it (Windows PowerShell)

Needs Node.js 20+.

```powershell
cd backend-node
npm install
copy .env.example .env      # optional: edit model / URL
npm run dev
```

Check: http://127.0.0.1:8000/api/health

Tests: `npm test`  ·  Type-check: `npm run typecheck`

## Your own LLM (Ollama, free, runs on your PC)

1. Install Ollama from https://ollama.com
2. Download a model once:  `ollama pull qwen2.5:7b-instruct`  (about 5 GB; use a smaller one such as `qwen2.5:3b-instruct` on a weak PC)
3. Ollama serves an OpenAI-compatible API at `http://127.0.0.1:11434/v1` automatically.
4. Make sure `LLM_MODEL` in `.env` matches the model you pulled.

The first question after starting is slow while the model loads into memory.
Any other OpenAI-compatible server works too (LM Studio, vLLM, llama.cpp server, a hosted API): just change `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`.

If the model server is not running, the chat window shows a readable message instead of failing.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | liveness |
| GET | `/api/archive` | instruction catalog |
| GET / PUT | `/api/state` | project (ladder + hardware board), saved to `data/state.json` |
| POST | `/api/agent/chat` | `{ message, history?, context }` → `{ reply }` |

## Layout

```
src/
  server.ts        starts the server
  app.ts           routes + error handling (createApp)
  config.ts        environment settings
  catalog.ts       instruction catalog
  validate.ts      ladder rules (same as the Python version)
  stateStore.ts    JSON-file storage (swap for Postgres later)
  agent/
    router.ts      POST /api/agent/chat
    llm.ts         LlmClient interface + OpenAI-compatible HTTP client
    prompt.ts      system prompt + project snapshot
    wiring.ts      ladder-vs-hardware checks given to the model as facts
    schemas.ts     request validation (zod)
test/              vitest + supertest
```

## Notes

- Set Bit / Reset Bit are now marked `implemented: true` in the catalog because the frontend scan engine runs them.
- The agent is chat-only for now: it explains and diagnoses, it cannot edit the project.
- Project text (tag names, labels) is treated as untrusted data in the prompt.
