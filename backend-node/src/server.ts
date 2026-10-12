import { createApp } from './app.js'
import { OpenAiCompatibleClient } from './agent/llm.js'
import { config } from './config.js'
import { startAIServices } from './aiServiceManager.js'
async function main(): Promise<void> {
  console.log('[Startup] Preparing AI services...')
  await startAIServices()
  const app = createApp({
    llm: new OpenAiCompatibleClient(config.llm),
    dataDir: config.dataDir,
    corsOrigins: config.corsOrigins
  })
  app.listen(config.port, config.host, () => {
    console.log(`PLC Studio backend: http://${config.host}:${config.port}`)
    console.log(`Health check:       http://${config.host}:${config.port}/api/health`)
    console.log(`LLM:                ${config.llm.model} @ ${config.llm.baseUrl}`)
  })
}
main().catch(error => {
  console.error('[Startup] Could not start the backend and AI services:', error)
  process.exitCode = 1
})
