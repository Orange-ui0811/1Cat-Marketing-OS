import { expect, Page, test } from '@playwright/test'

const now = new Date().toISOString()
const flow = [
  'start_mo_plan', 'approve_mo_plan', 'start_pma', 'approve_product', 'start_bga', 'approve_content',
  'record_simulated_publish', 'record_synthetic_feedback', 'start_mo_retrospective', 'accept_retrospective',
]
const labels: Record<string, string> = {
  start_mo_plan: '启动 MO 规划', approve_mo_plan: '人工确认协作计划', start_pma: '启动 PMA',
  approve_product: '人工审核 Fact / Claim', start_bga: '启动 BGA', approve_content: '人工审核 Campaign / Content',
  record_simulated_publish: '记录模拟发布回执', record_synthetic_feedback: '登记合成 Lead 与销售反馈',
  start_mo_retrospective: '启动 MO 复盘', accept_retrospective: '人工确认复盘并完成案例',
}
const stageKeys = ['brief', 'mo_plan', 'pma', 'product_review', 'bga', 'content_review', 'simulated_publish', 'feedback', 'mo_retrospective']

function snapshot(index: number) {
  const states = [
    ['mo_plan', 'active', 'ready'], ['mo_plan', 'awaiting_human', 'awaiting_human'],
    ['pma', 'active', 'ready'], ['product_review', 'awaiting_human', 'ready'],
    ['bga', 'active', 'ready'], ['content_review', 'awaiting_human', 'ready'],
    ['simulated_publish', 'awaiting_human', 'ready'], ['feedback', 'awaiting_human', 'ready'],
    ['mo_retrospective', 'active', 'ready'], ['mo_retrospective', 'awaiting_human', 'awaiting_human'],
    ['mo_retrospective', 'completed', 'completed'],
  ] as const
  const [current, status, currentStatus] = states[index]
  const currentOrdinal = stageKeys.indexOf(current)
  return {
    id: 'case_demo', title: '三 Agent 完整 Demo', objective: '验证统一前端中的人工门禁业务闭环。',
    target_platform: 'bilibili', execution_mode: 'synthetic', status, current_stage: current,
    correlation_id: 'workflow-corr', version: index + 1, created_at: now, updated_at: now,
    stages: stageKeys.map((step_key, ordinal) => ({
      id: `step_${step_key}`, case_id: 'case_demo', step_key, ordinal: ordinal + 1,
      status: ordinal < currentOrdinal ? 'completed' : step_key === current ? currentStatus : 'pending',
      input: {}, output: {}, failure: {}, started_at: now,
      completed_at: ordinal < currentOrdinal || status === 'completed' ? now : null,
    })),
    resources: index >= 6 ? [{
      id: 'ref_task', case_id: 'case_demo', step_id: 'step_content_review', resource_type: 'manual_task',
      resource_id: 'task_demo', resource_version: index >= 7 ? 2 : 1, relation: 'simulated_publish_task', created_at: now,
      resource: {
        id: 'task_demo', task_type: 'publish', platform: 'bilibili', status: index >= 7 ? 'simulated' : 'pending', version: index >= 7 ? 2 : 1,
        instructions: '仅执行演示模拟回执；不得登录或写入真实内容平台。',
        receipt: index >= 7 ? { external_effect: false, case_id: 'case_demo', note: '未写入真实平台' } : {},
      },
    }] : [],
    next_actions: index < flow.length ? [{ action: flow[index], label: labels[flow[index]] }] : [],
    boundary: { publishing: 'simulated', external_effect: false, pii: false, business_outcome_claimed: false },
  }
}

async function mockLogin(page: Page) {
  await page.route('**/auth/realms/1cat/protocol/openid-connect/token', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'workflow-token' }),
  }))
  await page.route('**/v1/runtime-model', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({
      provider: 'deepseek', model: 'deepseek-v4-pro', mode: 'deepseek-api-key', execution_enabled: true,
      credential_location: 'model-gateway-secret-file',
    }),
  }))
}

test('九阶段流程可逐门禁推进、刷新恢复并展示 simulated 边界', async ({ page }) => {
  await mockLogin(page)
  let index = 0
  let created = false
  await page.route('**/v1/marketing-cases?limit=20', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(created ? [snapshot(index)] : []),
  }))
  await page.route('**/v1/marketing-cases', async route => {
    if (route.request().method() !== 'POST') return route.fallback()
    created = true
    await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(snapshot(index)) })
  })
  await page.route('**/v1/marketing-cases/case_demo', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(snapshot(index)),
  }))
  await page.route('**/v1/marketing-cases/case_demo/commands', async route => {
    const body = route.request().postDataJSON() as { action: string }
    expect(body.action).toBe(flow[index])
    expect(route.request().headers()['if-match']).toBe(String(index + 1))
    index += 1
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot(index)) })
  })

  await page.goto('/?view=workflow')
  await page.getByLabel('密码').fill('123456')
  await page.getByRole('button', { name: '进入工作台' }).click()
  await expect(page.getByRole('heading', { name: '建立营销案例' })).toBeVisible()
  await page.getByRole('button', { name: '创建并进入流程' }).click()
  await expect(page.getByText('九阶段状态机')).toBeVisible()

  for (const action of flow) {
    await page.getByRole('button', { name: labels[action] }).click()
  }
  await expect(page.getByRole('heading', { name: '技术链路已完成' })).toBeVisible()
  await expect(page.getByText(/发布回执为 simulated/)).toBeVisible()
  await expect(page.getByText('external_effect=false')).toBeVisible()
  await expect(page.getByText('未写入真实平台')).toBeVisible()

  await page.reload()
  await expect(page.getByRole('heading', { name: '三 Agent 完整 Demo' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '技术链路已完成' })).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('1cat_runtime_active_case'))).toBe('case_demo')
})

test('营销流程接口 401 时清除会话并返回登录页', async ({ page }) => {
  await mockLogin(page)
  await page.route('**/v1/marketing-cases?limit=20', route => route.fulfill({
    status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'expired' }),
  }))
  await page.goto('/?view=workflow')
  await page.getByLabel('密码').fill('123456')
  await page.getByRole('button', { name: '进入工作台' }).click()
  await expect(page.getByRole('heading', { name: '登录 Runtime' })).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('1cat_runtime_token'))).toBeNull()
})

test('完整流程展示不可覆盖 Attempt、故障事实与 unknown 人工对账边界', async ({ page }) => {
  const item = snapshot(1) as any
  item.status = 'blocked'
  item.current_stage = 'mo_plan'
  item.stages[1].status = 'blocked'
  item.stages[1].active_run_id = 'run_demo'
  item.stages[1].failure = { code: 'external_result_unknown', retryability: 'unsafe' }
  item.next_actions = [{ action: 'cancel_case', label: '取消案例' }]
  item.resources = [{
    id: 'ref_run', case_id: item.id, step_id: item.stages[1].id, resource_type: 'run', resource_id: 'run_demo',
    relation: 'active_run', created_at: now, resource: { id: 'run_demo', status: 'unknown' },
  }]
  await page.addInitScript(() => {
    sessionStorage.setItem('1cat_runtime_token', 'workflow-token')
    sessionStorage.setItem('1cat_runtime_active_case', 'case_demo')
  })
  await page.route('**/v1/runtime-model', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    provider: 'deepseek', model: 'deepseek-v4-pro', mode: 'deepseek-api-key', execution_enabled: true,
    credential_location: 'model-gateway-secret-file',
  }) }))
  await page.route('**/v1/marketing-cases?limit=20', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([item]) }))
  await page.route('**/v1/marketing-cases/case_demo', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(item) }))
  await page.route('**/v1/runs/run_demo', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    id: 'run_demo', commitment_id: 'commitment_demo', role_id: 'DROLE-03', profile_id: 'mo', status: 'unknown',
    execution_mode: 'real', case_id: item.id, stage_key: 'mo_plan', correlation_id: 'corr-run', current_attempt_id: 'attempt_1',
    trace_id: '1234567890abcdef1234567890abcdef', output: {}, failure: { code: 'external_result_unknown' }, created_at: now,
  }) }))
  await page.route('**/v1/runs/run_demo/attempts', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{
    id: 'attempt_1', run_id: 'run_demo', attempt_no: 1, status: 'unknown', worker_id: 'worker-a',
    lease_until: now, heartbeat_at: now, hermes_run_id: 'hermes-real-1', output: {},
    failure: { detail: 'stop result unavailable' }, failure_class: 'external_result_unknown', retryability: 'unsafe', started_at: now, completed_at: now,
  }]) }))
  await page.route('**/v1/runs/run_demo/timeline', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{
    id: 'transition_1', run_id: 'run_demo', attempt_id: 'attempt_1', from_status: 'running', to_status: 'unknown',
    reason: 'external_result_unknown', actor: 'runtime-worker', correlation_id: 'corr-run', created_at: now,
  }]) }))

  await page.goto('/?view=workflow')
  await expect(page.getByText('需要人工对账')).toBeVisible()
  await expect(page.getByText('Hermes Run', { exact: true })).toBeVisible()
  await expect(page.getByText('hermes-real-1')).toBeVisible()
  await expect(page.getByText('历史不可覆盖记录').or(page.getByText('当前不可覆盖记录'))).toBeVisible()
  await expect(page.getByText('external_result_unknown').first()).toBeVisible()
  await expect(page.getByRole('button', { name: '取消案例' })).toBeVisible()
  await expect(page.getByRole('button', { name: /安全重试/ })).toHaveCount(0)
})

test('八类页面按视图展示只读服务端案例摘要', async ({ page }) => {
  const item = snapshot(3) as any
  item.resources = [
    ['commitment', 'commitment_1', 'accepted'], ['commitment', 'commitment_2', 'fulfilled'],
    ['handoff', 'handoff_1', 'accepted'], ['knowledge', 'knowledge_1', 'candidate'],
    ['approval', 'approval_1', 'approved'], ['run', 'run_1', 'evidence_accepted'],
  ].map(([resource_type, resource_id, status], index) => ({
    id: `ref_${index}`, case_id: item.id, step_id: item.stages[1].id, resource_type, resource_id,
    relation: 'workflow_fact', created_at: now, resource: { id: resource_id, status, kind: resource_type === 'knowledge' ? 'review' : undefined },
  }))
  await page.addInitScript(() => {
    localStorage.clear()
    sessionStorage.setItem('1cat_runtime_token', 'workflow-token')
    sessionStorage.setItem('1cat_runtime_active_case', 'case_demo')
  })
  await page.route('**/v1/runtime-model', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    provider: 'deepseek', model: 'deepseek-v4-pro', mode: 'deepseek-api-key', execution_enabled: true,
    credential_location: 'model-gateway-secret-file',
  }) }))
  await page.route('**/v1/marketing-cases?limit=20', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([item]) }))
  await page.route('**/v1/marketing-cases/case_demo', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(item) }))

  await page.goto('/?view=workspace')
  const summary = page.getByLabel('服务端案例摘要')
  await expect(summary.getByText('三 Agent 完整 Demo')).toBeVisible()
  await expect(summary.getByText('当前 Run')).toBeVisible()

  await page.getByRole('button', { name: '协作中心' }).click()
  await expect(summary.getByText('Commitment')).toBeVisible()
  await expect(summary.getByText('Handoff')).toBeVisible()
  await page.getByRole('button', { name: '业务对象' }).click()
  await expect(summary.getByText('Knowledge')).toBeVisible()
  await page.getByRole('button', { name: '决策台账' }).click()
  await expect(summary.getByText('Approval')).toBeVisible()
  await page.getByRole('button', { name: '异常处置' }).click()
  await expect(summary.getByText('Unknown Run')).toBeVisible()
  await page.getByRole('button', { name: 'Daily Brief' }).click()
  await expect(summary.getByText('已完成案例')).toBeVisible()
  await page.getByRole('button', { name: 'Agent 配置' }).click()
  await expect(summary.getByText('deepseek / deepseek-v4-pro')).toBeVisible()
  await page.getByRole('button', { name: '运行诊断' }).click()
  await expect(summary.getByText('Runtime')).toBeVisible()
  await expect(summary.getByText('已连接')).toBeVisible()
  await expect(page.getByRole('heading', { name: '真实接入状态与保留边界' })).toBeVisible()
  await expect(page.getByText(/CollaborationThread \/ AgentAssignment.*保留为本地演练/)).toBeVisible()
})
