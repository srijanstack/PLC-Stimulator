import 'dotenv/config'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))

const list = (value: string) =>
  value
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)

export const config = {
  port: Number(process.env.PORT ?? 8000),
  host: process.env.HOST ?? '127.0.0.1',
  corsOrigins: list(
    process.env.CORS_ORIGINS ?? 'http://127.0.0.1:5173,http://localhost:5173'
  ),
  /** Only used to import an old state.json into PostgreSQL the first time. */
  dataDir: process.env.DATA_DIR ?? path.resolve(here, '..', 'data'),
  /** PostgreSQL connection string. Change the default for your own setup (or set it in .env). */
  databaseUrl:
    process.env.DATABASE_URL ?? 'postgres://postgres:postgres@127.0.0.1:5432/plc_studio',
  llm: {
    baseUrl: process.env.LLM_BASE_URL ?? 'http://127.0.0.1:11434/v1',
    model: process.env.LLM_MODEL ?? 'qwen2.5:7b-instruct',
    apiKey: process.env.LLM_API_KEY ?? '',
    timeoutMs: Number(process.env.LLM_TIMEOUT_MS ?? 120000),
    temperature: Number(process.env.LLM_TEMPERATURE ?? 0.2)
  }
}