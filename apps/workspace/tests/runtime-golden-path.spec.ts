import { expect, Page, test } from '@playwright/test'

const commitment = {
  id: 'wc_demo', title: 'PMA 黄金链路', status: 'accepted', proposed_role: 'DROLE-01',
  objective: '生成候选表达', version: 2, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
}
const traceId = '0123456789abcdef0123456789abcdef'

async function mockLoginAndHealth(page: Page) {
  await page.route('**/auth/realms/1cat/protocol/openid-connect/token', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'test-token' }),
  }))
  await page.route('**/health/ready', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready', database: 'ok' }),
  }))
  await page.route('**/v1/runtime-model', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({
      provider: 'deepseek', model: 'deepseek-v4-pro', mode: 'deepseek-api-key',
      execution_enabled: true, credential_location: 'model-gateway-docker-secret',
    }),
  }))
}

test('PMA Commitment → Run → Attempt → 人工确认', async ({ page }) => {
  await mockLoginAndHealth(page)
  let runPoll = 0
  let commitmentStatus = 'accepted'
  await page.route('**/v1/commitments', async route => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ ...commitment, status: 'proposed', version: 1 }) })
    } else {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ ...commitment, status: commitmentStatus }]) })
    }
  })
  await page.route('**/v1/commitments/wc_demo/transition', async route => {
    const request = route.request().postDataJSON() as { status: string }
    commitmentStatus = request.status
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...commitment, status: request.status, version: 3 }) })
  })
  await page.route('**/v1/runs', route => {
    const run = {
      id: 'run_demo', commitment_id: 'wc_demo', role_id: 'DROLE-01', profile_id: 'pma', status: 'queued',
      correlation_id: 'corr_demo', trace_id: traceId, output: {}, failure: {}, created_at: new Date().toISOString(),
    }
    return route.fulfill({
      status: route.request().method() === 'POST' ? 202 : 200,
      contentType: 'application/json', body: JSON.stringify(route.request().method() === 'POST' ? run : []),
    })
  })
  await page.route('**/v1/runs/run_demo', route => {
    const statuses = ['accepted', 'running', 'evidence_accepted']
    const status = statuses[Math.min(runPoll++, statuses.length - 1)]
    if (status === 'evidence_accepted' && commitmentStatus === 'accepted') commitmentStatus = 'submitted'
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      id: 'run_demo', commitment_id: 'wc_demo', role_id: 'DROLE-01', profile_id: 'pma', status,
      correlation_id: 'corr_demo', trace_id: traceId, current_attempt_id: 'attempt_demo', current_attempt: {
        id: 'attempt_demo', run_id: 'run_demo', attempt_no: 1, status: status === 'accepted' ? 'claimed' : 'running',
        worker_id: 'worker-test', lease_until: new Date(Date.now() + 30_000).toISOString(),
        heartbeat_at: new Date().toISOString(), output: {}, failure: {}, retryability: 'conditional',
      }, output: status === 'evidence_accepted' ? { candidate_status: 'submitted' } : {}, failure: {}, created_at: new Date().toISOString(),
    }) })
  })
  await page.route('**/v1/runs/run_demo/attempts', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{
    id: 'attempt_demo', run_id: 'run_demo', attempt_no: 1, status: 'succeeded', worker_id: 'worker-test',
    lease_until: new Date().toISOString(), heartbeat_at: new Date().toISOString(), output: {}, failure: {}, retryability: 'safe',
  }]) }))
  await page.route('**/v1/runs/run_demo/timeline', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([
    { id: 't1', run_id: 'run_demo', from_status: 'queued', to_status: 'accepted', reason: 'worker claimed queued run', actor: 'worker-test', correlation_id: 'corr_demo', created_at: new Date().toISOString() },
    { id: 't2', run_id: 'run_demo', from_status: 'running', to_status: 'evidence_accepted', reason: 'attempt completed with accepted evidence', actor: 'worker-test', correlation_id: 'corr_demo', created_at: new Date().toISOString() },
  ]) }))

  await page.goto('/?view=runtime')
  await page.getByLabel('密码').fill('test-password')
  await page.getByRole('button', { name: '安全登录' }).click()
  await expect(page.getByText('Runtime 就绪')).toBeVisible()
  await expect(page.getByText(/deepseek \/ deepseek-v4-pro · 真实执行/)).toBeVisible()
  await page.getByRole('button', { name: '创建并启动 PMA Run' }).click()
  await expect(page.getByText('evidence_accepted', { exact: true })).toBeVisible({ timeout: 10_000 })
  await expect(page.locator('.runtime-attempt code').getByText('attempt_demo', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '在 Jaeger 打开 Trace' })).toHaveAttribute('href', `http://127.0.0.1:16686/trace/${traceId}`)
  await expect(page.getByRole('link', { name: '打开 Grafana Runtime 看板' })).toBeVisible()
  await expect(page.getByRole('link', { name: '查询 Prometheus 指标' })).toBeVisible()
  await page.getByRole('button', { name: '人工审阅并确认 fulfilled' }).click()
  await expect(page.getByText(/Commitment 现为 fulfilled/)).toBeVisible()

  await page.reload()
  await expect(page.getByText('run_demo', { exact: true }).first()).toBeVisible()
  await expect(page.locator('.runtime-attempt code').getByText('attempt_demo', { exact: true })).toBeVisible()
  await expect(page.getByText(/Commitment 现为 fulfilled/)).toBeVisible()
})

test('可从最近 Run 切换检查 safe recovery 与 unknown', async ({ page }) => {
  await mockLoginAndHealth(page)
  const createdAt = new Date().toISOString()
  const safeRun = {
    id: 'run_safe', commitment_id: 'wc_safe', role_id: 'DROLE-01', profile_id: 'pma',
    status: 'evidence_accepted', correlation_id: 'corr_safe', current_attempt_id: 'attempt_safe_2',
    output: { candidate_status: 'submitted' }, failure: {}, created_at: createdAt,
  }
  const unknownRun = {
    id: 'run_unknown', commitment_id: 'wc_unknown', role_id: 'DROLE-01', profile_id: 'pma',
    status: 'unknown', correlation_id: 'corr_unknown', current_attempt_id: 'attempt_unknown_1',
    output: {}, failure: { retryability: 'unsafe' }, created_at: new Date(Date.now() - 1000).toISOString(),
  }
  await page.route('**/v1/runs', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify([safeRun, unknownRun]),
  }))
  await page.route('**/v1/commitments', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify([
      { ...commitment, id: 'wc_safe', title: '派发前崩溃', status: 'submitted' },
      { ...commitment, id: 'wc_unknown', title: '派发后结果不明', status: 'active' },
    ]),
  }))
  await page.route('**/v1/runs/run_safe', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(safeRun),
  }))
  await page.route('**/v1/runs/run_safe/attempts', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify([
      { id: 'attempt_safe_1', run_id: 'run_safe', attempt_no: 1, status: 'lost', worker_id: 'victim', lease_until: createdAt, heartbeat_at: createdAt, output: {}, failure: {}, failure_class: 'lease_expired_before_external_start', retryability: 'safe' },
      { id: 'attempt_safe_2', run_id: 'run_safe', attempt_no: 2, status: 'succeeded', worker_id: 'recovery', lease_until: createdAt, heartbeat_at: createdAt, output: {}, failure: {}, retryability: 'safe' },
    ]),
  }))
  await page.route('**/v1/runs/run_safe/timeline', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.route('**/v1/runs/run_unknown', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(unknownRun),
  }))
  await page.route('**/v1/runs/run_unknown/attempts', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify([
      { id: 'attempt_unknown_1', run_id: 'run_unknown', attempt_no: 1, status: 'unknown', worker_id: 'victim', lease_until: createdAt, heartbeat_at: createdAt, output: {}, failure: {}, failure_class: 'lease_expired_after_external_dispatch', retryability: 'unsafe' },
    ]),
  }))
  await page.route('**/v1/runs/run_unknown/timeline', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))

  await page.goto('/?view=runtime')
  await page.getByLabel('密码').fill('test-password')
  await page.getByRole('button', { name: '安全登录' }).click()
  await page.getByLabel('切换最近 Run').selectOption('run_safe')
  await expect(page.getByText('安全恢复已完成')).toBeVisible()
  await expect(page.locator('.runtime-attempt code').getByText('attempt_safe_1', { exact: true })).toBeVisible()
  await expect(page.locator('.runtime-attempt code').getByText('attempt_safe_2', { exact: true })).toBeVisible()
  await page.getByLabel('切换最近 Run').selectOption('run_unknown')
  await expect(page.getByText('不确定副作用已隔离')).toBeVisible()
  await expect(page.getByText('lease_expired_after_external_dispatch / unsafe')).toBeVisible()
})

test('401 会清除 session token 并返回登录页', async ({ page }) => {
  await mockLoginAndHealth(page)
  await page.route('**/v1/runs', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify([]),
  }))
  await page.route('**/v1/commitments', route => route.fulfill({
    status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'expired' }),
  }))
  await page.goto('/?view=runtime')
  await page.getByLabel('密码').fill('test-password')
  await page.getByRole('button', { name: '安全登录' }).click()
  await page.getByRole('button', { name: '创建并启动 PMA Run' }).click()
  await expect(page.getByRole('heading', { name: '进入 Runtime 研修界面' })).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('1cat_runtime_token'))).toBeNull()
})
