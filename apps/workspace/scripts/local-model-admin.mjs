import { spawn } from 'node:child_process'
import { chmod, mkdir, readFile, rename, stat, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'

const route = '/local-admin/model-config'
const maxBodyBytes = 8 * 1024
let operationInProgress = false

function sendJson(response, status, payload) {
  response.statusCode = status
  response.setHeader('Content-Type', 'application/json; charset=utf-8')
  response.setHeader('Cache-Control', 'no-store')
  response.end(JSON.stringify(payload))
}

function isLoopback(address = '') {
  return address === '127.0.0.1' || address === '::1' || address === '::ffff:127.0.0.1'
}

function isLocalOrigin(origin = '') {
  if (!origin) return true
  try {
    const url = new URL(origin)
    return url.hostname === '127.0.0.1' || url.hostname === 'localhost' || url.hostname === '[::1]'
  } catch {
    return false
  }
}

async function readEnv(projectRoot) {
  const values = new Map()
  const content = await readFile(join(projectRoot, '.env'), 'utf8').catch(() => '')
  for (const line of content.split(/\r?\n/)) {
    const split = line.indexOf('=')
    if (split > 0 && !line.startsWith('#')) values.set(line.slice(0, split), line.slice(split + 1))
  }
  return values
}

async function statusPayload(projectRoot) {
  const env = await readEnv(projectRoot)
  const secretPath = join(projectRoot, '.runtime', 'secrets', 'model_api_key')
  const secretSize = await stat(secretPath).then(file => file.size).catch(() => 0)
  return {
    available: true,
    provider: env.get('HERMES_MODEL_PROVIDER') || 'deepseek',
    model: env.get('HERMES_MODEL_ID') || 'deepseek-v4-pro',
    mode: env.get('MODEL_MODE') || 'deepseek-api-key',
    credential_configured: secretSize > 0,
    execution_enabled: env.get('HERMES_EXECUTION_ENABLED') === 'true',
    operation_in_progress: operationInProgress,
  }
}

async function readJsonBody(request) {
  const chunks = []
  let size = 0
  for await (const chunk of request) {
    size += chunk.length
    if (size > maxBodyBytes) throw new Error('请求内容过大。')
    chunks.push(chunk)
  }
  if (!chunks.length) return {}
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'))
  } catch {
    throw new Error('请求格式无效。')
  }
}

async function saveSecret(projectRoot, apiKey) {
  const value = String(apiKey || '').trim()
  if (value.length < 16 || value.length > 512 || /\s/.test(value)) throw new Error('API Key 格式无效。')
  const target = join(projectRoot, '.runtime', 'secrets', 'model_api_key')
  const temporary = `${target}.${process.pid}.tmp`
  await mkdir(dirname(target), { recursive: true, mode: 0o700 })
  await writeFile(temporary, `${value}\n`, { encoding: 'utf8', mode: 0o600 })
  await rename(temporary, target)
  await chmod(target, 0o600).catch(() => {})
}

function locateBash() {
  const candidates = [
    process.env.ONECAT_GIT_BASH,
    join(process.env.ProgramFiles || 'C:\\Program Files', 'Git', 'bin', 'bash.exe'),
    'C:\\Program Files\\Git\\usr\\bin\\bash.exe',
  ].filter(Boolean)
  return candidates.find(candidate => existsSync(candidate))
}

function redact(output) {
  return output
    .replace(/Bearer\s+\S+/gi, 'Bearer [redacted]')
    .replace(/\bsk-[A-Za-z0-9_-]{12,}\b/g, '[redacted]')
    .slice(-4000)
}

function friendlyFailure(error) {
  const raw = redact(error instanceof Error ? error.message : String(error))
  if (/Access is denied/i.test(raw)) return '本机助手没有访问 Docker Desktop 的权限，请使用 start-demo1.cmd 启动页面。'
  if (/Connection refused|urlopen error/i.test(raw)) return 'Model Gateway 尚未就绪，请稍后重试。'
  if (/401|403|Unauthorized|Forbidden/i.test(raw)) return 'DeepSeek 拒绝了凭据，请检查 API Key 是否有效。'
  if (/404|model.*not.*found/i.test(raw)) return 'DeepSeek 未找到该模型，请检查模型名称或账号权限。'
  if (/timeout|timed out/i.test(raw)) return '连接 DeepSeek 超时，请检查网络或代理设置。'
  return '请检查 Docker Desktop、DeepSeek Key 和网络连接后重试。'
}

function runOneCat(projectRoot, args, timeoutMs = 10 * 60 * 1000) {
  const bash = locateBash()
  if (!bash) return Promise.reject(new Error('没有找到 Git Bash。'))
  return new Promise((resolvePromise, rejectPromise) => {
    const child = spawn(bash, ['./bin/1cat', ...args], {
      cwd: projectRoot,
      windowsHide: true,
      env: { ...process.env, LANG: 'C.UTF-8' },
    })
    let output = ''
    const collect = chunk => { output += chunk.toString('utf8') }
    child.stdout.on('data', collect)
    child.stderr.on('data', collect)
    const timer = setTimeout(() => {
      child.kill()
      rejectPromise(new Error('配置操作超时，请检查 Docker Desktop 和网络。'))
    }, timeoutMs)
    child.on('error', error => {
      clearTimeout(timer)
      rejectPromise(error)
    })
    child.on('close', code => {
      clearTimeout(timer)
      if (code === 0) resolvePromise(redact(output))
      else rejectPromise(new Error(redact(output) || `1Cat 配置命令退出：${code}`))
    })
  })
}

export function localModelAdmin(rootDirectory) {
  const projectRoot = resolve(rootDirectory, '..', '..', '1Cat-Marketing-OS')
  return {
    name: '1cat-local-model-admin',
    configureServer(server) {
      server.middlewares.use(async (request, response, next) => {
        const url = new URL(request.url || '/', 'http://127.0.0.1')
        if (url.pathname !== route) return next()
        if (!isLoopback(request.socket.remoteAddress) || !isLocalOrigin(request.headers.origin)) {
          return sendJson(response, 403, { message: '本机模型配置只允许从本机页面访问。' })
        }
        if (request.method === 'GET') return sendJson(response, 200, await statusPayload(projectRoot))
        if (request.method !== 'POST') return sendJson(response, 405, { message: '不支持的操作。' })
        if (operationInProgress) return sendJson(response, 409, { message: '模型配置正在进行，请稍候。' })

        operationInProgress = true
        try {
          const payload = await readJsonBody(request)
          if (payload.api_key) await saveSecret(projectRoot, payload.api_key)
          const current = await statusPayload(projectRoot)
          if (!current.credential_configured) throw new Error('请先输入 DeepSeek API Key。')
          if (payload.action === 'test') {
            if (!current.execution_enabled) throw new Error('请先验证 Key 并启用真实执行。')
            await runOneCat(projectRoot, ['model-test'], 3 * 60 * 1000)
            operationInProgress = false
            return sendJson(response, 200, {
              ...(await statusPayload(projectRoot)),
              message: 'DeepSeek Chat Completion 测试通过，模型可以正常调用。',
              model_test_passed: true,
            })
          }
          await runOneCat(projectRoot, ['auth', 'deepseek', '--reuse-secret'])
          await runOneCat(projectRoot, ['restart-agents'])
          operationInProgress = false
          sendJson(response, 200, {
            ...(await statusPayload(projectRoot)),
            message: 'DeepSeek 已验证，三个 Agent 已切换到真实执行。',
          })
        } catch (error) {
          operationInProgress = false
          sendJson(response, 502, {
            ...(await statusPayload(projectRoot)),
            message: 'DeepSeek 验证或 Agent 重启失败。',
            detail: friendlyFailure(error),
          })
        } finally {
          operationInProgress = false
        }
      })
    },
  }
}
