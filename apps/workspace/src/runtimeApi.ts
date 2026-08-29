const TOKEN_KEY = '1cat_runtime_token'
const ACTIVE_RUN_KEY = '1cat_runtime_active_run'
const ACTIVE_CASE_KEY = '1cat_runtime_active_case'

export type Commitment = {
  id: string
  title: string
  status: string
  proposed_role: string
  objective: string
  version: number
  created_at: string
  updated_at: string
}

export type RunAttempt = {
  id: string
  run_id: string
  attempt_no: number
  status: string
  worker_id: string
  lease_until: string
  heartbeat_at: string
  hermes_run_id?: string | null
  output: Record<string, unknown>
  failure: Record<string, unknown>
  failure_class?: string | null
  retryability: string
  started_at?: string | null
  completed_at?: string | null
}

export type AgentRun = {
  id: string
  commitment_id: string
  role_id: string
  profile_id: string
  profile_version?: number | null
  profile_snapshot?: Record<string, unknown>
  execution_mode?: 'synthetic' | 'real' | null
  case_id?: string | null
  stage_key?: string | null
  status: string
  correlation_id: string
  traceparent?: string | null
  tracestate?: string | null
  trace_id?: string | null
  current_attempt_id?: string | null
  current_attempt?: RunAttempt | null
  cancellation_requested_at?: string | null
  started_at?: string | null
  completed_at?: string | null
  output: Record<string, unknown>
  failure: Record<string, unknown>
  created_at: string
}

export type RunTransition = {
  id: string
  run_id: string
  attempt_id?: string | null
  from_status: string
  to_status: string
  reason: string
  actor: string
  correlation_id: string
  created_at: string
}

export type RuntimeModel = {
  provider: string
  model: string
  mode: string
  execution_enabled: boolean
  credential_location: string
}

export type MarketingCaseStage = {
  id: string
  case_id: string
  step_key: string
  ordinal: number
  status: 'pending' | 'ready' | 'running' | 'awaiting_human' | 'completed' | 'blocked'
  commitment_id?: string | null
  active_run_id?: string | null
  input: Record<string, unknown>
  output: Record<string, unknown>
  failure: Record<string, unknown>
  started_at?: string | null
  completed_at?: string | null
}

export type MarketingCaseResource = {
  id: string
  case_id: string
  step_id?: string | null
  resource_type: 'knowledge' | 'commitment' | 'run' | 'handoff' | 'approval' | 'manual_task' | 'lead' | 'sales_feedback' | 'deliverable'
  resource_id: string
  resource_version?: number | null
  relation: string
  resource: Record<string, any> | null
  created_at: string
}

export type MarketingCaseAction = { action: string; label: string }

export type MarketingCaseMessage = {
  id: string
  case_id: string
  stage_key?: string | null
  channel: 'MO' | 'PMA' | 'BGA'
  sender_type: 'human' | 'agent' | 'system'
  intent: 'message' | 'change_request' | 'decision_note'
  body: string
  attachments: Array<Record<string, unknown>>
  created_by: string
  created_at: string
}

export type MarketingDecision = {
  id: string
  case_id: string
  stage_key: string
  decision: string
  reason: string
  subject_refs: Array<{ type: string; id: string; version?: number; kind?: string }>
  metadata: Record<string, unknown>
  actor_id: string
  created_at: string
}

export type MarketingReconciliation = {
  id: string
  case_id: string
  step_id: string
  run_id?: string | null
  attempt_id?: string | null
  resolution: string
  note: string
  evidence: Record<string, unknown>
  actor_id: string
  created_at: string
}

export type MarketingBoundary = {
  publishing: 'simulated'
  external_effect: false
  pii: false
  business_outcome_claimed: false
}

export type MarketingDeliverableSection = {
  key: string
  title: string
  content: string
  source_refs: Array<{ type: string; id: string; version?: number | null; kind?: string }>
}

export type MarketingDeliverable = {
  id: string
  case_id: string
  title: string
  status: 'draft' | 'accepted'
  format_version: string
  document: {
    sections: MarketingDeliverableSection[]
    evidence_index: Array<{ type: string; id: string; version?: number | null; relation: string }>
    boundary: MarketingBoundary
  }
  markdown: string
  source_refs: Array<{ type: string; id: string; version?: number | null; kind?: string }>
  version: number
  accepted_by?: string | null
  accepted_at?: string | null
  created_at: string
  updated_at: string
}

export type MarketingDeliverableRevision = {
  id: string
  deliverable_id: string
  case_id: string
  version_no: number
  status: 'draft' | 'accepted'
  document: MarketingDeliverable['document']
  markdown: string
  source_refs: MarketingDeliverable['source_refs']
  content_hash: string
  created_by: string
  created_at: string
}

export type MarketingCase = {
  id: string
  title: string
  objective: string
  target_platform: string
  execution_mode: 'synthetic' | 'real'
  status: string
  current_stage: string
  correlation_id: string
  version: number
  created_at: string
  updated_at: string
  stages: MarketingCaseStage[]
  resources: MarketingCaseResource[]
  final_deliverable?: MarketingDeliverable | null
  deliverable_history: MarketingDeliverableRevision[]
  messages: MarketingCaseMessage[]
  decisions: MarketingDecision[]
  reconciliations: MarketingReconciliation[]
  next_actions: MarketingCaseAction[]
  boundary: MarketingBoundary
}

export type AgentProfileRevision = {
  id: string
  agent_key: 'MO' | 'PMA' | 'BGA'
  version_no: number
  status: 'draft' | 'validated' | 'published'
  config: Record<string, any>
  summary: string
  created_by: string
  created_at: string
}

export type AgentProfile = {
  id: string
  agent_key: 'MO' | 'PMA' | 'BGA'
  status: 'draft' | 'validated' | 'published'
  published_version: number
  config: Record<string, any>
  updated_by: string
  version: number
  updated_at: string
  revisions: AgentProfileRevision[]
}

export type LocalModelStatus = {
  available: boolean
  provider: string
  model: string
  mode: string
  credential_configured: boolean
  execution_enabled: boolean
  operation_in_progress: boolean
  message?: string
  detail?: string
  model_test_passed?: boolean
}

export class RuntimeApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
  }
}

export const runtimeSession = {
  hasToken: () => Boolean(sessionStorage.getItem(TOKEN_KEY)),
  activeRunId: () => sessionStorage.getItem(ACTIVE_RUN_KEY),
  rememberRun: (runId: string) => sessionStorage.setItem(ACTIVE_RUN_KEY, runId),
  forgetRun: () => sessionStorage.removeItem(ACTIVE_RUN_KEY),
  activeCaseId: () => sessionStorage.getItem(ACTIVE_CASE_KEY),
  rememberCase: (caseId: string) => sessionStorage.setItem(ACTIVE_CASE_KEY, caseId),
  forgetCase: () => sessionStorage.removeItem(ACTIVE_CASE_KEY),
  clear: () => {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(ACTIVE_RUN_KEY)
    sessionStorage.removeItem(ACTIVE_CASE_KEY)
  },
}

function requestId(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`
}

async function request<T>(path: string, options: RequestInit = {}, write = false): Promise<T> {
  const headers = new Headers(options.headers)
  const token = sessionStorage.getItem(TOKEN_KEY)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof URLSearchParams)) headers.set('Content-Type', 'application/json')
  if (write) {
    const id = requestId('demo1')
    headers.set('X-Correlation-ID', id)
    headers.set('Idempotency-Key', id)
  }
  let response: Response
  try {
    response = await fetch(path, { ...options, headers })
  } catch {
    throw new RuntimeApiError('无法连接 Runtime API，已保留最后一次可信状态。', 0)
  }
  if (response.status === 401) {
    runtimeSession.clear()
    throw new RuntimeApiError('登录已失效，请重新登录。', 401)
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: string }
    throw new RuntimeApiError(payload.detail || `Runtime API 返回 ${response.status}`, response.status)
  }
  return response.json() as Promise<T>
}

export const runtimeApi = {
  async login(username: string, password: string) {
    const body = new URLSearchParams({
      grant_type: 'password',
      client_id: '1cat-workspace',
      username,
      password,
    })
    const response = await fetch('/auth/realms/1cat/protocol/openid-connect/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    if (!response.ok) throw new RuntimeApiError('用户名或密码不正确。', response.status)
    const payload = await response.json() as { access_token: string }
    sessionStorage.setItem(TOKEN_KEY, payload.access_token)
  },
  ready: () => request<{ status: string; database: string }>('/health/ready'),
  getRuntimeModel: () => request<RuntimeModel>('/v1/runtime-model'),
  listCommitments: () => request<Commitment[]>('/v1/commitments'),
  listRuns: () => request<AgentRun[]>('/v1/runs'),
  createCommitment: (input: { title: string; objective: string }) => request<Commitment>('/v1/commitments', {
    method: 'POST',
    body: JSON.stringify({
      title: input.title,
      proposed_role: 'DROLE-01',
      objective: input.objective,
      acceptance: { human_confirmation_required: true },
      dependencies: [],
      context: { source: 'demo1-api-mode', pii: false },
    }),
  }, true),
  transitionCommitment: (id: string, status: string, reason: string) => request<Commitment>(
    `/v1/commitments/${id}/transition`,
    { method: 'POST', body: JSON.stringify({ status, reason }) },
    true,
  ),
  createRun: (commitmentId: string, input: string) => request<AgentRun>('/v1/runs', {
    method: 'POST',
    body: JSON.stringify({ commitment_id: commitmentId, role_id: 'DROLE-01', input, context_version: 1 }),
  }, true),
  getRun: (id: string) => request<AgentRun>(`/v1/runs/${id}`),
  getAttempts: (id: string) => request<RunAttempt[]>(`/v1/runs/${id}/attempts`),
  getTimeline: (id: string) => request<RunTransition[]>(`/v1/runs/${id}/timeline`),
  cancelRun: (id: string) => request<AgentRun>(`/v1/runs/${id}/cancel`, { method: 'POST' }, true),
  listMarketingCases: (query = '') => request<MarketingCase[]>(`/v1/marketing-cases?limit=100${query ? `&${query}` : ''}`),
  getMarketingCase: (id: string) => request<MarketingCase>(`/v1/marketing-cases/${id}`),
  createMarketingCase: (input: {
    title: string
    objective: string
    brief_body: string
    source_refs: string[]
    target_platform: string
    execution_mode: 'synthetic' | 'real'
  }) => request<MarketingCase>('/v1/marketing-cases', {
    method: 'POST', body: JSON.stringify(input),
  }, true),
  commandMarketingCase: (item: MarketingCase, action: string, payload: Record<string, unknown> = {}) =>
    request<MarketingCase>(`/v1/marketing-cases/${item.id}/commands`, {
      method: 'POST',
      headers: { 'If-Match': String(item.version) },
      body: JSON.stringify({ action, payload }),
    }, true),
  createMarketingCaseMessage: (item: MarketingCase, input: {
    channel: 'MO' | 'PMA' | 'BGA'; body: string; intent?: 'message' | 'change_request' | 'decision_note'; attachments?: Array<Record<string, unknown>>
  }) => request<MarketingCase>(`/v1/marketing-cases/${item.id}/messages`, {
    method: 'POST', body: JSON.stringify(input),
  }, true),
  listAgentConfigs: () => request<AgentProfile[]>('/v1/agent-configs'),
  updateAgentConfig: (item: AgentProfile, config: Record<string, unknown>, summary: string) => request<AgentProfile>(`/v1/agent-configs/${item.agent_key}`, {
    method: 'PUT', headers: { 'If-Match': String(item.version) }, body: JSON.stringify({ config, summary }),
  }, true),
  commandAgentConfig: (item: AgentProfile, action: 'validate' | 'publish' | 'rollback', version?: number) => request<AgentProfile>(`/v1/agent-configs/${item.agent_key}/commands`, {
    method: 'POST', headers: { 'If-Match': String(item.version) }, body: JSON.stringify({ action, version, summary: action === 'rollback' ? `恢复历史版本 ${version}` : `执行 ${action}` }),
  }, true),
}

async function localModelRequest(options: RequestInit = {}): Promise<LocalModelStatus> {
  let response: Response
  try {
    response = await fetch('/local-admin/model-config', {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    })
  } catch {
    throw new RuntimeApiError('本机模型配置服务不可用，请确认 1Cat 后端已经启动。', 0)
  }
  const payload = await response.json().catch(() => ({})) as Partial<LocalModelStatus>
  if (!response.ok) {
    const message = [payload.message, payload.detail].filter(Boolean).join(' ')
    throw new RuntimeApiError(message || '模型配置失败。', response.status)
  }
  return payload as LocalModelStatus
}

export const localModelAdmin = {
  status: () => localModelRequest(),
  configure: (apiKey?: string) => localModelRequest({
    method: 'POST',
    body: JSON.stringify(apiKey ? { api_key: apiKey } : {}),
  }),
  test: () => localModelRequest({
    method: 'POST',
    body: JSON.stringify({ action: 'test' }),
  }),
}
