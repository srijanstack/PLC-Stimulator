import fs from 'node:fs'
import path from 'node:path'
import pg from 'pg'
import { z } from 'zod'
import { HttpError } from './validate.js'

export const projectStateSchema = z.object({
  project_name: z.string().max(120).default('Motor Control Project'),
  instructions: z.array(z.record(z.string(), z.unknown())).default([]),
  /** Parts on the hardware board (see frontend HwComponent). */
  hardware: z.array(z.record(z.string(), z.unknown())).default([])
})

export type ProjectState = z.infer<typeof projectStateSchema>

export const defaultState = (): ProjectState => ({
  project_name: 'Motor Control Project',
  instructions: [],
  hardware: []
})

/** There is one project for now. A later "many projects" feature only needs a different id. */
const PROJECT_ID = 'default'

/**
 * The ladder and the hardware board change shape often, so they are stored as
 * JSONB. Everything else gets a real column.
 */
const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS projects (
  id           TEXT PRIMARY KEY,
  project_name TEXT        NOT NULL,
  instructions JSONB       NOT NULL DEFAULT '[]'::jsonb,
  hardware     JSONB       NOT NULL DEFAULT '[]'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
)`

/** Saves the project (ladder + hardware canvas) in PostgreSQL. */
export class StateStore {
  private readonly pool: pg.Pool
  private readonly legacyFile: string | null
  private initPromise: Promise<void> | null = null

  /**
   * @param databaseUrl  e.g. postgres://user:password@127.0.0.1:5432/plc_studio
   * @param legacyDir    optional folder holding an old state.json to import once
   */
  constructor(databaseUrl: string, legacyDir?: string) {
    this.pool = new pg.Pool({ connectionString: databaseUrl, max: 5 })
    // An idle client dropping must not crash the whole server.
    this.pool.on('error', err => console.error('[db] idle client error:', err.message))
    this.legacyFile = legacyDir ? path.join(legacyDir, 'state.json') : null
  }

  /** Creates the table on first use (and retries on the next request if the DB was down). */
  private ready(): Promise<void> {
    if (!this.initPromise) {
      this.initPromise = this.init().catch(err => {
        this.initPromise = null
        throw err
      })
    }
    return this.initPromise
  }

  private async init(): Promise<void> {
    await this.pool.query(SCHEMA_SQL)

    // One-time import of the old file-based save, if there is one and the DB is still empty.
    const existing = await this.pool.query('SELECT 1 FROM projects WHERE id = $1', [PROJECT_ID])
    if (existing.rowCount === 0 && this.legacyFile && fs.existsSync(this.legacyFile)) {
      try {
        const raw: unknown = JSON.parse(fs.readFileSync(this.legacyFile, 'utf-8'))
        const parsed = projectStateSchema.safeParse(raw)
        if (parsed.success) {
          await this.upsert(parsed.data, true)
          console.log('[db] imported existing state.json into PostgreSQL')
        }
      } catch (err) {
        console.warn('[db] could not import state.json:', (err as Error).message)
      }
    }
  }

  private async upsert(state: ProjectState, onlyIfMissing = false): Promise<void> {
    // pg turns JS arrays into Postgres arrays, so JSON columns must be sent as JSON text.
    await this.pool.query(
      `INSERT INTO projects (id, project_name, instructions, hardware)
       VALUES ($1, $2, $3::jsonb, $4::jsonb)
       ON CONFLICT (id) DO ${
         onlyIfMissing
           ? 'NOTHING'
           : `UPDATE SET project_name = EXCLUDED.project_name,
                         instructions = EXCLUDED.instructions,
                         hardware     = EXCLUDED.hardware,
                         updated_at   = now()`
       }`,
      [
        PROJECT_ID,
        state.project_name,
        JSON.stringify(state.instructions),
        JSON.stringify(state.hardware)
      ]
    )
  }

  async read(): Promise<ProjectState> {
    try {
      await this.ready()
      const { rows } = await this.pool.query(
        'SELECT project_name, instructions, hardware FROM projects WHERE id = $1',
        [PROJECT_ID]
      )
      if (rows.length === 0) {
        const value = defaultState()
        await this.upsert(value)
        return value
      }
      const parsed = projectStateSchema.safeParse(rows[0])
      return parsed.success ? parsed.data : defaultState()
    } catch (err) {
      throw this.unavailable(err)
    }
  }

  async write(state: ProjectState): Promise<void> {
    try {
      await this.ready()
      await this.upsert(state)
    } catch (err) {
      throw this.unavailable(err)
    }
  }

  /** Cheap connectivity check for /api/health. */
  async ping(): Promise<boolean> {
    try {
      await this.pool.query('SELECT 1')
      return true
    } catch {
      return false
    }
  }

  async close(): Promise<void> {
    await this.pool.end()
  }

  private unavailable(err: unknown): HttpError {
    if (err instanceof HttpError) return err
    console.error('[db]', err)
    return new HttpError(503, 'Database unavailable. Check DATABASE_URL and that PostgreSQL is running.')
  }
}