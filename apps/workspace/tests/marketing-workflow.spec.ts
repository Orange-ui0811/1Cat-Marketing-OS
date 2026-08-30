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

  await page.goto('/?view=tasks')
  await expect(page.getByRole('button', { name: '协作中心', exact: true })).toBeVisible()
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

  await runTask()
  await page.getByRole('button', { name: '协作中心', exact: true }).click()
  await expect(page.getByText('MO 协作计划', { exact: true })).toBeVisible()
  await expect(page.getByText('任务观察器', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'review 完整候选' })).toBeVisible()
  await page.getByRole('button', { name: '任务中心' }).click()
  await decide(labels.approve_mo_plan)
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
  await expect(page.getByText('FINAL DELIVERABLE')).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('1cat_runtime_active_case'))).toBe('case_demo')
})

test('八类页面登录失效时清除会话并返回统一登录页', async ({ page }) => {
  await mockBootstrap(page)
  await page.route('**/v1/marketing-cases?limit=100*', route => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'expired' }) }))
  await page.goto('/?view=tasks')
  await page.getByLabel('密码').fill('123456')
  await page.getByRole('button', { name: '进入八类工作台' }).click()
  await expect(page.getByRole('heading', { name: '登录 Runtime' })).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('1cat_runtime_token'))).toBeNull()
})

test('协作中心把消息发送给真实岗位 Agent 并展示持久化回复', async ({ page }) => {
  await mockBootstrap(page)
  const item: any = snapshot(0)
  item.chat_turns = []
  await page.addInitScript(() => {
    sessionStorage.setItem('1cat_runtime_token', 'workspace-token')
    sessionStorage.setItem('1cat_runtime_active_case', 'case_demo')
  })
  await page.route('**/v1/marketing-cases?limit=100*', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify([item]),
  }))
  await page.route('**/v1/marketing-cases/case_demo/chat-turns', async route => {
    expect(route.request().headers()['if-match']).toBe(String(item.version))
    const requestBody = route.request().postDataJSON() as any
    expect(requestBody).toMatchObject({
      channel: 'PMA', mode: 'consultation', body: '当前 Claim 最需要补什么证据？',
    })
    expect(requestBody.attachments[0]).toMatchObject({
      name: 'brief.md', type: 'text/markdown', size: 14,
    })
    expect(requestBody.attachments[0]).not.toHaveProperty('content')
    expect(requestBody.attachments[0]).not.toHaveProperty('path')
    const userMessage = {
      id: 'msg_chat_user', case_id: item.id, stage_key: item.current_stage, channel: 'PMA',
      sender_type: 'human', intent: 'message', body: '当前 Claim 最需要补什么证据？',
      attachments: requestBody.attachments, created_by: 'admin', created_at: now,
    }
    const agentMessage = {
      id: 'msg_chat_agent', case_id: item.id, stage_key: item.current_stage, channel: 'PMA',
      sender_type: 'agent', intent: 'agent_reply', body: '优先补充可复现测试条件、样本范围和来源版本。',
      attachments: [{ type: 'agent_run', run_id: 'run_chat_pma' }], created_by: 'agent:pma', created_at: now,
    }
    item.version += 2
    item.messages.push(userMessage, agentMessage)
    item.chat_turns = [{
      id: 'chat_turn_pma', case_id: item.id, stage_key: item.current_stage, channel: 'PMA',
      mode: 'consultation', status: 'completed', user_message_id: userMessage.id,
      agent_message_id: agentMessage.id, run_id: 'run_chat_pma', profile_id: 'pma', profile_version: 1,
      profile_hash: 'profile-hash', execution_mode: 'real', failure: {}, created_by: 'admin',
      created_at: now, updated_at: now,
    }]
    await route.fulfill({
      status: 202,
      contentType: 'application/json',
      body: JSON.stringify({ turn: item.chat_turns[0], run: { id: 'run_chat_pma', purpose: 'chat', status: 'queued' }, case_version: item.version - 1 }),
    })
  })
  await page.route('**/v1/marketing-cases/case_demo', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(item),
  }))

  await page.goto('/?view=collaboration')
  await page.getByRole('button').filter({ hasText: 'Product Marketing Agent' }).click()
  await page.locator('.server-composer input[type="file"]').setInputFiles({
    name: 'brief.md', mimeType: 'text/markdown', buffer: Buffer.from('brief metadata'),
  })
  await expect(page.getByText('brief.md')).toBeVisible()
  await page.getByPlaceholder('向真实 PMA Agent 提问…').fill('当前 Claim 最需要补什么证据？')
  const sendButton = page.getByRole('button', { name: '发送给 Agent' })
  await expect(sendButton).toBeVisible()
  await expect(sendButton).toHaveText('发送给 Agent')
  const sendBox = await sendButton.boundingBox()
  expect(sendBox?.width).toBeGreaterThanOrEqual(120)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy()
  await sendButton.click()

  await expect(page.getByText('优先补充可复现测试条件、样本范围和来源版本。')).toBeVisible()
  await expect(page.getByText('真实 Agent 回复', { exact: true })).toBeVisible()
  await expect(page.locator('.server-message-list small').filter({ hasText: 'Run run_chat_pma' }).first()).toBeVisible()
  await expect(page.getByText('brief.md')).toBeVisible()
  await page.setViewportSize({ width: 375, height: 812 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy()
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
  await expect(page.getByRole('heading', { name: 'Unknown 人工对账' })).toBeVisible()
  await expect(page.getByRole('button', { name: '提交对账结论' })).toBeVisible()
  await expect(page.getByRole('button', { name: /安全重试/ })).toHaveCount(0)
})

test('API 模式默认使用服务端事实，旧界面只在明确原型入口中保留', async ({ page }) => {
  await mockBootstrap(page)
  await page.route('**/v1/marketing-cases?limit=100*', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify([]),
  }))
  await page.addInitScript(() => sessionStorage.setItem('1cat_runtime_token', 'workspace-token'))

  await page.goto('/?view=tasks')
  await expect(page.getByText('SERVER SOURCE OF TRUTH')).toBeVisible()
  await expect(page.getByRole('button', { name: '新建营销任务' })).toBeVisible()
  await expect(page.getByText('前端影子演练')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '真实任务', exact: true })).toHaveCount(0)

  await page.getByRole('link', { name: '界面原型参考' }).click()
  await expect(page).toHaveURL(/mode=prototype/)
  await expect(page.getByText('前端界面原型')).toBeVisible()
  await expect(page.getByRole('link', { name: '返回服务端工作台' })).toBeVisible()
})

test('Agent 配置可编辑 Prompt、Skill 与权限并保存为服务端草稿', async ({ page }) => {
  const config = {
    agent: 'MO', profile_name: 'HRM-01-mo', role_name: 'Marketing Orchestrator',
    model: { provider: 'Model Gateway', model: 'deepseek-v4-pro', endpoint_alias: 'gateway/default', credential_ref: 'secret://model', reasoning_level: 'low', max_turns: 1, timeout_seconds: 90 },
    six_pack: ['role_manifest', 'soul', 'skill_pack', 'memory_policy', 'daily_operation', 'evaluation'].map(key => ({ key, version: 'v1.0', status: 'ready', source: `profiles/mo/${key}`, summary: `${key} summary` })),
    skills: [{ id: 'work-plan', version: 'v1.0', enabled: true, status: 'ready', source: 'SKL-OR-02', capability: '拆解计划', permissions: ['organization-runtime:role-scoped'] }],
    permissions: { network: false, terminal: false, browser: false, other_agents: true, memory_write: true, tools: ['OrganizationEvent', 'WorkCommitment'] },
    memory_summary: '只保存岗位偏好与协作习惯，不保存正式业务事实或PII。',
    prompt_templates: { workflow: { version: 'v1.0', body: '按照当前阶段生成受控候选，引用对象版本并保留人工审批边界。' }, chat: { version: 'v1.0', body: '以岗位视角回答问题，区分事实、建议和仍需人工确认的事项。' } },
  }
  let profile: any = { id: 'config-mo', agent_key: 'MO', status: 'published', published_version: 1, config, published_config: structuredClone(config), published_hash: 'a'.repeat(64), updated_by: 'bootstrap', version: 1, updated_at: now, revisions: [] }
  await page.addInitScript(() => sessionStorage.setItem('1cat_runtime_token', 'workspace-token'))
  await page.route('**/v1/marketing-cases?limit=100*', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.route('**/v1/runtime-model', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ provider: 'deepseek', model: 'deepseek-v4-pro', mode: 'deepseek-api-key', execution_enabled: true, credential_location: 'secret' }) }))
  await page.route('**/local-admin/model-config', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ available: true, provider: 'deepseek', model: 'deepseek-v4-pro', mode: 'deepseek-api-key', credential_configured: true, execution_enabled: true, operation_in_progress: false }) }))
  await page.route('**/v1/agent-configs', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([profile]) }))
  await page.route('**/v1/agent-configs/MO', async route => {
    expect(route.request().method()).toBe('PUT')
    expect(route.request().headers()['if-match']).toBe('1')
    const body = route.request().postDataJSON() as any
    expect(body.config.prompt_templates.workflow.version).toBe('v2.0')
    expect(body.config.permissions.tools).toContain('RoleHandoff')
    expect(body.config.skills[0].source).toBe('SKL-OR-02')
    profile = { ...profile, status: 'draft', config: body.config, version: 2, revisions: [{ id: 'rev-2', agent_key: 'MO', version_no: 2, status: 'draft', config: body.config, summary: body.summary, created_by: 'admin', created_at: now }] }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(profile) })
  })

  await page.goto('/?view=agent_config')
  await page.getByRole('button', { name: 'Prompt 模板' }).click()
  const workflowPrompt = page.locator('.server-prompt-editor article').first()
  await workflowPrompt.getByLabel('模板版本').fill('v2.0')
  await workflowPrompt.getByLabel('受控指令').fill('按照当前阶段生成受控候选，引用对象版本、证据缺口并保留全部人工审批边界。')
  await page.getByRole('button', { name: '工具与权限' }).click()
  await page.getByLabel('允许工具（每行一项）').fill('OrganizationEvent\nWorkCommitment\nRoleHandoff')
  await page.getByRole('button', { name: '保存草稿' }).click()
  await expect(page.getByText('草稿', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('尚未保存')).toHaveCount(0)
})

test('运行诊断展示不可覆盖的 Profile 版本、哈希和完整快照', async ({ page }) => {
  const item: any = snapshot(1)
  const profileSnapshot = {
    agent: 'MO', role_name: 'Marketing Orchestrator', model: { model: 'deepseek-v4-pro', reasoning_level: 'low', timeout_seconds: 90 },
    six_pack: [{ key: 'role_manifest', version: 'v1.0', status: 'ready' }],
    skills: [{ id: 'work-plan', version: 'v1.0', enabled: true, status: 'ready', source: 'SKL-OR-02' }],
    permissions: { tools: ['OrganizationEvent'], network: false },
    prompt_templates: { workflow: { version: 'v3.0', body: 'workflow' }, chat: { version: 'v2.0', body: 'chat' } },
  }
  const run = { id: 'run_profile_snapshot', commitment_id: 'commitment-1', role_id: 'DROLE-03', profile_id: 'mo', profile_version: 7, profile_hash: 'b'.repeat(64), profile_snapshot: profileSnapshot, purpose: 'workflow', execution_mode: 'synthetic', case_id: item.id, stage_key: 'mo_plan', status: 'evidence_accepted', correlation_id: 'corr-profile', trace_id: null, output: {}, failure: {}, created_at: now, started_at: now, completed_at: now }
  item.resources.push({ id: 'ref_run_profile', case_id: item.id, step_id: 'step_mo_plan', resource_type: 'run', resource_id: run.id, resource_version: 1, relation: 'mo_plan_run', resource: run, created_at: now })
  await page.addInitScript(() => { sessionStorage.setItem('1cat_runtime_token', 'workspace-token'); sessionStorage.setItem('1cat_runtime_active_case', 'case_demo') })
  await mockBootstrap(page)
  await page.route('**/v1/marketing-cases?limit=100*', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([item]) }))
  await page.route('**/v1/marketing-cases/case_demo', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(item) }))
  await page.route('**/v1/runs/run_profile_snapshot/attempts', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.route('**/v1/runs/run_profile_snapshot/timeline', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.route('**/v1/runs/run_profile_snapshot', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(run) }))

  await page.goto('/?view=diagnostics')
  await expect(page.getByText('运行配置快照')).toBeVisible()
  await page.getByText('运行配置快照').click()
  await expect(page.getByText('Profile v7')).toBeVisible()
  await expect(page.getByText('workflow v3.0')).toBeVisible()
  await expect(page.getByText('work-plan@v1.0 · SKL-OR-02')).toBeVisible()
  await expect(page.getByText('b'.repeat(64))).toBeVisible()
})
