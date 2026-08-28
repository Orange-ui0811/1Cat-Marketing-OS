import { spawn } from 'node:child_process'
import { once } from 'node:events'
import process from 'node:process'

const serverUrl = 'http://127.0.0.1:4173'
const childEnv = { ...process.env, VITE_RUNTIME_MODE: 'api' }
const vite = spawn(
  process.execPath,
  ['./node_modules/vite/bin/vite.js', '--host', '127.0.0.1'],
  { env: childEnv, stdio: ['ignore', 'inherit', 'inherit'] },
)

async function waitForServer() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (vite.exitCode !== null) throw new Error(`Vite exited before readiness: ${vite.exitCode}`)
    try {
      const response = await fetch(serverUrl)
      if (response.ok) return
    } catch {
      // The development server is still starting.
    }
    await new Promise(resolve => setTimeout(resolve, 250))
  }
  throw new Error(`Timed out waiting for ${serverUrl}`)
}

async function stopServer() {
  if (vite.exitCode !== null) return
  vite.kill()
  await Promise.race([
    once(vite, 'exit'),
    new Promise(resolve => setTimeout(resolve, 3_000)),
  ])
}

let exitCode = 1
try {
  await waitForServer()
  const playwright = spawn(
    process.execPath,
    ['./node_modules/@playwright/test/cli.js', 'test'],
    { env: childEnv, stdio: 'inherit' },
  )
  const [code] = await once(playwright, 'exit')
  exitCode = code ?? 1
} finally {
  await stopServer()
}

process.exitCode = exitCode
