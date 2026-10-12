import { spawn, type ChildProcess } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
const root = process.env.PLC_AI_ROOT ?? 'D:\\Projects\\PLC-Stimulator\\LLM'
const host = '127.0.0.1'
const llamaPort = 8080
const ragPort = 8001
const modelPath = path.join(
  process.env.USERPROFILE ?? '',
  '.cache', 'huggingface', 'hub',
  'models--ggml-org--Qwen3-1.7B-GGUF',
  'snapshots', 'daeb8e2d528a760970442092f6bf1e55c3b659eb',
  'Qwen3-1.7B-Q4_K_M.gguf'
)
const ollamaLibDir = path.join(
  process.env.LOCALAPPDATA ?? '',
  'Programs', 'Ollama', 'lib', 'ollama'
)
const llamaExe = path.join(ollamaLibDir, 'llama-server.exe')
const cudaDir = path.join(ollamaLibDir, 'cuda_v12')
const cudaDll = path.join(cudaDir, 'ggml-cuda.dll')
const pythonExe = path.join(root, '.venv', 'Scripts', 'python.exe')
const children: ChildProcess[] = []
async function isHealthy(url: string): Promise<boolean> {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(1500) })
    return response.ok
  } catch {
    return false
  }
}
function launch(
  executable: string,
  args: string[],
  cwd: string,
  label: string,
  extraEnv?: Record<string, string>
): ChildProcess {
  const child = spawn(executable, args, {
    cwd,
    env: extraEnv ? { ...process.env, ...extraEnv } : process.env,
    windowsHide: true,
    stdio: 'inherit'
  })
  child.on('error', error => {
    console.error(`[AI services] ${label} failed to launch:`, error.message)
  })
  child.on('exit', (code, signal) => {
    console.log(`[AI services] ${label} exited (code=${code}, signal=${signal})`)
  })
  children.push(child)
  return child
}
async function waitForHealth(
  url: string,
  child: ChildProcess,
  label: string,
  timeoutMs: number
): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await isHealthy(url)) {
      console.log(`[AI services] ${label} is ready at ${url}`)
      return
    }
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new Error(`${label} exited before becoming healthy. Check its startup output.`)
    }
    await new Promise(resolve => setTimeout(resolve, 1000))
  }
  throw new Error(`${label} did not become healthy within ${timeoutMs / 1000} seconds.`)
}
export async function startAIServices(): Promise<void> {
  if (!(await isHealthy(`http://${host}:${llamaPort}/health`))) {
    if (!fs.existsSync(llamaExe)) {
      throw new Error(`llama-server executable not found: ${llamaExe}`)
    }
    if (!fs.existsSync(modelPath)) {
      throw new Error(`GGUF model file not found: ${modelPath}`)
    }

    const hasCuda = fs.existsSync(cudaDll)
    const gpuLayers = process.env.LLM_GPU_LAYERS ?? process.env.GPU_LAYERS ?? (hasCuda ? '99' : '0')
    const llamaArgs = [
      '-m', modelPath,
      '--host', host,
      '--port', String(llamaPort),
      '-c', '4096'
    ]
    const llamaEnv: Record<string, string> = {}

    if (hasCuda && gpuLayers !== '0') {
      llamaArgs.push('-ngl', gpuLayers)
      llamaEnv.PATH = `${cudaDir};${ollamaLibDir};${process.env.PATH ?? ''}`
      llamaEnv.GGML_BACKEND_PATH = cudaDll
      console.log(`[AI services] Starting local llama.cpp server with GPU acceleration (-ngl ${gpuLayers})...`)
    } else {
      console.log('[AI services] Starting local llama.cpp server on CPU...')
    }

    const llama = launch(
      llamaExe,
      llamaArgs,
      root,
      'llama.cpp',
      llamaEnv
    )
    await waitForHealth(`http://${host}:${llamaPort}/health`, llama, 'llama.cpp', 120_000)
  } else {
    console.log('[AI services] llama.cpp server is already healthy.')
  }
  if (!(await isHealthy(`http://${host}:${ragPort}/healthz`))) {
    if (!fs.existsSync(pythonExe)) {
      throw new Error(`Python virtual environment not found: ${pythonExe}`)
    }
    console.log('[AI services] Starting FastAPI RAG service...')
    const api = launch(
      pythonExe,
      ['-m', 'uvicorn', 'api.main:app', '--host', host, '--port', String(ragPort), '--reload'],
      root,
      'FastAPI RAG',
      { LLM_BASE_URL: `http://${host}:${llamaPort}` }
    )
    await waitForHealth(`http://${host}:${ragPort}/healthz`, api, 'FastAPI RAG', 60_000)
  } else {
    console.log('[AI services] FastAPI RAG service is already healthy.')
  }
  console.log('[AI services] All AI services are ready.')
}
