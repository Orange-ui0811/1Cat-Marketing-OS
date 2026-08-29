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
  start_mo_retrospective: '启动 MO 复盘', accept_retrospective: '人工确认最终方案并完成案例',
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
  const knowledgeKinds = index >= 9 ? ['brief', 'review', 'fact', 'claim', 'campaign', 'content', 'review']
    : index >= 5 ? ['brief', 'review', 'fact', 'claim', 'campaign', 'content']
      : index >= 3 ? ['brief', 'review', 'fact', 'claim'] : index >= 1 ? ['brief', 'review'] : ['brief']
  const resources: any[] = knowledgeKinds.map((kind, resourceIndex) => ({
    id: `ref_knowledge_${resourceIndex}`, case_id: 'case_demo', step_id: `step_${kind}`,
    resource_type: 'knowledge', resource_id: `knowledge_${resourceIndex}`, resource_version: 1,
    relation: `${kind}_candidate`, created_at: now,
    resource: {
      id: `knowledge_${resourceIndex}`, kind, title: `${kind} 完整候选`, body: `${kind} 的完整可审阅正文，包含来源、边界、执行建议和人工门禁。`,
      status: 'candidate', version: 1, source_refs: ['synthetic://test'], created_by: 'runtime-worker',
      metadata: { stage_key: kind === 'fact' || kind === 'claim' ? 'pma' : kind === 'campaign' || kind === 'content' ? 'bga' : kind === 'review' && resourceIndex > 4 ? 'mo_retrospective' : kind === 'review' ? 'mo_plan' : 'brief' },
    },
  }))
  if (index >= 6) resources.push({
    id: 'ref_task', case_id: 'case_demo', step_id: 'step_content_review', resource_type: 'manual_task',
    resource_id: 'task_demo', resource_version: index >= 7 ? 2 : 1, relation: 'simulated_publish_task', created_at: now,
    resource: {
      id: 'task_demo', task_type: 'publish', platform: 'bilibili', status: index >= 7 ? 'simulated' : 'pending', version: index >= 7 ? 2 : 1,
      instructions: '仅执行演示模拟回执；不得登录或写入真实内容平台。',
      receipt: index >= 7 ? { external_effect: false, case_id: 'case_demo', note: '未写入真实平台' } : {},
    },
  })
  return {
    id: 'case_demo', title: '三 Agent 完整 Demo', objective: '验证八类页面中的人工门禁业务闭环。',
    target_platform: 'bilibili', execution_mode: 'synthetic', status, current_stage: current,
    correlation_id: 'workspace-corr', version: index + 1, created_at: now, updated_at: now,
    stages: stageKeys.map((step_key, ordinal) => ({
      id: `step_${step_key}`, case_id: 'case_demo', step_key, ordinal: ordinal + 1,
      status: ordinal < currentOrdinal ? 'completed' : step_key === current ? currentStatus : 'pending',
      input: {}, output: {}, failure: {}, started_at: now,
      completed_at: ordinal < currentOrdinal || status === 'completed' ? now : null,
    })),
    resources,
    messages: [{ id: 'msg_system', case_id: 'case_demo', stage_key: 'brief', channel: 'MO', sender_type: 'system', intent: 'message', body: 'Brief 已持久化。', attachments: [], created_by: 'runtime-system', created_at: now }],
    decisions: flow.slice(0, index).filter(action => action.startsWith('approve') || action === 'accept_retrospective').map((action, decisionIndex) => ({
      id: `decision_${decisionIndex}`, case_id: 'case_demo', stage_key: current, decision: 'approved', reason: labels[action], subject_refs: [], metadata: {}, actor_id: 'admin', created_at: now,
    })),
    reconciliations: [],
    final_deliverable: index >= 9 ? {
      id: 'deliverable_demo', case_id: 'case_demo', title: '三 Agent 完整 Demo · 完整营销执行方案',
      status: index >= 10 ? 'accepted' : 'draft', format_version: 'marketing-plan/v1', version: index >= 10 ? 2 : 1,
      document: {
        sections: ['执行摘要', '受众与问题', '事实底稿', 'Claim 边界', 'Campaign 策略', '完整内容母稿', '发布与反馈', '度量与风险', 'MO 复盘', '证据索引'].map((title, sectionIndex) => ({ key: `section_${sectionIndex}`, title, content: `${title}的完整可审阅内容。`, source_refs: [] })),
        evidence_index: [], boundary: { publishing: 'simulated', external_effect: false, pii: false, business_outcome_claimed: false },
      },
      markdown: '# 完整营销执行方案', source_refs: [{ type: 'knowledge', id: 'knowledge_1', version: 1 }],
      accepted_by: index >= 10 ? 'admin' : null, accepted_at: index >= 10 ? now : null, created_at: now, updated_at: now,
    } : null,
    next_actions: index < flow.length ? [{ action: flow[index], label: labels[flow[index]] }] : [],
    boundary: { publishing: 'simulated', external_effect: false, pii: false, business_outcome_claimed: false },
  }
}

async function mockBootstrap(page: Page) {
  await page.route('**/auth/realms/1cat/protocol/openid-connect/token', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'workspace-token' }) }))
  await page.route('**/v1/runtime-model', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ provider: 'deepseek', model: 'deepseek-v4-pro', mode: 'deepseek-api-key', execution_enabled: true, credential_location: 'secret' }) }))
  await page.route('**/v1/agent-configs', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
}

test('不进入完整流程页也能在八类页面完成案例并查看结果', async ({ page }) => {
  await mockBootstrap(page)
  let index = 0
  let created = false
  await page.route('**/v1/marketing-cases?limit=100*', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(created ? [snapshot(index)] : []) }))
  await page.route('**/v1/marketing-cases', async route => {
    if (route.request().method() !== 'POST') return route.fallback()
    created = true
    await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(snapshot(index)) })
  })
  await page.route('**/v1/marketing-cases/case_demo', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot(index)) }))
  await page.route('**/v1/marketing-cases/case_demo/commands', async route => {
    const body = route.request().postDataJSON() as { action: string }
    expect(body.action).toBe(flow[index])
    expect(route.request().headers()['if-match']).toBe(String(index + 1))
    index += 1
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot(index)) })
  })

  await page.goto('/?view=workspace')
  await expect(page.getByRole('button', { name: '向 MO 发起新目标' }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: '协作中心', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '真实任务', exact: true }).click()
  await page.getByLabel('密码').fill('123456')
  await page.getByRole('button', { name: '进入八类工作台' }).click()
  await page.getByRole('button', { name: '新建营销任务' }).click()
  await page.getByRole('button', { name: '创建案例' }).click()
  await expect(page.getByText('创建 Brief').first()).toBeVisible()

  async function runTask() { await page.getByRole('button', { name: '执行任务' }).click() }
  async function decide(label: string) {
    await page.getByRole('button', { name: '决策台账' }).click()
    await page.getByRole('button', { name: label }).click()
    await page.getByRole('button', { name: '确认并记录' }).click()
    await page.getByRole('button', { name: '任务中心' }).click()
  }

  await runTask(); await decide(labels.approve_mo_plan)
  await runTask(); await decide(labels.approve_product)
  await runTask(); await decide(labels.approve_content)
  await runTask(); await runTask(); await runTask(); await decide(labels.accept_retrospective)

  await page.getByRole('button', { name: '业务对象' }).click()
  await expect(page.getByText('FINAL DELIVERABLE')).toBeVisible()
  await expect(page.getByRole('heading', { name: '三 Agent 完整 Demo · 完整营销执行方案' })).toBeVisible()
  await expect(page.getByRole('button', { name: '下载 Markdown' })).toBeVisible()
  await expect(page.getByText('发布 simulated · external_effect=false · 不声明真实营销效果', { exact: true })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('view')).toBe('objects')
  expect(page.url()).not.toContain('view=workflow')

  await page.reload()
  await expect(page.getByRole('button', { name: '向 MO 发起新目标' }).first()).toBeVisible()
  await page.getByRole('button', { name: '真实任务', exact: true }).click()
  await expect(page.getByText('FINAL DELIVERABLE')).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('1cat_runtime_active_case'))).toBe('case_demo')
})

test('八类页面登录失效时清除会话并返回统一登录页', async ({ page }) => {
  await mockBootstrap(page)
  await page.route('**/v1/marketing-cases?limit=100*', route => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'expired' }) }))
  await page.goto('/?view=tasks')
  await page.getByRole('button', { name: '真实任务', exact: true }).click()
  await page.getByLabel('密码').fill('123456')
  await page.getByRole('button', { name: '进入八类工作台' }).click()
  await expect(page.getByRole('heading', { name: '登录 Runtime' })).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('1cat_runtime_token'))).toBeNull()
})

test('异常处置页提供 Unknown 人工对账而不是自动重试', async ({ page }) => {
  await mockBootstrap(page)
  const item: any = snapshot(1)
  item.status = 'blocked'; item.current_stage = 'mo_plan'; item.stages[1].status = 'blocked'
  item.stages[1].active_run_id = 'run_unknown'
  item.stages[1].failure = { failure_class: 'external_result_unknown', run_status: 'unknown', retryability: 'unsafe' }
  item.next_actions = [{ action: 'resolve_unknown', label: '提交 Unknown 人工对账' }, { action: 'cancel_case', label: '取消案例' }]
  await page.addInitScript(() => { sessionStorage.setItem('1cat_runtime_token', 'workspace-token'); sessionStorage.setItem('1cat_runtime_active_case', 'case_demo') })
  await page.route('**/v1/marketing-cases?limit=100*', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([item]) }))
  await page.route('**/v1/marketing-cases/case_demo', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(item) }))
  await page.goto('/?view=holds')
  await page.getByRole('button', { name: '真实任务', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Unknown 人工对账' })).toBeVisible()
  await expect(page.getByRole('button', { name: '提交对账结论' })).toBeVisible()
  await expect(page.getByRole('button', { name: /安全重试/ })).toHaveCount(0)
})
