import { createContext, useContext, useEffect, useMemo, useReducer, type ReactNode } from 'react'
import { createDemoState, roleCopy } from './demoData'
import type {
  AgentAssignment,
  AgentProfileConfig,
  AgentKey,
  AppState,
  AttachmentMeta,
  CollaborationThread,
  ConversationMessage,
  DecisionKind,
  HumanDecision,
  PlanHumanDraft,
  PlanVersion,
  RoleKey,
  TraceEvent,
  ViewKey,
} from './types'

const STORAGE_KEY = 's2-marketing-demo1:v2'

type Action =
  | { type: 'SET_VIEW'; view: ViewKey }
  | { type: 'SET_ROLE'; role: RoleKey }
  | { type: 'OPEN_THREAD'; threadId: string; channel?: AgentKey }
  | { type: 'SET_CHANNEL'; channel: AgentKey }
  | { type: 'CREATE_THREAD' }
  | { type: 'DELETE_DRAFT'; threadId: string }
  | { type: 'TERMINATE_THREAD'; threadId: string; reason: string }
  | { type: 'SEND_MESSAGE'; threadId: string; channel: AgentKey; body: string; attachments: AttachmentMeta[]; requestChange: boolean }
  | { type: 'SAVE_PLAN_DRAFT'; threadId: string; planId: string; draft: PlanHumanDraft }
  | { type: 'REPLAN_WITH_HUMAN_INPUT'; threadId: string; planId: string; draft: PlanHumanDraft }
  | { type: 'CONFIRM_PLAN'; threadId: string }
  | { type: 'RETURN_PLAN'; threadId: string }
  | { type: 'SIMULATE_RESULT'; threadId: string; assignmentId: string }
  | { type: 'DECIDE'; threadId: string; decision: DecisionKind; note: string; route?: HumanDecisionRoute }
  | { type: 'RESUME_THREAD'; threadId: string }
  | { type: 'IMPORT_DEMO'; state: AppState }
  | { type: 'UPDATE_AGENT_CONFIG'; config: AgentProfileConfig }
  | { type: 'VALIDATE_AGENT_CONFIG'; agent: AgentKey }
  | { type: 'PUBLISH_AGENT_CONFIG'; agent: AgentKey }
  | { type: 'ROLLBACK_AGENT_CONFIG'; agent: AgentKey; historyId: string }
  | { type: 'RESET_DEMO' }

type StoreValue = {
  state: AppState
  activeThread?: CollaborationThread
  setView: (view: ViewKey) => void
  setRole: (role: RoleKey) => void
  openThread: (threadId: string, channel?: AgentKey) => void
  setChannel: (channel: AgentKey) => void
  createThread: () => void
  deleteDraft: (threadId: string) => void
  terminateThread: (threadId: string, reason: string) => void
  sendMessage: (threadId: string, channel: AgentKey, body: string, attachments?: AttachmentMeta[], requestChange?: boolean) => void
  savePlanDraft: (threadId: string, planId: string, draft: PlanHumanDraft) => void
  replanWithHumanInput: (threadId: string, planId: string, draft: PlanHumanDraft) => void
  confirmPlan: (threadId: string) => void
  returnPlan: (threadId: string) => void
  simulateResult: (threadId: string, assignmentId: string) => void
  decide: (threadId: string, decision: DecisionKind, note: string, route?: HumanDecisionRoute) => void
  resumeThread: (threadId: string) => void
  importDemo: (state: AppState) => void
  updateAgentConfig: (config: AgentProfileConfig) => void
  validateAgentConfig: (agent: AgentKey) => void
  publishAgentConfig: (agent: AgentKey) => void
  rollbackAgentConfig: (agent: AgentKey, historyId: string) => void
  resetDemo: () => void
}

type HumanDecisionRoute = 'next_gate' | 'approve_object' | 'end_round'

const StoreContext = createContext<StoreValue | null>(null)

function id(prefix: string) {
  const suffix = typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID().slice(0, 8)
    : Math.random().toString(36).slice(2, 10)
  return `${prefix}-${suffix}`
}

function now() {
  return new Date().toISOString()
}

function trace(kind: TraceEvent['kind'], actor: string, title: string, detail: string): TraceEvent {
  return { id: id('trace'), kind, actor, title, detail, createdAt: now() }
}

function message(channel: AgentKey, sender: ConversationMessage['sender'], actor: string, body: string, intent: ConversationMessage['intent'] = 'conversation'): ConversationMessage {
  return { id: id('message'), channel, sender, actor, body, createdAt: now(), intent }
}

function pendingDecision(title: string, reason: string): HumanDecision {
  return { id: id('decision'), title, reason, status: 'pending', createdAt: now() }
}

function planDecision(plan: PlanVersion): HumanDecision {
  return pendingDecision(`确认 Plan v${plan.version}`, 'MO 已形成新的工作计划；确认后才会创建或更新岗位任务。')
}

function hasSubstantialChange(text: string) {
  const patterns = ['调整目标', '改变目标', '修改目标', '扩大范围', '缩小范围', '改范围', '提前', '延期', '截止', '交付物', '改交付', '证据标准', '无需证据', '直接发布', '自动发布', '批准边界', '预算', '增加渠道']
  return patterns.some(pattern => text.includes(pattern))
}

function createHumanDraft(thread: CollaborationThread, actor: string): PlanHumanDraft {
  return {
    objective: thread.objective,
    scope: '只处理当前营销目标；不补充未经确认的外部事实。',
    acceptance: thread.acceptance,
    priority: thread.priority,
    deadline: '无真实截止时间',
    requiredEvidence: thread.objects.length ? thread.objects.map(object => `${object.type} ${object.version}`).join('、') : '由岗位任务列出证据缺口',
    deliverables: 'Fact / Claim 边界、内容候选、Review Packet',
    agents: ['PMA', 'BGA'],
    publishBoundary: 'MANUAL：不自动发布、不投放、不形成销售承诺。',
    note: '',
    updatedAt: now(),
    updatedBy: actor,
  }
}

function createDefaultPlan(thread: CollaborationThread, changeSummary?: string): PlanVersion {
  const version = Math.max(0, ...thread.plans.map(plan => plan.version)) + 1
  const humanDraft = createHumanDraft(thread, 'Marketing Orchestrator')
  return {
    id: id('plan'),
    version,
    summary: changeSummary
      ? '根据岗位侧变更请求，重新确认产品证据与内容交付边界。'
      : '先由 PMA 核对事实与表达，再由 BGA 形成内容候选；MO 汇总后提交人工决策。',
    boundary: '本演示不联网、不发布、不投放；Agent 只提交候选和证据缺口，最终判断由人类责任人完成。',
    createdAt: now(),
    status: 'proposed',
    changeSummary,
    humanDraft,
    diff: changeSummary ? ['恢复原因或任务边界发生变化', '旧岗位任务不会自动沿用'] : [],
    steps: [
      { id: id('step'), owner: 'PMA', title: '核对产品事实与表达', deliverable: 'Fact / Claim 边界与表达候选', acceptance: '每项表达都有来源或清晰的证据缺口' },
      { id: id('step'), owner: 'BGA', title: '形成渠道内容候选', deliverable: '内容草案、风险与人工发布检查表', acceptance: '使用已批准表达，不触发真实平台动作' },
      { id: id('step'), owner: 'MO', title: '聚合岗位结果', deliverable: 'Review Packet', acceptance: '列出证据、分歧、缺口、建议与下一责任人' },
    ],
  }
}

function planFromHumanDraft(thread: CollaborationThread, draft: PlanHumanDraft, previous: PlanVersion): PlanVersion {
  const version = Math.max(0, ...thread.plans.map(plan => plan.version)) + 1
  const agentSteps = draft.agents.map(agent => ({
    id: id('step'),
    owner: agent,
    title: agent === 'PMA' ? '核对事实与表达' : '形成内容候选',
    deliverable: agent === 'PMA' ? 'Fact / Claim 边界' : draft.deliverables,
    acceptance: draft.acceptance.join('；'),
  }))
  const diff = [
    draft.objective !== thread.objective ? '目标已修改' : '',
    draft.priority !== thread.priority ? `优先级 ${thread.priority} → ${draft.priority}` : '',
    `参与岗位：${draft.agents.join(' + ') || '仅 MO'}`,
    `期限：${draft.deadline}`,
    draft.note ? `人工意见：${draft.note}` : '',
  ].filter(Boolean)
  return {
    id: id('plan'), version,
    summary: '按人类修订的业务约束重新拆解岗位任务。',
    boundary: `${draft.scope} ${draft.publishBoundary}`,
    createdAt: now(), status: 'proposed',
    changeSummary: draft.note || `基于 Plan v${previous.version} 的人工修订`,
    humanDraft: { ...draft, updatedAt: now() },
    diff,
    steps: [
      ...agentSteps,
      { id: id('step'), owner: 'MO', title: '聚合与提交决策', deliverable: 'Review Packet', acceptance: '列出证据、缺口、风险与下一责任人' },
    ],
  }
}

function assignmentFromPlan(thread: CollaborationThread, plan: PlanVersion, agent: 'PMA' | 'BGA'): AgentAssignment {
  const step = plan.steps.find(item => item.owner === agent)!
  return {
    id: id(`assignment-${agent.toLowerCase()}`),
    agent,
    title: step.title,
    sourceInstruction: thread.objective,
    deliverable: step.deliverable,
    boundary: plan.boundary,
    status: 'working',
    currentAction: agent === 'PMA' ? '核对输入事实与可用表达' : '等待事实边界并搭建内容结构',
    dueLabel: plan.humanDraft?.deadline ?? '演示任务 · 无真实截止时间',
    evidence: [],
    gaps: agent === 'PMA' ? ['尚未绑定正式 Fact 版本'] : ['等待 PMA 提交可用表达'],
    startedAt: now(),
    deadline: plan.humanDraft?.deadline,
    dependsOn: agent === 'BGA' && plan.humanDraft?.agents.includes('PMA') ? ['PMA 可用表达'] : [],
    escalationTo: 'Marketing Orchestrator',
  }
}

function updateThread(state: AppState, threadId: string, updater: (thread: CollaborationThread) => CollaborationThread): AppState {
  return {
    ...state,
    threads: state.threads.map(thread => thread.id === threadId ? updater(thread) : thread),
  }
}

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_VIEW':
      return { ...state, view: action.view }
    case 'SET_ROLE':
      return { ...state, role: action.role }
    case 'SET_CHANNEL':
      return { ...state, activeChannel: action.channel }
    case 'OPEN_THREAD':
      return {
        ...state,
        view: 'collaboration',
        activeThreadId: action.threadId,
        activeChannel: action.channel ?? 'MO',
        threads: state.threads.map(thread => thread.id === action.threadId ? { ...thread, unread: 0 } : thread),
      }
    case 'CREATE_THREAD': {
      const createdAt = now()
      const threadId = id('thread')
      const thread: CollaborationThread = {
        id: threadId,
        code: `OBJ-${String(state.threads.length + 44).padStart(3, '0')}`,
        title: '未命名营销目标',
        objective: '等待你向 MO 说明目标、资料与问题。',
        acceptance: ['由 MO 复述目标并提出可确认的工作计划'],
        status: 'draft',
        priority: 'P1',
        createdAt,
        updatedAt: createdAt,
        currentOwner: `${roleCopy[state.role].label}（你）`,
        nextStep: '在 MO 主线程中说明新目标；PMA / BGA 不能直接创建无关任务',
        unread: 0,
        messages: [message('MO', 'agent', 'Marketing Orchestrator', '请说明这次营销目标、已知事实、限制条件和你希望得到的交付物。我会先复述目标与边界，再提出 Plan，未经确认不会分派岗位任务。')],
        plans: [], assignments: [], changeRequests: [],
        decisions: [pendingDecision('提交目标草稿给 MO', '目标尚未提交；可以继续说明目标，也可以直接删除草稿。')],
        objects: [],
        trace: [trace('state', '协作控制面', '创建目标草稿', '新目标已进入 MO 主线程，尚未形成业务任务。')],
      }
      return { ...state, view: 'collaboration', activeThreadId: threadId, activeChannel: 'MO', threads: [thread, ...state.threads] }
    }
    case 'DELETE_DRAFT': {
      const target = state.threads.find(thread => thread.id === action.threadId)
      if (!target || target.status !== 'draft') return state
      const threads = state.threads.filter(thread => thread.id !== action.threadId)
      return {
        ...state,
        threads,
        activeThreadId: state.activeThreadId === action.threadId ? (threads[0]?.id ?? '') : state.activeThreadId,
        activeChannel: state.activeThreadId === action.threadId ? 'MO' : state.activeChannel,
      }
    }
    case 'TERMINATE_THREAD':
      return updateThread(state, action.threadId, thread => {
        const reason = action.reason.trim()
        if (!reason || ['draft', 'ended', 'terminated'].includes(thread.status)) return thread
        const terminatedAt = now()
        return {
          ...thread,
          status: 'terminated',
          updatedAt: terminatedAt,
          currentOwner: '流程已终止',
          nextStep: '无后续动作；协作记录与事件链仅供追溯',
          plans: thread.plans.map(plan => plan.status === 'proposed' ? { ...plan, status: 'returned' as const } : plan),
          assignments: thread.assignments.map(item => ({ ...item, status: 'cancelled' as const, currentAction: '目标已终止，岗位任务停止' })),
          decisions: [
            ...thread.decisions.map(item => item.status === 'pending' ? { ...item, status: 'returned' as const, resolvedAt: terminatedAt, note: '目标已终止' } : item),
            { id: id('decision'), title: '终止目标', reason, status: 'terminated', createdAt: terminatedAt, resolvedAt: terminatedAt, note: reason },
          ],
          messages: [
            ...thread.messages,
            message('MO', 'human', roleCopy[state.role].label, `终止目标：${reason}`),
            message('MO', 'system', '协作控制面', '目标已终止。所有 PMA / BGA 岗位任务均已停止，现有记录继续保留用于追溯。'),
          ],
          trace: [...thread.trace, trace('state', roleCopy[state.role].label, '终止目标', `${reason}；所有岗位任务已停止。`)],
        }
      })
    case 'SEND_MESSAGE':
      return updateThread(state, action.threadId, thread => {
        const createdAt = now()
        const humanMessage: ConversationMessage = {
          id: id('message'), channel: action.channel, sender: 'human', actor: roleCopy[state.role].label,
          body: action.body, createdAt, attachments: action.attachments, intent: thread.status === 'draft' ? 'instruction' : 'conversation',
        }
        const baseMessages = [...thread.messages, humanMessage]
        const attachmentDetail = action.attachments.length ? `；附带 ${action.attachments.length} 个文件元数据` : ''

        if (action.channel === 'MO' && thread.status === 'draft') {
          const plan = createDefaultPlan(thread)
          const titleText = action.body.replace(/\s+/g, ' ').slice(0, 26)
          const moReply = message('MO', 'agent', 'Marketing Orchestrator', `我把目标复述为：${action.body}\n\n建议 Plan v${plan.version}：PMA 先锁定事实和表达边界，BGA 在该边界内形成内容候选，我负责聚合并把需要判断的事项交还给你。请先确认或退回计划。`)
          const submittedAt = now()
          return {
            ...thread,
            title: titleText || thread.title,
            objective: action.body,
            status: 'awaiting_plan',
            updatedAt: createdAt,
            currentOwner: `${roleCopy[state.role].label}（你）`,
            nextStep: `确认或退回 Plan v${plan.version}`,
            messages: [...baseMessages, moReply],
            plans: [...thread.plans, plan],
            decisions: [
              ...thread.decisions.map(item => item.status === 'pending' ? { ...item, status: 'approved' as const, resolvedAt: submittedAt, note: '目标已提交给 MO' } : item),
              planDecision(plan),
            ],
            trace: [
              ...thread.trace,
              trace('instruction', roleCopy[state.role].label, '向 MO 下达新目标', `${action.body.slice(0, 90)}${attachmentDetail}`),
              trace('plan', 'MO', `提出 Plan v${plan.version}`, plan.summary),
            ],
          }
        }

        if (action.channel === 'MO') {
          const moReply = message('MO', 'agent', 'Marketing Orchestrator', thread.status === 'HOLD'
            ? '我已记录补充信息。当前任务仍为 HOLD；恢复前需要明确缺失证据是否已补齐，或由责任人调整目标与验收标准。'
            : '我已记录这条指令，并把它绑定到当前目标。它不会直接改变岗位任务；若涉及范围或交付变化，我会先形成计划差异供你确认。')
          return {
            ...thread, updatedAt: createdAt, messages: [...baseMessages, moReply],
            trace: [...thread.trace, trace('message', roleCopy[state.role].label, '在 MO 主线程补充信息', `${action.body.slice(0, 90)}${attachmentDetail}`)],
          }
        }

        const assignment = thread.assignments.find(item => item.agent === action.channel && !['cancelled'].includes(item.status))
        if (!assignment) {
          return {
            ...thread, updatedAt: createdAt,
            messages: [...baseMessages, message(action.channel, 'system', '协作控制面', '当前没有分派给该岗位的有效任务。请先回到 MO 主线程确认计划。')],
            trace: [...thread.trace, trace('message', roleCopy[state.role].label, `尝试联系 ${action.channel}`, '因没有有效岗位任务，未创建新任务。')],
          }
        }

        if (action.requestChange) {
          const changeId = id('change')
          const changeSummary = action.body.slice(0, 120)
          const plan = createDefaultPlan(thread, changeSummary)
          return {
            ...thread,
            status: 'awaiting_plan',
            updatedAt: createdAt,
            currentOwner: `${roleCopy[state.role].label}（你）`,
            nextStep: `确认 MO 根据变更请求形成的 Plan v${plan.version}`,
            messages: [
              ...baseMessages,
              message(action.channel, 'agent', action.channel === 'PMA' ? 'Product Marketing Agent' : 'Brand & Growth Agent', '这条指令会改变目标、范围、期限或交付边界。我不会自行改写岗位任务，已将它升级为 Change Request 交给 MO。', 'change_request'),
              message('MO', 'agent', 'Marketing Orchestrator', `${action.channel} 子线程出现任务变更请求：${changeSummary}\n\n我已暂停受影响岗位任务并形成 Plan v${plan.version}。请查看计划差异并确认；确认前不会继续下游执行。`, 'change_request'),
            ],
            plans: [...thread.plans, plan],
            decisions: [...thread.decisions, planDecision(plan)],
            assignments: thread.assignments.map(item => item.id === assignment.id ? { ...item, status: 'waiting_change', currentAction: '等待 MO 重规划与人类确认' } : item),
            changeRequests: [...thread.changeRequests, { id: changeId, assignmentId: assignment.id, requestedBy: roleCopy[state.role].label, summary: changeSummary, impact: '可能改变岗位交付物或下游任务，需 MO 重规划。', status: 'awaiting_human', createdAt }],
            trace: [
              ...thread.trace,
              trace('change_request', roleCopy[state.role].label, `${action.channel} 子线程提出任务变更`, changeSummary),
              trace('plan', 'MO', `提出 Plan v${plan.version}`, '基于岗位侧变更请求重新规划。'),
            ],
          }
        }

        if (hasSubstantialChange(action.body)) {
          return {
            ...thread, updatedAt: createdAt,
            messages: [...baseMessages, message(action.channel, 'agent', action.channel === 'PMA' ? 'Product Marketing Agent' : 'Brand & Growth Agent', '这条消息可能改变任务边界。我暂不修改任务；如需生效，请切换为“任务变更”后重新提交。')],
            trace: [...thread.trace, trace('message', roleCopy[state.role].label, `在 ${action.channel} 提出潜在变更`, '保持普通沟通，未改变计划或岗位状态。')],
          }
        }

        const specialistReply = action.channel === 'PMA'
          ? '已收到补充信息。我会在原任务边界内更新事实核对与表达候选；如果资料不能支持 Claim，我会继续标记证据缺口。'
          : '已收到补充信息。我会在现有 Campaign 与交付边界内调整内容候选；发布、投放和新增渠道仍需回到 MO 与人类审批。'
        return {
          ...thread, updatedAt: createdAt,
          messages: [...baseMessages, message(action.channel, 'agent', action.channel === 'PMA' ? 'Product Marketing Agent' : 'Brand & Growth Agent', specialistReply)],
          trace: [...thread.trace, trace('message', roleCopy[state.role].label, `在 ${action.channel} 岗位子线程沟通`, `${action.body.slice(0, 90)}${attachmentDetail}`)],
        }
      })
    case 'SAVE_PLAN_DRAFT':
      return updateThread(state, action.threadId, thread => ({
        ...thread,
        updatedAt: now(),
        nextStep: '人工修订草稿已保存；交给 MO 重排后才能确认恢复或执行',
        plans: thread.plans.map(plan => plan.id === action.planId ? { ...plan, humanDraft: { ...action.draft, updatedAt: now(), updatedBy: roleCopy[state.role].label } } : plan),
        trace: [...thread.trace, trace('message', roleCopy[state.role].label, '保存计划人工草稿', action.draft.note || '更新业务目标、验收或边界。')],
      }))
    case 'REPLAN_WITH_HUMAN_INPUT':
      return updateThread(state, action.threadId, thread => {
        const previous = thread.plans.find(plan => plan.id === action.planId)
        if (!previous) return thread
        const draft = { ...action.draft, updatedAt: now(), updatedBy: roleCopy[state.role].label }
        const nextPlan = planFromHumanDraft(thread, draft, previous)
        const replannedAt = now()
        return {
          ...thread,
          objective: draft.objective,
          acceptance: draft.acceptance,
          priority: draft.priority,
          status: 'awaiting_plan',
          updatedAt: now(),
          currentOwner: `${roleCopy[state.role].label}（你）`,
          nextStep: `确认 MO 重排后的 Plan v${nextPlan.version}`,
          plans: [...thread.plans.map(plan => plan.id === previous.id ? { ...plan, status: 'superseded' as const, humanDraft: draft } : plan), nextPlan],
          decisions: [
            ...thread.decisions.map(item => item.status === 'pending' ? { ...item, status: 'returned' as const, resolvedAt: replannedAt, note: '已由人工计划修订替代' } : item),
            planDecision(nextPlan),
          ],
          messages: [
            ...thread.messages,
            message('MO', 'human', roleCopy[state.role].label, `我已修订业务约束：${draft.note || '请按编辑后的目标、验收与边界重排。'}`),
            message('MO', 'agent', 'Marketing Orchestrator', `已形成 Plan v${nextPlan.version}。变更重点：${nextPlan.diff?.join('；')}。请确认后再创建岗位任务。`),
          ],
          trace: [
            ...thread.trace,
            trace('message', roleCopy[state.role].label, '提交人工计划修订', draft.note || '更新业务约束。'),
            trace('plan', 'MO', `形成 Plan v${nextPlan.version}`, nextPlan.diff?.join('；') || nextPlan.summary),
          ],
        }
      })
    case 'CONFIRM_PLAN':
      return updateThread(state, action.threadId, thread => {
        const proposed = [...thread.plans].reverse().find(plan => plan.status === 'proposed')
        if (!proposed) return thread
        const confirmedAt = now()
        const selectedAgents = proposed.humanDraft?.agents ?? (['PMA', 'BGA'] as const)
        const assignments = selectedAgents.map(agent => assignmentFromPlan(thread, proposed, agent))
        const planDecisionId = [...thread.decisions].reverse().find(item => item.status === 'pending' && item.title.includes(`Plan v${proposed.version}`))?.id
        const generatedObjects = [
          ...(selectedAgents.includes('PMA') && !thread.objects.some(object => object.type === 'Claim') ? [{ id: id('claim'), type: 'Claim' as const, title: '产品事实与可用表达', version: 'v0.1', status: 'draft' as const }] : []),
          ...(selectedAgents.includes('BGA') && !thread.objects.some(object => object.type === 'Campaign') ? [{ id: id('campaign'), type: 'Campaign' as const, title: '营销执行计划', version: 'v0.1', status: 'draft' as const }] : []),
          ...(selectedAgents.includes('BGA') && !thread.objects.some(object => object.type === 'Content') ? [{ id: id('content'), type: 'Content' as const, title: '内容候选与发布包', version: 'v0.1', status: 'draft' as const }] : []),
        ]
        return {
          ...thread,
          status: 'active', updatedAt: confirmedAt, currentOwner: 'Marketing Orchestrator',
          nextStep: 'PMA 与 BGA 并行执行；当前无需人类处理', unread: 0,
          plans: thread.plans.map(plan => plan.id === proposed.id ? { ...plan, status: 'confirmed', confirmedAt } : plan),
          assignments: [...thread.assignments.map(item => item.status === 'waiting_change' ? { ...item, status: 'cancelled' as const, currentAction: '由新计划版本替代' } : item), ...assignments],
          objects: [...thread.objects, ...generatedObjects],
          decisions: thread.decisions.map(item => item.id === planDecisionId ? { ...item, status: 'approved' as const, resolvedAt: confirmedAt, note: `确认 Plan v${proposed.version}` } : item),
          changeRequests: thread.changeRequests.map(item => item.status === 'awaiting_human' ? { ...item, status: 'accepted' as const } : item),
          messages: [...thread.messages, message('MO', 'system', '协作控制面', `Plan v${proposed.version} 已确认。MO 已创建 PMA 与 BGA 两项独立岗位任务，执行结果将先回到 MO 聚合。`)],
          trace: [
            ...thread.trace,
            trace('plan_confirmed', roleCopy[state.role].label, `确认 Plan v${proposed.version}`, '批准当前计划版本与任务边界。'),
            trace('assignment', 'MO', '分派 PMA / BGA 岗位任务', '两项任务进入 working，互不共享隐藏推理。'),
          ],
        }
      })
    case 'RETURN_PLAN':
      return updateThread(state, action.threadId, thread => {
        const proposed = [...thread.plans].reverse().find(plan => plan.status === 'proposed')
        if (!proposed) return thread
        const revised = createDefaultPlan({ ...thread, plans: thread.plans.map(plan => plan.id === proposed.id ? { ...plan, status: 'returned' as const } : plan) }, '人类责任人退回上一版计划，要求收紧范围并明确验收。')
        const returnedAt = now()
        const planDecisionId = [...thread.decisions].reverse().find(item => item.status === 'pending' && item.title.includes(`Plan v${proposed.version}`))?.id
        return {
          ...thread, status: 'awaiting_plan', updatedAt: now(), currentOwner: `${roleCopy[state.role].label}（你）`,
          nextStep: `查看并确认 MO 修订后的 Plan v${revised.version}`,
          plans: [...thread.plans.map(plan => plan.id === proposed.id ? { ...plan, status: 'returned' as const } : plan), revised],
          decisions: [
            ...thread.decisions.map(item => item.id === planDecisionId ? { ...item, status: 'returned' as const, resolvedAt: returnedAt, note: '退回 MO 修订' } : item),
            planDecision(revised),
          ],
          messages: [...thread.messages, message('MO', 'human', roleCopy[state.role].label, `退回 Plan v${proposed.version}，请收紧范围并明确验收标准。`), message('MO', 'agent', 'Marketing Orchestrator', `已按退回意见形成 Plan v${revised.version}：保留双岗位分工，但强化事实来源、发布边界与 Review Packet 验收。请再次确认。`)],
          trace: [...thread.trace, trace('decision', roleCopy[state.role].label, `退回 Plan v${proposed.version}`, '要求 MO 修订后再次提交确认。'), trace('plan', 'MO', `提出 Plan v${revised.version}`, revised.summary)],
        }
      })
    case 'SIMULATE_RESULT':
      return updateThread(state, action.threadId, thread => {
        const target = thread.assignments.find(item => item.id === action.assignmentId)
        if (!target || target.status !== 'working') return thread
        const assignments = thread.assignments.map(item => item.id === target.id ? {
          ...item,
          status: 'submitted' as const,
          currentAction: '结果已提交 MO，等待聚合',
          evidence: [...item.evidence, `${target.agent} 演示结果包 v1`],
          gaps: item.gaps.filter((_, index) => index !== 0),
        } : item)
        const currentPlanAssignments = assignments.filter(item => item.status !== 'cancelled')
        const allSubmitted = currentPlanAssignments.length > 0 && currentPlanAssignments.every(item => item.status === 'submitted')
        const agentName = target.agent === 'PMA' ? 'Product Marketing Agent' : 'Brand & Growth Agent'
        const resultBody = target.agent === 'PMA'
          ? '岗位结果已提交：已区分可用事实、表达候选和证据缺口。未经证实的强 Claim 保持阻塞，详细结果已交给 MO。'
          : '岗位结果已提交：已形成内容草案、风险清单和 MANUAL 发布检查项。未执行任何外部发布动作，详细结果已交给 MO。'
        const messages = [...thread.messages, message(target.agent, 'agent', agentName, resultBody, 'result')]
        const decisions = [...thread.decisions]
        if (allSubmitted) {
          messages.push(message('MO', 'agent', 'Marketing Orchestrator', 'PMA 与 BGA 已全部提交。我已聚合为 Review Packet：包含候选结果、证据、缺口和风险。现在需要人类责任人批准、退回、HOLD 或接管。', 'result'))
          if (!decisions.some(item => item.status === 'pending')) {
            decisions.push({ id: id('decision'), title: '审核 MO 聚合后的 Review Packet', reason: '岗位任务已完成，但业务结果仍需人类责任人判断。', status: 'pending', createdAt: now() })
          }
        } else {
          messages.push(message('MO', 'agent', 'Marketing Orchestrator', `${target.agent} 已提交结果，我已登记证据与缺口。另一项岗位任务仍在执行，暂不生成最终 Review Packet。`))
        }
        return {
          ...thread,
          status: allSubmitted ? 'awaiting_human' : 'active',
          updatedAt: now(),
          currentOwner: allSubmitted ? `${roleCopy[state.role].label}（你）` : 'Marketing Orchestrator',
          nextStep: allSubmitted ? '审核 MO 聚合结果并做业务决策' : '等待另一岗位提交结果',
          assignments, messages, decisions,
          trace: [...thread.trace, trace('result', target.agent, `提交 ${target.title}`, '结果、证据和缺口已回传 MO。'), ...(allSubmitted ? [trace('aggregation', 'MO', '生成 Review Packet', '岗位结果已聚合，等待人类业务决策。')] : [])],
        }
      })
    case 'DECIDE':
      return updateThread(state, action.threadId, thread => {
        const decidedAt = now()
        const pendingDecisionId = [...thread.decisions].reverse().find(item => item.status === 'pending')?.id
        const statusMap = { approve: 'approved', return: 'returned', HOLD: 'HOLD', takeover: 'takeover' } as const
        const labelMap = { approve: '批准', return: '退回', HOLD: 'HOLD', takeover: '人工接管' }
        const route = action.route ?? 'next_gate'
        const approvedToNextGate = action.decision === 'approve' && route !== 'end_round'
        const nextPlan = approvedToNextGate ? createDefaultPlan(thread, route === 'approve_object' ? '当前对象版本已批准，下一阶段仍需重新确认任务边界。' : '当前 Gate 已批准，准备进入下一 Gate。') : undefined
        const nextStatus = approvedToNextGate ? 'awaiting_plan' : action.decision === 'approve' ? 'ended' : action.decision === 'return' ? 'active' : 'HOLD'
        const nextOwner = approvedToNextGate ? `${roleCopy[state.role].label}（你）` : action.decision === 'return' ? 'Marketing Orchestrator' : action.decision === 'approve' ? '流程已结束' : `${roleCopy[state.role].label}（你）`
        const nextStep = approvedToNextGate && nextPlan ? `确认下一 Gate 的 Plan v${nextPlan.version}` : action.decision === 'return' ? 'MO 根据退回理由安排补充' : action.decision === 'approve' ? '本轮结束；真实发布仍保持 MANUAL' : action.decision === 'takeover' ? '由人类继续处理，Agent 停止推进' : '等待人类恢复或取消'
        return {
          ...thread, status: nextStatus, updatedAt: decidedAt, currentOwner: nextOwner, nextStep,
          plans: nextPlan ? [...thread.plans, nextPlan] : thread.plans,
          decisions: [
            ...thread.decisions.map(item => item.id === pendingDecisionId ? { ...item, status: statusMap[action.decision], resolvedAt: decidedAt, note: action.note, route: action.route } : item),
            ...(nextPlan ? [planDecision(nextPlan)] : []),
          ],
          assignments: thread.assignments.map(item => action.decision === 'return' && item.status === 'submitted' ? { ...item, status: 'waiting_change' as const, currentAction: '等待 MO 明确补充项' } : action.decision === 'takeover' && item.status === 'working' ? { ...item, status: 'cancelled' as const, currentAction: '已转人工接管' } : item),
          messages: [...thread.messages, message('MO', 'human', roleCopy[state.role].label, `${labelMap[action.decision]}：${action.note}`, 'conversation'), message('MO', 'agent', 'Marketing Orchestrator', `决策已记录。${nextStep}`)],
          trace: [...thread.trace, trace('decision', roleCopy[state.role].label, labelMap[action.decision], `${action.note}；${nextStep}`), ...(nextPlan ? [trace('plan', 'MO', `提出 Plan v${nextPlan.version}`, nextPlan.summary)] : [])],
        }
      })
    case 'RESUME_THREAD':
      return updateThread(state, action.threadId, thread => {
        const basePlan = createDefaultPlan(thread, '恢复 HOLD 前，由人类修订业务约束。')
        const plan = { ...basePlan, humanDraft: { ...basePlan.humanDraft!, updatedBy: roleCopy[state.role].label, note: '请补充恢复原因、证据变化和新的验收要求。' } }
        return {
          ...thread, status: 'awaiting_plan', updatedAt: now(), currentOwner: `${roleCopy[state.role].label}（你）`, nextStep: `参与修订恢复计划 Plan v${plan.version}`,
          plans: [...thread.plans, plan],
          decisions: [...thread.decisions, planDecision(plan)],
          messages: [...thread.messages, message('MO', 'human', roleCopy[state.role].label, '申请恢复当前 HOLD。'), message('MO', 'agent', 'Marketing Orchestrator', `恢复草案 Plan v${plan.version} 已建立。请先修改目标、证据、交付与边界，我再重排岗位任务。`)],
          trace: [...thread.trace, trace('state', roleCopy[state.role].label, '申请恢复 HOLD', '进入人工与 MO 共同修订。'), trace('plan', 'MO', `建立恢复草案 v${plan.version}`, plan.summary)],
        }
      })
    case 'UPDATE_AGENT_CONFIG':
      return {
        ...state,
        agentConfigs: state.agentConfigs.map(config => config.agent === action.config.agent ? {
          ...action.config, status: 'draft', updatedAt: now(), updatedBy: roleCopy[state.role].label,
        } : config),
      }
    case 'VALIDATE_AGENT_CONFIG':
      return {
        ...state,
        agentConfigs: state.agentConfigs.map(config => {
          if (config.agent !== action.agent) return config
          const valid = Boolean(config.profileName && config.model.model && config.model.credentialRef)
            && config.model.credentialStatus === 'available'
            && config.sixPack.length === 6
            && config.sixPack.every(item => item.status !== 'missing')
            && config.skills.filter(item => item.enabled).length > 0
          return { ...config, status: valid ? 'validated' : 'invalid', lastValidatedAt: now(), updatedAt: now(), updatedBy: roleCopy[state.role].label }
        }),
      }
    case 'PUBLISH_AGENT_CONFIG': {
      const current = state.agentConfigs.find(config => config.agent === action.agent)
      if (!current || current.status !== 'validated') return state
      const published = { ...current, profileVersion: current.profileVersion + 1, status: 'published' as const, updatedAt: now(), updatedBy: roleCopy[state.role].label }
      return {
        ...state,
        agentConfigs: state.agentConfigs.map(config => config.agent === action.agent ? published : config),
        agentConfigHistory: [...state.agentConfigHistory, {
          id: id(`history-${action.agent.toLowerCase()}`), agent: action.agent, version: published.profileVersion,
          createdAt: published.updatedAt, summary: `发布 ${published.profileName} v${published.profileVersion}`, config: structuredClone(published),
        }],
      }
    }
    case 'ROLLBACK_AGENT_CONFIG': {
      const snapshot = state.agentConfigHistory.find(item => item.id === action.historyId && item.agent === action.agent)
      const current = state.agentConfigs.find(config => config.agent === action.agent)
      if (!snapshot || !current) return state
      const restored = { ...structuredClone(snapshot.config), profileVersion: current.profileVersion, status: 'draft' as const, updatedAt: now(), updatedBy: roleCopy[state.role].label }
      return { ...state, agentConfigs: state.agentConfigs.map(config => config.agent === action.agent ? restored : config) }
    }
    case 'RESET_DEMO':
      return createDemoState()
    case 'IMPORT_DEMO':
      if (action.state.schemaVersion !== 2 || !Array.isArray(action.state.threads)) return state
      return {
        ...action.state,
        agentConfigs: action.state.agentConfigs ?? createDemoState().agentConfigs,
        agentConfigHistory: action.state.agentConfigHistory ?? createDemoState().agentConfigHistory,
      }
    default:
      return state
  }
}

function loadInitialState(): AppState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return createDemoState()
    const parsed = JSON.parse(raw) as AppState
    if (parsed.schemaVersion !== 2 || !Array.isArray(parsed.threads)) return createDemoState()
    const defaults = createDemoState()
    return {
      ...parsed,
      agentConfigs: parsed.agentConfigs ?? defaults.agentConfigs,
      agentConfigHistory: parsed.agentConfigHistory ?? defaults.agentConfigHistory,
    }
  } catch {
    return createDemoState()
  }
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, loadInitialState)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }, [state])

  const value = useMemo<StoreValue>(() => ({
    state,
    activeThread: state.threads.find(thread => thread.id === state.activeThreadId),
    setView: view => dispatch({ type: 'SET_VIEW', view }),
    setRole: role => dispatch({ type: 'SET_ROLE', role }),
    openThread: (threadId, channel) => dispatch({ type: 'OPEN_THREAD', threadId, channel }),
    setChannel: channel => dispatch({ type: 'SET_CHANNEL', channel }),
    createThread: () => dispatch({ type: 'CREATE_THREAD' }),
    deleteDraft: threadId => dispatch({ type: 'DELETE_DRAFT', threadId }),
    terminateThread: (threadId, reason) => dispatch({ type: 'TERMINATE_THREAD', threadId, reason }),
    sendMessage: (threadId, channel, body, attachments = [], requestChange = false) => dispatch({ type: 'SEND_MESSAGE', threadId, channel, body, attachments, requestChange }),
    savePlanDraft: (threadId, planId, draft) => dispatch({ type: 'SAVE_PLAN_DRAFT', threadId, planId, draft }),
    replanWithHumanInput: (threadId, planId, draft) => dispatch({ type: 'REPLAN_WITH_HUMAN_INPUT', threadId, planId, draft }),
    confirmPlan: threadId => dispatch({ type: 'CONFIRM_PLAN', threadId }),
    returnPlan: threadId => dispatch({ type: 'RETURN_PLAN', threadId }),
    simulateResult: (threadId, assignmentId) => dispatch({ type: 'SIMULATE_RESULT', threadId, assignmentId }),
    decide: (threadId, decision, note, route) => dispatch({ type: 'DECIDE', threadId, decision, note, route }),
    resumeThread: threadId => dispatch({ type: 'RESUME_THREAD', threadId }),
    importDemo: importedState => dispatch({ type: 'IMPORT_DEMO', state: importedState }),
    updateAgentConfig: config => dispatch({ type: 'UPDATE_AGENT_CONFIG', config }),
    validateAgentConfig: agent => dispatch({ type: 'VALIDATE_AGENT_CONFIG', agent }),
    publishAgentConfig: agent => dispatch({ type: 'PUBLISH_AGENT_CONFIG', agent }),
    rollbackAgentConfig: (agent, historyId) => dispatch({ type: 'ROLLBACK_AGENT_CONFIG', agent, historyId }),
    resetDemo: () => dispatch({ type: 'RESET_DEMO' }),
  }), [state])

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}

export function useStore() {
  const value = useContext(StoreContext)
  if (!value) throw new Error('useStore must be used inside StoreProvider')
  return value
}
