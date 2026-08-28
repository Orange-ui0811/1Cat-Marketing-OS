export type RoleKey = 'product' | 'brand' | 'ceo' | 'rd' | 'sales' | 'tech'

export type ViewKey = 'tasks' | 'collaboration' | 'objects' | 'reviews' | 'holds' | 'daily' | 'agent_config' | 'diagnostics'

export type AgentKey = 'MO' | 'PMA' | 'BGA'

export type ThreadStatus = 'draft' | 'awaiting_plan' | 'active' | 'HOLD' | 'awaiting_human' | 'ended' | 'terminated'

export type AssignmentStatus = 'awaiting_accept' | 'working' | 'submitted' | 'blocked' | 'waiting_change' | 'cancelled'

export type DecisionKind = 'approve' | 'return' | 'HOLD' | 'takeover'

export type DecisionStatus = 'pending' | 'approved' | 'returned' | 'HOLD' | 'takeover' | 'terminated'

export type TraceKind =
  | 'instruction'
  | 'plan'
  | 'plan_confirmed'
  | 'assignment'
  | 'message'
  | 'state'
  | 'result'
  | 'change_request'
  | 'aggregation'
  | 'decision'

export type AttachmentMeta = {
  id: string
  name: string
  type: string
  size: number
}

export type BusinessObjectRef = {
  id: string
  type: 'Fact' | 'Claim' | 'Campaign' | 'Content' | 'Decision'
  title: string
  version: string
  status: 'draft' | 'verified' | 'blocked' | 'approved'
}

export type ConversationMessage = {
  id: string
  channel: AgentKey
  sender: 'human' | 'agent' | 'system'
  actor: string
  body: string
  createdAt: string
  attachments?: AttachmentMeta[]
  relatedAssignmentId?: string
  intent?: 'conversation' | 'instruction' | 'result' | 'change_request'
}

export type PlanStep = {
  id: string
  owner: AgentKey | 'human'
  title: string
  deliverable: string
  acceptance: string
}

export type PlanHumanDraft = {
  objective: string
  scope: string
  acceptance: string[]
  priority: 'P0' | 'P1' | 'P2'
  deadline: string
  requiredEvidence: string
  deliverables: string
  agents: Array<'PMA' | 'BGA'>
  publishBoundary: string
  note: string
  updatedAt: string
  updatedBy: string
}

export type PlanVersion = {
  id: string
  version: number
  summary: string
  boundary: string
  createdAt: string
  confirmedAt?: string
  status: 'proposed' | 'confirmed' | 'superseded' | 'returned'
  steps: PlanStep[]
  changeSummary?: string
  humanDraft?: PlanHumanDraft
  diff?: string[]
}

export type AgentAssignment = {
  id: string
  agent: Exclude<AgentKey, 'MO'>
  title: string
  sourceInstruction: string
  deliverable: string
  boundary: string
  status: AssignmentStatus
  currentAction: string
  dueLabel: string
  evidence: string[]
  gaps: string[]
  startedAt?: string
  deadline?: string
  dependsOn?: string[]
  escalationTo?: string
}

export type ChangeRequest = {
  id: string
  assignmentId: string
  requestedBy: string
  summary: string
  impact: string
  status: 'pending_mo' | 'awaiting_human' | 'accepted' | 'rejected'
  createdAt: string
}

export type TraceEvent = {
  id: string
  kind: TraceKind
  actor: string
  title: string
  detail: string
  createdAt: string
}

export type HumanDecision = {
  id: string
  title: string
  reason: string
  status: DecisionStatus
  createdAt: string
  resolvedAt?: string
  note?: string
  route?: 'next_gate' | 'approve_object' | 'end_round'
}

export type CollaborationThread = {
  id: string
  code: string
  title: string
  objective: string
  acceptance: string[]
  status: ThreadStatus
  priority: 'P0' | 'P1' | 'P2'
  createdAt: string
  updatedAt: string
  currentOwner: string
  nextStep: string
  gate?: 'G0' | 'G1' | 'G2' | 'G3' | 'G4' | 'G5'
  unread: number
  messages: ConversationMessage[]
  plans: PlanVersion[]
  assignments: AgentAssignment[]
  changeRequests: ChangeRequest[]
  decisions: HumanDecision[]
  objects: BusinessObjectRef[]
  trace: TraceEvent[]
}

export type ConfigStatus = 'published' | 'draft' | 'validated' | 'invalid'

export type SixPackKey = 'role_manifest' | 'soul' | 'skill_pack' | 'memory_policy' | 'daily_operation' | 'evaluation'

export type SixPackResource = {
  key: SixPackKey
  name: string
  version: string
  source: string
  summary: string
  status: 'ready' | 'missing' | 'warning'
}

export type AgentSkillBinding = {
  id: string
  name: string
  version: string
  source: string
  capability: string
  enabled: boolean
  permissions: string[]
  status: 'ready' | 'warning' | 'blocked'
}

export type AgentModelConfig = {
  provider: string
  model: string
  endpointAlias: string
  credentialRef: string
  credentialStatus: 'available' | 'missing' | 'expired'
  reasoningLevel: 'low' | 'medium' | 'high'
  maxTurns: number
  timeoutSeconds: number
}

export type AgentPermissionConfig = {
  network: boolean
  terminal: boolean
  browser: boolean
  otherAgents: boolean
  memoryWrite: boolean
  tools: string[]
}

export type AgentProfileConfig = {
  id: string
  agent: AgentKey
  profileName: string
  roleName: string
  profileVersion: number
  status: ConfigStatus
  model: AgentModelConfig
  sixPack: SixPackResource[]
  skills: AgentSkillBinding[]
  permissions: AgentPermissionConfig
  memorySummary: string
  lastValidatedAt?: string
  updatedAt: string
  updatedBy: string
}

export type AgentConfigHistory = {
  id: string
  agent: AgentKey
  version: number
  createdAt: string
  summary: string
  config: AgentProfileConfig
}

export type AppState = {
  schemaVersion: 2
  role: RoleKey
  view: ViewKey
  activeThreadId: string
  activeChannel: AgentKey
  threads: CollaborationThread[]
  agentConfigs: AgentProfileConfig[]
  agentConfigHistory: AgentConfigHistory[]
}
