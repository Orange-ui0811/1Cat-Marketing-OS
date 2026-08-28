import type { AgentConfigHistory, AgentKey, AgentProfileConfig, AppState, CollaborationThread, RoleKey, SixPackResource } from './types'

export const roleCopy: Record<RoleKey, { label: string; short: string; responsibility: string; boundary: string }> = {
  product: {
    label: '产品营销负责人',
    short: '产品营销',
    responsibility: '确认产品商业语境、定位表达和产品资产是否可用；处理 MO 汇总后需要你判断的事项。',
    boundary: '你不替代 R&D 确认技术事实，也不直接管理 Brand & Growth Agent 的新目标。',
  },
  brand: {
    label: '品牌营销负责人',
    short: '品牌营销',
    responsibility: '确认 Campaign、品牌表达、内容白名单和人工发布边界；对增长复盘作最终业务判断。',
    boundary: '你不替代销售承诺成交，也不让 Agent 自动发布或投放。',
  },
  ceo: {
    label: '公司负责人',
    short: '经营责任',
    responsibility: '设定目标、批准关键定位与预算，并对经营结果承担最终责任。',
    boundary: '当前前端版本只展示责任入口，完整经营操作将在后续版本接入。',
  },
  rd: {
    label: '产品 / R&D',
    short: '事实权威',
    responsibility: '确认产品事实、证据版本和技术限制。',
    boundary: '当前前端版本只展示事实确认入口，完整操作将在后续版本接入。',
  },
  sales: {
    label: '销售负责人',
    short: '销售反馈',
    responsibility: '回传有效询盘、商机、报价和成交结果。',
    boundary: '当前前端版本只展示反馈入口，完整操作将在后续版本接入。',
  },
  tech: {
    label: '技术管理员',
    short: '运行保障',
    responsibility: '维护模型、连接器、权限和审计可用性。',
    boundary: '当前前端版本只展示运行诊断入口，业务决策仍由人类责任人完成。',
  },
}

const productFactThread: CollaborationThread = {
  id: 'thread-product-fact',
  code: 'OBJ-042',
  title: '低噪运行事实核对与表达边界',
  objective: '为匿名 AI 任务平台形成一组可用于内容策划的产品事实与安全表达，不使用行业排名或普遍性能保证。',
  acceptance: ['只使用已给定的 1 卡 / 4 卡运行数据', '明确证据缺口与不可发布 Claim', '形成可供 BGA 使用的产品表达包'],
  status: 'awaiting_human',
  priority: 'P0',
  createdAt: '2026-08-13T09:12:00+08:00',
  updatedAt: '2026-08-14T09:46:00+08:00',
  currentOwner: '产品营销负责人（你）',
  nextStep: '审核 PMA 的 Fact / Claim 边界，批准后交给 MO 继续路由',
  unread: 2,
  messages: [
    {
      id: 'm-pf-01', channel: 'MO', sender: 'human', actor: '产品营销负责人',
      body: '请基于现有测试资料形成一份可营销的产品事实包。不得补充外部事实，也不要把单次测试写成普遍性能结论。',
      createdAt: '2026-08-13T09:12:00+08:00', intent: 'instruction',
    },
    {
      id: 'm-pf-02', channel: 'MO', sender: 'agent', actor: 'Marketing Orchestrator',
      body: '我理解的目标是：先锁定可验证事实，再形成安全表达候选。本轮不做发布，也不判断技术事实真伪。\n\n我建议由 PMA 核对事实与 Claim 边界，BGA 暂不启动；待你批准产品表达包后，再进入内容任务。',
      createdAt: '2026-08-13T09:14:00+08:00', intent: 'conversation',
    },
    {
      id: 'm-pf-03', channel: 'MO', sender: 'system', actor: '协作控制面',
      body: 'Plan v1 已于 09:18 获得确认。MO 已创建 PMA 岗位任务 PMA-117。',
      createdAt: '2026-08-13T09:18:00+08:00', intent: 'conversation',
    },
    {
      id: 'm-pf-04', channel: 'PMA', sender: 'agent', actor: 'Product Marketing Agent',
      body: '我已按任务边界完成核对。可确认的只是两条具体观测：1 张 GPU 用时 20 分钟；4 张 GPU 用时 14 分钟。\n\n“性能提升 4 倍”与数据不一致；“行业最快”“所有任务都能提速”均缺少证据，应保持阻塞。建议表达为：在本次任务与配置下，运行时间从 20 分钟缩短到 14 分钟。',
      createdAt: '2026-08-14T09:31:00+08:00', relatedAssignmentId: 'a-pma-117', intent: 'result',
    },
    {
      id: 'm-pf-05', channel: 'MO', sender: 'agent', actor: 'Marketing Orchestrator',
      body: 'PMA 已提交结果。我汇总后的判断是：事实边界清楚，可形成“单次观测型”表达；三项强 Claim 继续阻塞。现在需要你批准这组边界，或退回补充证据。',
      createdAt: '2026-08-14T09:46:00+08:00', intent: 'conversation',
    },
  ],
  plans: [
    {
      id: 'plan-pf-v1', version: 1, summary: '先核对产品事实和 Claim，再决定是否启动内容生产。',
      boundary: '无外部检索、无真实客户案例、无发布动作；R&D 仍是产品事实最终权威。',
      createdAt: '2026-08-13T09:14:00+08:00', confirmedAt: '2026-08-13T09:18:00+08:00', status: 'confirmed',
      steps: [
        { id: 'step-pf-1', owner: 'PMA', title: '核对产品事实与 Claim', deliverable: 'Fact / Claim 边界表', acceptance: '每条表达均能回溯到输入事实或明确标记缺口' },
        { id: 'step-pf-2', owner: 'MO', title: '汇总并发起人工审核', deliverable: 'Review Packet', acceptance: '不替代人类做最终批准' },
      ],
    },
  ],
  assignments: [
    {
      id: 'a-pma-117', agent: 'PMA', title: '产品事实与 Claim 边界核对',
      sourceInstruction: '形成可营销的产品事实包，不补充外部事实，不把单次测试写成普遍结论。',
      deliverable: 'Fact / Claim 边界表 + 安全替代表达', boundary: '不得联网；不得虚构客户、排名或普遍性能保证。',
      status: 'submitted', currentAction: '结果已由 MO 汇总，等待产品营销负责人审核', dueLabel: '已提交 · 09:31',
      evidence: ['输入资料：1 GPU / 20 分钟', '输入资料：4 GPU / 14 分钟', 'PMA 结果包 v1'],
      gaps: ['缺少跨任务重复测试', '缺少行业基准', '缺少客户授权案例'],
    },
  ],
  changeRequests: [],
  decisions: [
    { id: 'decision-pf-1', title: '批准 Fact / Claim 边界', reason: 'PMA 已提交，MO 已完成聚合；需要人类责任人决定是否进入内容阶段。', status: 'pending', createdAt: '2026-08-14T09:46:00+08:00' },
  ],
  objects: [
    { id: 'fact-17', type: 'Fact', title: '单次 GPU 运行观测', version: 'v1.2', status: 'verified' },
    { id: 'claim-08', type: 'Claim', title: '性能提升表达边界', version: 'v0.4', status: 'blocked' },
  ],
  trace: [
    { id: 'tr-pf-1', kind: 'instruction', actor: '产品营销负责人', title: '下达营销目标', detail: '要求形成产品事实包，并明确禁止外部补充与普遍化表达。', createdAt: '2026-08-13T09:12:00+08:00' },
    { id: 'tr-pf-2', kind: 'plan', actor: 'MO', title: '提出 Plan v1', detail: '先由 PMA 核对事实和 Claim，BGA 暂不启动。', createdAt: '2026-08-13T09:14:00+08:00' },
    { id: 'tr-pf-3', kind: 'plan_confirmed', actor: '产品营销负责人', title: '确认 Plan v1', detail: '批准任务分解与工作边界。', createdAt: '2026-08-13T09:18:00+08:00' },
    { id: 'tr-pf-4', kind: 'assignment', actor: 'MO', title: '分派 PMA-117', detail: 'Fact / Claim 边界核对。', createdAt: '2026-08-13T09:19:00+08:00' },
    { id: 'tr-pf-5', kind: 'result', actor: 'PMA', title: '提交结果包', detail: '确认单次观测表达，阻塞三项强 Claim。', createdAt: '2026-08-14T09:31:00+08:00' },
    { id: 'tr-pf-6', kind: 'aggregation', actor: 'MO', title: '形成 Review Packet', detail: '汇总证据、缺口和安全表达，提交人工审核。', createdAt: '2026-08-14T09:46:00+08:00' },
  ],
}

const bilibiliThread: CollaborationThread = {
  id: 'thread-bilibili-campaign',
  code: 'OBJ-043',
  title: 'B 站产品解释视频与发布准备',
  objective: '把已批准的产品事实组织成一支 90 秒 B 站视频草案，重点解释“为什么 4 卡不是 4 倍提速”。',
  acceptance: ['脚本引用批准后的 Fact 版本', '包含标题、开场、结构、画面提示和 CTA', '发布保持 MANUAL，不触发平台连接器'],
  status: 'active',
  priority: 'P1',
  createdAt: '2026-08-13T14:20:00+08:00',
  updatedAt: '2026-08-14T10:18:00+08:00',
  currentOwner: 'Brand & Growth Agent',
  nextStep: 'BGA 完成脚本草案并提交 MO；PMA 同步校验引用的产品表达',
  unread: 1,
  messages: [
    { id: 'm-bi-01', channel: 'MO', sender: 'human', actor: '品牌营销负责人', body: '请围绕“GPU 数量与真实任务耗时的关系”策划一支 B 站解释视频。先做草案，不发布。', createdAt: '2026-08-13T14:20:00+08:00', intent: 'instruction' },
    { id: 'm-bi-02', channel: 'MO', sender: 'agent', actor: 'Marketing Orchestrator', body: '我会把任务拆成两条并行线：PMA 校验可用事实和表达，BGA 设计内容结构与发布准备。二者都只提交候选，最终由你审核。', createdAt: '2026-08-13T14:23:00+08:00' },
    { id: 'm-bi-03', channel: 'PMA', sender: 'agent', actor: 'Product Marketing Agent', body: '已接收任务。当前只允许引用 Fact v1.2 中的单次观测，不允许出现“线性加速”“4 倍性能”等表达。', createdAt: '2026-08-13T14:31:00+08:00', relatedAssignmentId: 'a-pma-118' },
    { id: 'm-bi-04', channel: 'BGA', sender: 'agent', actor: 'Brand & Growth Agent', body: '已接收任务。内容将用“更多 GPU 为什么不等于等比例变快”作为认知钩子，90 秒内完成问题—数据—原因—边界—CTA 的结构。当前不调用发布工具。', createdAt: '2026-08-13T14:34:00+08:00', relatedAssignmentId: 'a-bga-206' },
    { id: 'm-bi-05', channel: 'MO', sender: 'agent', actor: 'Marketing Orchestrator', body: '两项岗位任务正在并行。BGA 已锁定内容骨架，PMA 正在校验可引用措辞。当前没有需要你处理的事项。', createdAt: '2026-08-14T10:18:00+08:00' },
  ],
  plans: [
    {
      id: 'plan-bi-v1', version: 1, summary: 'PMA 与 BGA 并行工作，MO 汇总后再进入品牌审核。',
      boundary: '不联网、不调用 B 站接口、不做真实投放；所有性能表达引用已批准 Fact。',
      createdAt: '2026-08-13T14:23:00+08:00', confirmedAt: '2026-08-13T14:27:00+08:00', status: 'confirmed',
      steps: [
        { id: 'step-bi-1', owner: 'PMA', title: '校验内容可用事实', deliverable: '可引用表达清单', acceptance: '与 Fact v1.2 一致' },
        { id: 'step-bi-2', owner: 'BGA', title: '形成 B 站视频草案', deliverable: '90 秒脚本与画面提示', acceptance: '结构完整且保持 MANUAL 发布' },
        { id: 'step-bi-3', owner: 'MO', title: '聚合并提交品牌审核', deliverable: 'Content Review Packet', acceptance: '明确证据、风险与下一步' },
      ],
    },
  ],
  assignments: [
    {
      id: 'a-pma-118', agent: 'PMA', title: '校验 B 站脚本可用事实', sourceInstruction: '围绕 GPU 数量与真实任务耗时，校验脚本可以使用的产品事实。',
      deliverable: '可引用表达清单 + 禁用表达清单', boundary: '只读 Fact v1.2；不修改产品事实；不创建内容。',
      status: 'working', currentAction: '逐句标注可引用与需改写的表达', dueLabel: '今天 14:30', evidence: ['Fact v1.2'], gaps: ['原因解释尚无 R&D 正式说明'],
    },
    {
      id: 'a-bga-206', agent: 'BGA', title: 'B 站 90 秒解释视频草案', sourceInstruction: '围绕 GPU 数量与真实任务耗时的关系策划解释视频，先做草案，不发布。',
      deliverable: '标题候选、90 秒脚本、画面提示、CTA、发布检查表', boundary: '不添加未经证实原因；不调用平台；不承诺性能。',
      status: 'working', currentAction: '编写第一版脚本并匹配画面节奏', dueLabel: '今天 16:00', evidence: ['Campaign Brief v1', 'Fact v1.2'], gaps: ['缺少产品界面录屏素材'],
    },
  ],
  changeRequests: [],
  decisions: [],
  objects: [
    { id: 'campaign-12', type: 'Campaign', title: 'GPU 真实耗时解释', version: 'v0.3', status: 'draft' },
    { id: 'content-31', type: 'Content', title: 'B 站 90 秒脚本', version: 'v0.1', status: 'draft' },
  ],
  trace: [
    { id: 'tr-bi-1', kind: 'instruction', actor: '品牌营销负责人', title: '发起 B 站内容目标', detail: '解释 GPU 数量与任务耗时，限定为草案。', createdAt: '2026-08-13T14:20:00+08:00' },
    { id: 'tr-bi-2', kind: 'plan', actor: 'MO', title: '提出双岗位并行计划', detail: 'PMA 校验事实，BGA 形成内容。', createdAt: '2026-08-13T14:23:00+08:00' },
    { id: 'tr-bi-3', kind: 'plan_confirmed', actor: '品牌营销负责人', title: '确认 Plan v1', detail: '批准两项岗位任务。', createdAt: '2026-08-13T14:27:00+08:00' },
    { id: 'tr-bi-4', kind: 'assignment', actor: 'MO', title: '并行分派 PMA / BGA', detail: '两个独立岗位任务进入 working。', createdAt: '2026-08-13T14:29:00+08:00' },
    { id: 'tr-bi-5', kind: 'state', actor: 'MO', title: '同步运行状态', detail: 'BGA 已锁定内容骨架，PMA 正在校验措辞。', createdAt: '2026-08-14T10:18:00+08:00' },
  ],
}

const holdThread: CollaborationThread = {
  id: 'thread-douyin-hold', code: 'OBJ-039', title: '抖音增长实验发布包',
  objective: '把抖音增长 Skill 的实验结果整理成演示内容，验证流程但不触发真实发布。',
  acceptance: ['只使用匿名实验结果', '显示 Skill 前后差异', '发布前必须人工白名单确认'],
  status: 'HOLD', priority: 'P1', createdAt: '2026-08-12T11:00:00+08:00', updatedAt: '2026-08-13T17:22:00+08:00',
  currentOwner: '品牌营销负责人（你）', nextStep: '补充实验盲评结果，或人工取消本轮内容任务', unread: 0,
  messages: [
    { id: 'm-dy-1', channel: 'MO', sender: 'human', actor: '品牌营销负责人', body: '把抖音 Skill A/B 实验整理成一条演示内容，但不能展示模型密钥或真实平台数据。', createdAt: '2026-08-12T11:00:00+08:00', intent: 'instruction' },
    { id: 'm-dy-2', channel: 'MO', sender: 'agent', actor: 'Marketing Orchestrator', body: '当前缺少完整盲评结论，无法证明 Skill 带来的质量提升。任务已进入 HOLD，不会进入内容白名单或发布准备。', createdAt: '2026-08-13T17:22:00+08:00' },
  ],
  plans: [], assignments: [], changeRequests: [],
  decisions: [{ id: 'decision-dy-1', title: '恢复或取消抖音实验内容任务', reason: '关键证据缺失：盲评结果尚未形成。', status: 'HOLD', createdAt: '2026-08-13T17:22:00+08:00' }],
  objects: [{ id: 'content-dy-1', type: 'Content', title: '抖音实验演示内容', version: 'v0.1', status: 'blocked' }],
  trace: [
    { id: 'tr-dy-1', kind: 'instruction', actor: '品牌营销负责人', title: '发起演示内容目标', detail: '限定匿名资料与人工发布。', createdAt: '2026-08-12T11:00:00+08:00' },
    { id: 'tr-dy-2', kind: 'state', actor: 'MO', title: '进入 HOLD', detail: '缺少盲评证据，停止后续任务创建。', createdAt: '2026-08-13T17:22:00+08:00' },
  ],
}

const sixPackTemplate: SixPackResource[] = [
  { key: 'role_manifest', name: 'Role Manifest', version: 'v1.1', source: 'profiles/shared/role-manifest.yaml', summary: '岗位使命、责任人和业务边界', status: 'ready' },
  { key: 'soul', name: 'SOUL', version: 'v1.0', source: 'profiles/shared/SOUL.md', summary: '行为原则与表达约束', status: 'ready' },
  { key: 'skill_pack', name: 'Skill Pack', version: 'v1.3', source: 'profiles/shared/skills.yaml', summary: '岗位 Skill 绑定与优先级', status: 'ready' },
  { key: 'memory_policy', name: 'Memory Policy', version: 'v0.8', source: 'profiles/shared/memory-policy.yaml', summary: '可写内容、保留范围和禁存数据', status: 'ready' },
  { key: 'daily_operation', name: 'Daily Operation', version: 'v1.0', source: 'profiles/shared/daily-operation.md', summary: '日常触发、交接和升级规则', status: 'ready' },
  { key: 'evaluation', name: 'Evaluation', version: 'v0.9', source: 'profiles/shared/evaluation.yaml', summary: '质量、安全与成本验收', status: 'ready' },
]

const skillSets: Record<Exclude<AgentKey, never>, Array<[string, string, string]>> = {
  MO: [
    ['brief-check', 'Brief 检查', '检查目标、输入与边界'], ['work-plan', '协作规划', '拆解计划与岗位任务'],
    ['commitment', 'Work Commitment', '维护承诺与状态'], ['route-escalation', '路由与升级', '处理依赖、异常与超时'],
    ['human-handoff', '人工接管', '生成接管包并停止推进'], ['growth-review', '增长复盘', '聚合结果与下一轮建议'],
  ],
  PMA: [
    ['fact-version', '事实与版本', '绑定正式 Fact 版本'], ['user-research', '用户 / 竞品研究', '形成研究证据'],
    ['position-claim', '定位与 Claim', '提出定位和安全表达'], ['product-assets', '产品资产', '形成商业化资产'],
    ['expression-review', '表达审核', '识别越界宣称'], ['rd-evidence', 'R&D 证据请求', '提出正式证据需求'],
  ],
  BGA: [
    ['channel-research', '渠道研究', '识别渠道语境与限制'], ['campaign', 'Campaign', '形成活动结构'],
    ['content-adapt', '内容适配', '生成平台内容候选'], ['publish-ready', '发布准备', '检查白名单与 MANUAL 边界'],
    ['lead-stub', 'LeadStub', '登记原始线索'], ['attribution', '归因实验', '形成增长复盘候选'],
  ],
}

function createAgentConfig(agent: AgentKey): AgentProfileConfig {
  const roleNames = { MO: 'Marketing Orchestrator', PMA: 'Product Marketing Agent', BGA: 'Brand & Growth Agent' }
  const permissionMap = {
    MO: { network: false, terminal: false, browser: false, otherAgents: true, memoryWrite: true, tools: ['OrganizationEvent', 'WorkCommitment', 'RoleHandoff'] },
    PMA: { network: false, terminal: false, browser: false, otherAgents: false, memoryWrite: true, tools: ['Fact Registry', 'Evidence Request', 'Manual Task'] },
    BGA: { network: false, terminal: false, browser: false, otherAgents: false, memoryWrite: true, tools: ['Campaign Object', 'Content Draft', 'Manual Publish'] },
  }
  return {
    id: `config-${agent.toLowerCase()}`,
    agent,
    profileName: `HRM-${agent === 'MO' ? '01' : agent === 'PMA' ? '02' : '03'}-${agent.toLowerCase()}`,
    roleName: roleNames[agent],
    profileVersion: 1,
    status: 'published',
    model: {
      provider: 'Model Gateway', model: 'deepseek-v4-pro', endpointAlias: 'gateway/default',
      credentialRef: 'secret://hermes/model-primary', credentialStatus: 'available', reasoningLevel: 'low', maxTurns: 1, timeoutSeconds: 90,
    },
    sixPack: structuredClone(sixPackTemplate).map(item => ({ ...item, source: item.source.replace('shared', agent.toLowerCase()) })),
    skills: skillSets[agent].map(([id, name, capability]) => ({ id, name, capability, version: 'v1.0', source: `skill-library/${id}`, enabled: true, permissions: ['对象只读'], status: 'ready' })),
    permissions: permissionMap[agent],
    memorySummary: agent === 'MO' ? '保存协作偏好和路由习惯；不保存正式事实或审批状态。' : '仅保存岗位偏好、术语和协作习惯。',
    lastValidatedAt: '2026-08-14T10:30:00+08:00', updatedAt: '2026-08-14T10:30:00+08:00', updatedBy: '技术管理员',
  }
}

function createAgentConfigState() {
  const agentConfigs = (['MO', 'PMA', 'BGA'] as const).map(createAgentConfig)
  const agentConfigHistory: AgentConfigHistory[] = agentConfigs.map(config => ({
    id: `history-${config.agent}-v1`, agent: config.agent, version: 1, createdAt: config.updatedAt,
    summary: '初始影子配置', config: structuredClone(config),
  }))
  return { agentConfigs, agentConfigHistory }
}

export function createDemoState(): AppState {
  const configState = createAgentConfigState()
  return {
    schemaVersion: 2,
    role: 'product',
    view: 'tasks',
    activeThreadId: productFactThread.id,
    activeChannel: 'MO',
    threads: [structuredClone(productFactThread), structuredClone(bilibiliThread), structuredClone(holdThread)],
    ...configState,
  }
}
