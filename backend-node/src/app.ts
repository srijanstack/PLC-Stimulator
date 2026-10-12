import cors from 'cors'
import express from 'express'
import type { ErrorRequestHandler, Request, RequestHandler, Response } from 'express'
import { FOLDERS, INSTRUCTIONS } from './catalog.js'
import { agentRouter } from './agent/router.js'
import type { LlmClient } from './agent/llm.js'
import { config } from './config.js'
import { StateStore, projectStateSchema } from './stateStore.js'
import { HttpError, validateLadder } from './validate.js'

export type AppDeps = {
  llm: LlmClient
  dataDir: string
  corsOrigins: string[]
  /** Optional: tests can pass their own store. By default one is built from DATABASE_URL. */
  store?: StateStore
}

/** Express 4 does not catch rejected promises, so forward them to the error handler. */
const asyncHandler =
  (fn: (req: Request, res: Response) => Promise<void>): RequestHandler =>
  (req, res, next) => {
    fn(req, res).catch(next)
  }

export function createApp({ llm, dataDir, corsOrigins, store: givenStore }: AppDeps) {
  const app = express()
  // dataDir is only used to import an old state.json into PostgreSQL once.
  const store = givenStore ?? new StateStore(config.databaseUrl, dataDir)

  app.use(cors({ origin: corsOrigins }))
  app.use(express.json({ limit: '1mb' }))

  const api = express.Router()

  api.get(
    '/health',
    asyncHandler(async (_req, res) => {
      const database = await store.ping()
      res.json({ status: database ? 'ok' : 'degraded', service: 'plc-archive-backend', database })
    })
  )

  api.get('/archive', (_req, res) => {
    res.json({ folders: FOLDERS, instructions: INSTRUCTIONS })
  })

  api.get(
    '/state',
    asyncHandler(async (_req, res) => {
      res.json(await store.read())
    })
  )

  api.put(
    '/state',
    asyncHandler(async (req, res) => {
      const parsed = projectStateSchema.safeParse(req.body)
      if (!parsed.success) {
        const detail = parsed.error.issues
          .map(i => `${i.path.join('.') || 'body'}: ${i.message}`)
          .join('; ')
        throw new HttpError(422, detail)
      }
      const state = parsed.data
      if (!state.project_name.trim()) {
        throw new HttpError(422, 'Project name cannot be blank.')
      }
      validateLadder(state.instructions)
      await store.write(state)
      res.json({ status: 'saved', ...state })
    })
  )

  api.use('/agent', agentRouter(llm))

  app.use('/api', api)

  const onError: ErrorRequestHandler = (err, _req, res, _next) => {
    if (err instanceof HttpError) {
      res.status(err.status).json({ detail: err.message })
      return
    }
    if (err && typeof err === 'object' && (err as { type?: string }).type === 'entity.parse.failed') {
      res.status(400).json({ detail: 'Request body is not valid JSON.' })
      return
    }
    console.error(err)
    res.status(500).json({ detail: 'Internal server error.' })
  }
  app.use(onError)

  return app
}