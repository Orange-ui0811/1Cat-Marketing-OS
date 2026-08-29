import { useEffect, useMemo, useRef, useState, type ChangeEvent, type ReactNode } from 'react'
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  BookOpenCheck,
  Bot,
  Box,
  BriefcaseBusiness,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  CircleDot,
  CirclePause,
  ClipboardCheck,
  Clock3,
  Database,
  Download,
  Edit3,
  Eye,
  FileText,
  Gauge,
  GitBranch,
  History,
  Inbox,
  LayoutDashboard,
  ListChecks,
  LockKeyhole,
  KeyRound,
  Layers3,
  Library,
  Menu,
  MessageSquareText,
  Paperclip,
  PanelRightClose,
  Plus,
  RefreshCcw,
  RotateCcw,
  Save,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  UserRound,
  UsersRound,
  Undo2,
  Wrench,
  Workflow,
  X,
} from 'lucide-react'
import { roleCopy } from './demoData'
import { localModelAdmin, RuntimeApiError, type LocalModelStatus } from './runtimeApi'
import RuntimeCaseSummary from './RuntimeCaseSummary'
import { ServerWorkspacePage } from './ServerWorkspace'
import { StoreProvider, useStore } from './store'
import type {
  AgentAssignment,
  AgentProfileConfig,
  AgentSkillBinding,
  AgentKey,
  AttachmentMeta,
  CollaborationThread,
  DecisionKind,
  PlanHumanDraft,
  RoleKey,
  ThreadStatus,
  ViewKey,
  SixPackResource,
} from './types'

const navItems: { key: ViewKey; label: string; icon: typeof LayoutDashboard }[] = [
  { key: 'tasks', label: '任务中心', icon: LayoutDashboard },
  { key: 'collaboration', label: '协作中心', icon: MessageSquareText },
  { key: 'objects', label: '业务对象', icon: Box },
  { key: 'reviews', label: '决策台账', icon: ClipboardCheck },
  { key: 'holds', label: '异常处置', icon: CirclePause },
  { key: 'daily', label: 'Daily Brief', icon: CalendarDays },
  { key: 'agent_config', label: 'Agent 配置', icon: Settings },
  { key: 'diagnostics', label: '运行诊断', icon: Gauge },
]

const roleOrder: RoleKey[] = ['product', 'brand', 'ceo', 'rd', 'sales', 'tech']

const threadStatusCopy: Record<ThreadStatus, { label: string; tone: StatusTone }> = {
  draft: { label: '目标草稿', tone: 'neutral' },
  awaiting_plan: { label: '待确认计划', tone: 'warning' },
  active: { label: 'Agent 推进中', tone: 'info' },
  HOLD: { label: 'HOLD', tone: 'danger' },
  awaiting_human: { label: '待人工决策', tone: 'warning' },
  ended: { label: '本轮已结束', tone: 'success' },
  terminated: { label: '已终止', tone: 'neutral' },
}

const agentCopy: Record<AgentKey, { short: string; full: string; description: string }> = {
  MO: { short: 'MO', full: 'Marketing Orchestrator', description: '目标澄清、计划拆解、路由、提醒与结果聚合' },
  PMA: { short: 'PMA', full: 'Product Marketing Agent', description: '产品事实、用户研究、定位与商业化表达候选' },
  BGA: { short: 'BGA', full: 'Brand & Growth Agent', description: 'Campaign、内容候选、渠道准备与增长归因' },
}

type StatusTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

function formatTime(value: string, withDate = false) {
  const date = new Date(value)
  return new Intl.DateTimeFormat('zh-CN', withDate
    ? { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }
    : { hour: '2-digit', minute: '2-digit', hour12: false }).format(date)
}

function statusLabel(status: AgentAssignment['status']) {
  const labels: Record<AgentAssignment['status'], string> = {
    awaiting_accept: '待接收', working: '执行中', submitted: '已提交 MO', blocked: '阻塞', waiting_change: '等待变更确认', cancelled: '已取消',
  }
  return labels[status]
}

function statusTone(status: AgentAssignment['status']): StatusTone {
  if (status === 'submitted') return 'success'
  if (status === 'working') return 'info'
  if (status === 'blocked' || status === 'cancelled') return 'danger'
  return 'warning'
}

function decisionStatusLabel(status: CollaborationThread['decisions'][number]['status']) {
  const labels = {
    pending: '待决定',
    approved: '已批准',
    returned: '已退回',
    HOLD: '已暂停',
    takeover: '人工接管',
    terminated: '已终止',
  } as const
  return labels[status]
}

function decisionStatusTone(status: CollaborationThread['decisions'][number]['status']): StatusTone {
  if (status === 'approved') return 'success'
  if (status === 'pending' || status === 'returned') return 'warning'
  if (status === 'HOLD') return 'danger'
  if (status === 'terminated') return 'neutral'
  return 'info'
}

function objectStatusLabel(status: CollaborationThread['objects'][number]['status']) {
  const labels = { draft: '草稿', verified: '已验证', blocked: '不可用', approved: '已确认' } as const
  return labels[status]
}

function App() {
  return (
    <StoreProvider>
      <ApplicationShell />
    </StoreProvider>
  )
}

function ApplicationShell() {
  const { state, setView, setRole, createThread, resetDemo } = useStore()
  const [mobileNav, setMobileNav] = useState(false)
  const apiMode = import.meta.env.VITE_RUNTIME_MODE === 'api'
  const [surface, setSurface] = useState<'collaboration' | 'runtime'>('collaboration')
  const pendingCount = state.threads.filter(thread => ['awaiting_plan', 'awaiting_human', 'HOLD'].includes(thread.status)).length

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get('view')
    if (navItems.some(item => item.key === requested) && requested !== state.view) setView(requested as ViewKey)
  }, [])

  function navigate(view: ViewKey) {
    setView(view)
    setMobileNav(false)
    const url = new URL(window.location.href)
    url.searchParams.set('view', view)
    window.history.replaceState({}, '', url)
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">跳到主要内容</a>
      {mobileNav && <button className="nav-scrim" aria-label="关闭导航" onClick={() => setMobileNav(false)} />}
      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <header className="brand-block">
          <div className="brand-mark" aria-hidden="true"><span>S2</span></div>
          <div>
            <strong>营销组织运行台</strong>
            <small>AI native · shadow workspace</small>
          </div>
          <button className="icon-button sidebar-close" aria-label="关闭导航" onClick={() => setMobileNav(false)}><X size={18} /></button>
        </header>

        <div className="environment-note">
          <CircleDot size={14} />
          <div><strong>前端影子演练</strong><small>无真实发布与外部调用</small></div>
        </div>

        <nav className="main-nav" aria-label="主要导航">
          <p>工作台</p>
          {navItems.map(item => {
            const Icon = item.icon
            return (
              <button key={item.key} className={state.view === item.key ? 'active' : ''} onClick={() => navigate(item.key)} aria-current={state.view === item.key ? 'page' : undefined}>
                <Icon size={18} />
                <span>{item.label}</span>
                {item.key === 'tasks' && pendingCount > 0 && <em>{pendingCount}</em>}
              </button>
            )
          })}
        </nav>

        <footer className="sidebar-footer">
          {apiMode && <button className="workflow-entry" onClick={() => setSurface(surface === 'runtime' ? 'collaboration' : 'runtime')}><Workflow size={16} /><span>{surface === 'runtime' ? '返回协作工作台' : '查看真实服务端任务'}</span></button>}
          <button onClick={createThread}><Plus size={16} /><span>向 MO 发起新目标</span></button>
          <div className="boundary-line"><LockKeyhole size={14} /><span>四平台 MANUAL · 人类最终决策</span></div>
        </footer>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="打开导航" onClick={() => setMobileNav(true)}><Menu size={20} /></button>
          <div className="topbar-path">
            <span>1Cat Marketing OS</span>
            <ChevronRight size={14} />
            <strong>{navItems.find(item => item.key === state.view)?.label}</strong>
          </div>
          <div className="topbar-actions">
            {apiMode && <div className="workspace-surface-switch" aria-label="切换工作台数据层">
              <button className={surface === 'collaboration' ? 'active' : ''} onClick={() => setSurface('collaboration')}><MessageSquareText size={14} />协作设计</button>
              <button className={surface === 'runtime' ? 'active' : ''} onClick={() => setSurface('runtime')}><Database size={14} />真实任务</button>
            </div>}
            <button className="quiet-action" onClick={resetDemo} title="恢复最初的演示会话与任务"><RotateCcw size={15} /><span>恢复演示初始数据</span></button>
            <label className="role-switcher">
              <span className="role-avatar">{roleCopy[state.role].short.slice(0, 1)}</span>
              <span><small>当前身份</small><strong>{roleCopy[state.role].label}</strong></span>
              <select value={state.role} onChange={event => setRole(event.target.value as RoleKey)} aria-label="切换当前身份">
                {roleOrder.map(role => <option key={role} value={role}>{roleCopy[role].label}</option>)}
              </select>
            </label>
          </div>
        </header>

        <main id="main-content" className={surface === 'collaboration' && state.view === 'collaboration' ? 'main-content collaboration-page' : 'main-content'}>
          {apiMode && surface === 'runtime'
            ? <ServerWorkspacePage view={state.view} navigate={navigate} />
            : <>
              <RuntimeCaseSummary view={state.view} onOpenServer={apiMode ? () => setSurface('runtime') : undefined} />
              {!['product', 'brand'].includes(state.role) && !['diagnostics', 'agent_config'].includes(state.view)
                ? <RolePlaceholder role={state.role} onDiagnostics={() => setView('diagnostics')} />
                : <CurrentView />}
            </>}
        </main>
      </div>
    </div>
  )
}

function CurrentView() {
  const { state } = useStore()
  switch (state.view) {
    case 'tasks': return <TaskCenter />
    case 'collaboration': return <CollaborationCenter />
    case 'objects': return <ObjectsView />
    case 'reviews': return <ReviewsView />
    case 'holds': return <HoldsView />
    case 'daily': return <DailyView />
    case 'agent_config': return <AgentConfigView />
    case 'diagnostics': return <DiagnosticsView />
    default: return <TaskCenter />
  }
}

function PageHeader({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  )
}

function StatusBadge({ tone = 'neutral', children }: { tone?: StatusTone; children: ReactNode }) {
  return <span className={`status-badge ${tone}`}>{children}</span>
}

function TaskCenter() {
  const { state, createThread, openThread, resumeThread } = useStore()
  const [taskScope, setTaskScope] = useState<'mine' | 'all'>('mine')
  const responsibility = roleCopy[state.role]
  const allHumanThreads = state.threads.filter(thread => ['awaiting_plan', 'awaiting_human', 'HOLD'].includes(thread.status))
  const humanThreads = taskScope === 'all' ? allHumanThreads : allHumanThreads.filter(thread => thread.currentOwner.includes(responsibility.label))
  const activeThreads = state.threads.filter(thread => thread.status === 'active')
  const latest = state.threads
    .filter(thread => !['ended', 'terminated'].includes(thread.status))
    .sort((a, b) => +new Date(b.updatedAt) - +new Date(a.updatedAt))[0]
  const latestMo = [...(latest?.messages ?? [])].reverse().find(item => item.channel === 'MO' && item.sender === 'agent')
  const workingAssignments = activeThreads.flatMap(thread => thread.assignments.filter(item => item.status === 'working').map(item => ({ thread, assignment: item })))

  return (
    <div className="page-container task-center">
      <PageHeader
        eyebrow="human responsibility desk"
        title="任务中心"
        description="只看需要你判断的事。"
        actions={<button className="primary-button" onClick={createThread}><Plus size={17} />向 MO 发起新目标</button>}
      />

      <section className="responsibility-strip" aria-labelledby="responsibility-title">
        <div className="responsibility-index">01</div>
        <div><span>我的责任 · {responsibility.short}</span><h2 id="responsibility-title">{state.role === 'product' ? '确认定位、表达与产品资产' : '确认 Campaign、内容与发布边界'}</h2><p>{responsibility.boundary}</p></div>
        <ShieldCheck size={28} aria-hidden="true" />
      </section>

      <section className="metric-ribbon compact-metrics" aria-label="工作台摘要">
        <Metric label="需要我处理" value={humanThreads.length} detail="确认、审批、HOLD 或接管" tone="warm" />
        <Metric label="Agent 推进中" value={workingAssignments.length} detail={`${activeThreads.length} 个目标处于执行阶段`} />
        <Metric label="发布权限" value="MANUAL" detail="四平台均未连接" tone="ink" />
      </section>

      <div className="task-layout">
        <section className="human-workstream">
          <SectionHeading number="02" title="现在需要我处理" meta={`${humanThreads.length} 项`} />
          <div className="scope-switch" aria-label="任务范围"><button className={taskScope === 'mine' ? 'active' : ''} onClick={() => setTaskScope('mine')}>我的责任</button><button className={taskScope === 'all' ? 'active' : ''} onClick={() => setTaskScope('all')}>组织全部</button></div>
          {humanThreads.length > 0 ? (
            <div className="human-task-list">
              {humanThreads.map(thread => (
                <HumanTaskCard key={thread.id} thread={thread} onOpen={() => openThread(thread.id)} onResume={() => { resumeThread(thread.id); openThread(thread.id) }} />
              ))}
            </div>
          ) : <EmptyState icon={<CheckCircle2 />} title="当前没有待人工事项" body="Agent 可以继续推进；新的审批、证据缺口或 HOLD 会出现在这里。" action={<button className="text-button" onClick={createThread}>发起新目标 <ArrowRight size={15} /></button>} />}
        </section>

        <aside className="recent-collaboration">
          <SectionHeading number="03" title="继续最近协作" meta="MO 主线程" />
          {latest ? (
            <article className="recent-thread-card">
              <header><div><small>{latest.code}</small><h3>{latest.title}</h3></div>{latest.unread > 0 && <span className="unread-mark">{latest.unread} 条未读</span>}</header>
              <div className="recent-message"><span className="agent-monogram mo">MO</span><div><small>{latestMo ? formatTime(latestMo.createdAt, true) : '暂无更新'}</small><p>{latestMo?.body ?? '尚无 MO 回复'}</p></div></div>
              <dl className="owner-next"><div><dt>当前责任人</dt><dd>{latest.currentOwner}</dd></div><div><dt>下一步</dt><dd>{latest.nextStep}</dd></div></dl>
              <button className="wide-link" onClick={() => openThread(latest.id)}>打开完整协作记录 <ArrowUpRight size={16} /></button>
            </article>
          ) : <EmptyState icon={<Inbox />} title="还没有协作目标" body="所有新目标都从 MO 主线程开始。" />}
        </aside>
      </div>

      <section className="agent-workstream">
        <SectionHeading number="04" title="Agent 正在推进" meta="运行可见，但不等于业务完成" />
        {workingAssignments.length > 0 ? (
          <div className="agent-progress-grid">
            {workingAssignments.map(({ thread, assignment }) => (
              <button className="agent-progress-card" key={assignment.id} onClick={() => openThread(thread.id, assignment.agent)}>
                <div className={`agent-monogram ${assignment.agent.toLowerCase()}`}>{assignment.agent}</div>
                <div><span>{thread.code} · {statusLabel(assignment.status)}</span><h3>{assignment.title}</h3><p>{assignment.currentAction}</p><small>下一责任链：{thread.nextStep}</small></div>
                <ChevronRight size={18} />
              </button>
            ))}
          </div>
        ) : <EmptyState icon={<Bot />} title="当前没有运行中的岗位任务" body="确认 MO 的计划后，PMA 与 BGA 的独立任务会显示在这里。" />}
      </section>
    </div>
  )
}

function Metric({ label, value, detail, tone = 'default' }: { label: string; value: number | string; detail: string; tone?: 'default' | 'warm' | 'ink' }) {
  return <div className={`metric-item ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
}

function SectionHeading({ number, title, meta }: { number: string; title: string; meta: string }) {
  return <header className="section-heading"><span>{number}</span><h2>{title}</h2><small>{meta}</small></header>
}

function HumanTaskCard({ thread, onOpen, onResume }: { thread: CollaborationThread; onOpen: () => void; onResume: () => void }) {
  const latestDecision = [...thread.decisions].reverse()[0]
  const submitted = thread.assignments.filter(item => item.status === 'submitted')
  const status = threadStatusCopy[thread.status]
  return (
    <article className={`human-task-card ${thread.status === 'HOLD' ? 'hold' : ''}`}>
      <header>
        <div><StatusBadge tone={status.tone}>{status.label}</StatusBadge><span className="task-code">{thread.code} · {thread.priority}</span></div>
        <time>{formatTime(thread.updatedAt, true)}</time>
      </header>
      <h3>{latestDecision?.title ?? thread.title}</h3>
      <p className="task-reason">{latestDecision?.reason ?? thread.nextStep}</p>
      <div className="task-signal"><span>{submitted.length ? `${submitted.map(item => item.agent).join('、')} 已提交` : thread.status === 'HOLD' ? '等待恢复条件' : `Plan v${thread.plans.at(-1)?.version ?? 1}`}</span><strong>{thread.nextStep}</strong></div>
      <footer>
        <button className="secondary-button" onClick={onOpen}><Eye size={15} />查看上下文</button>
        {thread.status === 'awaiting_plan' && <button className="primary-button" onClick={onOpen}>修订 / 确认计划 <ArrowRight size={15} /></button>}
        {thread.status === 'awaiting_human' && <DecisionControls thread={thread} compact />}
        {thread.status === 'HOLD' && <button className="primary-button" onClick={onResume}><Edit3 size={15} />参与恢复计划</button>}
      </footer>
    </article>
  )
}

function DecisionControls({ thread, compact = false }: { thread: CollaborationThread; compact?: boolean }) {
  const { decide } = useStore()
  const [open, setOpen] = useState(false)
  const [kind, setKind] = useState<DecisionKind>('approve')
  const [note, setNote] = useState('')
  const [route, setRoute] = useState<'next_gate' | 'approve_object' | 'end_round'>('next_gate')
  const effects: Record<DecisionKind, string> = {
    approve: route === 'end_round' ? '结束本轮，发布仍为 MANUAL。' : route === 'approve_object' ? '批准当前对象，并由 MO 准备下一阶段计划。' : '进入下一 Gate，先确认新版 Plan。',
    return: '回到 MO，岗位任务等待补充。',
    HOLD: '停止下游推进，等待恢复。',
    takeover: 'Agent 停止，人类接管。',
  }

  function submitDecision() {
    if (!note.trim()) return
    decide(thread.id, kind, note.trim(), kind === 'approve' ? route : undefined)
    setOpen(false)
    setNote('')
  }

  return <>
    <button className={compact ? 'primary-button decision-trigger' : 'primary-button'} onClick={() => setOpen(true)}><ClipboardCheck size={14} />做出决策</button>
    {open && <div className="decision-layer" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setOpen(false) }}>
      <section className="decision-dialog" role="dialog" aria-modal="true" aria-label="记录人工决策">
        <header><div><span>{thread.code}</span><h2>记录决策</h2></div><button className="icon-button" aria-label="关闭" onClick={() => setOpen(false)}><X size={17} /></button></header>
        <div className="decision-kinds">
          {([['approve', '批准'], ['return', '退回'], ['HOLD', 'HOLD'], ['takeover', '接管']] as const).map(([value, label]) => <button key={value} className={kind === value ? 'active' : ''} onClick={() => setKind(value)}>{label}</button>)}
        </div>
        {kind === 'approve' && <label><span>批准后</span><select value={route} onChange={event => setRoute(event.target.value as typeof route)}><option value="next_gate">进入下一 Gate</option><option value="approve_object">仅批准当前对象</option><option value="end_round">结束本轮</option></select></label>}
        <label><span>决策理由</span><textarea value={note} onChange={event => setNote(event.target.value)} placeholder="说明依据、保留条件或需要补充的内容" autoFocus /></label>
        <div className="decision-effect"><strong>影响</strong><span>{effects[kind]}</span></div>
        <footer><button className="secondary-button" onClick={() => setOpen(false)}>取消</button><button className="primary-button" disabled={!note.trim()} onClick={submitDecision}>确认并记录</button></footer>
      </section>
    </div>}
  </>
}

function CollaborationCenter() {
  const { state, activeThread, openThread, createThread } = useStore()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'mine' | 'active' | 'hold' | 'closed'>('all')
  const [observerOpen, setObserverOpen] = useState(false)
  const filteredThreads = state.threads.filter(thread => {
    const matchesSearch = `${thread.title}${thread.code}${thread.objective}`.toLowerCase().includes(search.toLowerCase())
    const matchesFilter = filter === 'all' || (filter === 'mine' && ['awaiting_plan', 'awaiting_human', 'HOLD'].includes(thread.status) && thread.currentOwner.includes(roleCopy[state.role].label)) || (filter === 'active' && thread.status === 'active') || (filter === 'hold' && thread.status === 'HOLD') || (filter === 'closed' && ['ended', 'terminated'].includes(thread.status))
    return matchesSearch && matchesFilter
  })

  return (
    <div className="collaboration-shell">
      <ThreadList
        threads={filteredThreads}
        activeId={activeThread?.id}
        search={search}
        filter={filter}
        onSearch={setSearch}
        onFilter={setFilter}
        onOpen={id => openThread(id)}
        onCreate={createThread}
      />
      {activeThread ? (
        <>
          <ConversationPanel thread={activeThread} onObserver={() => setObserverOpen(true)} />
          <TaskObserver thread={activeThread} open={observerOpen} onClose={() => setObserverOpen(false)} />
        </>
      ) : (
        <div className="conversation-empty"><EmptyState icon={<MessageSquareText />} title="选择一个协作目标" body="每个目标包含 MO 主线程、岗位子线程、计划版本和完整事件链。" /></div>
      )}
    </div>
  )
}

function ThreadList({ threads, activeId, search, filter, onSearch, onFilter, onOpen, onCreate }: {
  threads: CollaborationThread[]
  activeId?: string
  search: string
  filter: 'all' | 'mine' | 'active' | 'hold' | 'closed'
  onSearch: (value: string) => void
  onFilter: (value: 'all' | 'mine' | 'active' | 'hold' | 'closed') => void
  onOpen: (id: string) => void
  onCreate: () => void
}) {
  return (
    <aside className="thread-list-panel">
      <header><div><span>目标级协作</span><h1>协作中心</h1></div><button className="icon-button create-thread" aria-label="向 MO 发起新目标" title="向 MO 发起新目标" onClick={onCreate}><Plus size={18} /></button></header>
      <label className="thread-search"><Search size={15} /><input value={search} onChange={event => onSearch(event.target.value)} placeholder="搜索目标、编号或指令" /></label>
      <div className="thread-filters" role="tablist" aria-label="协作筛选">
        {([['all', '全部'], ['mine', '待我'], ['active', '推进中'], ['hold', '异常'], ['closed', '已结束']] as const).map(([key, label]) => <button key={key} className={filter === key ? 'active' : ''} onClick={() => onFilter(key)}>{label}</button>)}
      </div>
      <div className="thread-scroll">
        {threads.map(thread => {
          const status = threadStatusCopy[thread.status]
          return (
            <button key={thread.id} className={`thread-list-item ${activeId === thread.id ? 'active' : ''}`} onClick={() => onOpen(thread.id)}>
              <div className="thread-list-meta"><span>{thread.code}</span><StatusBadge tone={status.tone}>{status.label}</StatusBadge></div>
              <strong>{thread.title}</strong>
              <p>{thread.nextStep}</p>
              <footer><span>{thread.currentOwner}</span><time>{formatTime(thread.updatedAt, true)}</time>{thread.unread > 0 && <em>{thread.unread}</em>}</footer>
            </button>
          )
        })}
        {threads.length === 0 && <EmptyState icon={<Search />} title="没有匹配的协作" body="调整筛选，或从 MO 发起一个新目标。" />}
      </div>
    </aside>
  )
}

function ConversationPanel({ thread, onObserver }: { thread: CollaborationThread; onObserver: () => void }) {
  const { state, setChannel, sendMessage, confirmPlan, returnPlan, deleteDraft, terminateThread } = useStore()
  const [draft, setDraft] = useState('')
  const [attachments, setAttachments] = useState<AttachmentMeta[]>([])
  const [messageMode, setMessageMode] = useState<'chat' | 'change'>('chat')
  const [closePanelOpen, setClosePanelOpen] = useState(false)
  const [terminationReason, setTerminationReason] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const currentChannel = state.activeChannel
  const messages = thread.messages.filter(item => item.channel === currentChannel)
  const assignment = [...thread.assignments].reverse().find(item => item.agent === currentChannel)
  const proposedPlan = [...thread.plans].reverse().find(plan => plan.status === 'proposed')
  const isClosed = thread.status === 'ended' || thread.status === 'terminated'
  const channelEnabled = (channel: AgentKey) => channel === 'MO' || thread.assignments.some(item => item.agent === channel) || thread.messages.some(item => item.channel === channel)

  useEffect(() => {
    setDraft('')
    setAttachments([])
    setMessageMode('chat')
    setClosePanelOpen(false)
    setTerminationReason('')
  }, [thread.id])

  function chooseChannel(channel: AgentKey) {
    if (channelEnabled(channel)) setChannel(channel)
  }

  function addFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []).slice(0, 5)
    setAttachments(current => [...current, ...files.map(file => ({ id: `${file.name}-${file.lastModified}`, name: file.name, type: file.type || 'application/octet-stream', size: file.size }))].slice(0, 5))
    event.target.value = ''
  }

  function submit() {
    const body = draft.trim()
    if (!body) return
    sendMessage(thread.id, currentChannel, body, attachments, currentChannel !== 'MO' && messageMode === 'change')
    setDraft('')
    setAttachments([])
    setMessageMode('chat')
  }

  return (
    <section className="conversation-panel">
      <header className="conversation-header">
        <div><span>{thread.code} · {thread.priority}</span><h2>{thread.title}</h2></div>
        <div><StatusBadge tone={threadStatusCopy[thread.status].tone}>{threadStatusCopy[thread.status].label}</StatusBadge>{!isClosed && <button className="goal-close-trigger" onClick={() => setClosePanelOpen(value => !value)}><X size={13} />{thread.status === 'draft' ? '删除草稿' : '终止目标'}</button>}<button className="icon-button observer-toggle" aria-label="查看任务观察器" onClick={onObserver}><ListChecks size={18} /></button></div>
      </header>

      {closePanelOpen && !isClosed && <section className="goal-close-panel">
        <div><strong>{thread.status === 'draft' ? '删除未提交草稿' : '终止当前目标'}</strong><p>{thread.status === 'draft' ? '草稿还没有提交给 MO，删除后不保留事件链。' : 'PMA / BGA 的任务会停止；原因、消息和事件链继续保留。'}</p></div>
        {thread.status !== 'draft' && <textarea value={terminationReason} onChange={event => setTerminationReason(event.target.value)} aria-label="终止原因" placeholder="简要说明终止原因" autoFocus />}
        <footer><button className="secondary-button" onClick={() => { setClosePanelOpen(false); setTerminationReason('') }}>继续保留</button>{thread.status === 'draft' ? <button className="danger-button" onClick={() => deleteDraft(thread.id)}>确认删除</button> : <button className="danger-button" disabled={!terminationReason.trim()} onClick={() => { terminateThread(thread.id, terminationReason); setClosePanelOpen(false); setTerminationReason('') }}>确认终止</button>}</footer>
      </section>}

      <nav className="channel-tabs" aria-label="协作线程">
        {(Object.keys(agentCopy) as AgentKey[]).map(channel => {
          const enabled = channelEnabled(channel)
          return (
            <button key={channel} className={currentChannel === channel ? 'active' : ''} disabled={!enabled} onClick={() => chooseChannel(channel)} title={!enabled ? 'MO 尚未给该岗位分派任务' : agentCopy[channel].description}>
              <span className={`agent-monogram ${channel.toLowerCase()}`}>{channel}</span>
              <span><strong>{agentCopy[channel].full}</strong><small>{channel === 'MO' ? '主线程' : enabled ? '岗位子线程' : '尚未分派'}</small></span>
              {!enabled && <LockKeyhole size={13} />}
            </button>
          )
        })}
      </nav>

      {currentChannel !== 'MO' && assignment && (
        <section className="assignment-context">
          <div><span>任务来源</span><p>{assignment.sourceInstruction}</p></div>
          <div><span>交付物</span><p>{assignment.deliverable}</p></div>
          <div><span>边界</span><p>{assignment.boundary}</p></div>
          <StatusBadge tone={statusTone(assignment.status)}>{statusLabel(assignment.status)}</StatusBadge>
        </section>
      )}

      <div className="message-scroll" aria-live="polite">
        <div className="conversation-date"><span>{agentCopy[currentChannel].description}</span></div>
        {messages.map(item => <MessageBubble key={item.id} message={item} />)}
        {messages.length === 0 && <EmptyState icon={<MessageSquareText />} title="这个子线程还没有消息" body="岗位接收任务后，指令、回复、结果和变更请求都会保留在这里。" />}
        {currentChannel === 'MO' && proposedPlan && (
          <PlanCard key={proposedPlan.id} thread={thread} plan={proposedPlan} onConfirm={() => confirmPlan(thread.id)} onReturn={() => returnPlan(thread.id)} />
        )}
      </div>

      {!isClosed ? <footer className="composer">
        {attachments.length > 0 && <div className="attachment-row">{attachments.map(file => <span key={file.id}><FileText size={14} /><span>{file.name}</span><button aria-label={`移除 ${file.name}`} onClick={() => setAttachments(current => current.filter(item => item.id !== file.id))}><X size={13} /></button></span>)}</div>}
        <div className="composer-box">
          <textarea
            value={draft}
            onChange={event => setDraft(event.target.value)}
            onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }}
            placeholder={currentChannel === 'MO' ? '向 MO 说明目标或补充信息…' : messageMode === 'change' ? '说明要修改的目标、范围、期限或交付…' : `与 ${currentChannel} 沟通当前任务…`}
            aria-label={`发送给 ${agentCopy[currentChannel].full}`}
          />
          <div className="composer-actions">
            <button className="icon-button" aria-label="添加附件元数据" title="仅保存名称、类型和大小，不保存文件内容" onClick={() => fileInput.current?.click()}><Paperclip size={17} /></button>
            <input ref={fileInput} type="file" multiple hidden onChange={addFiles} />
            {currentChannel !== 'MO' && <div className="message-mode"><button className={messageMode === 'chat' ? 'active' : ''} onClick={() => setMessageMode('chat')}>普通沟通</button><button className={messageMode === 'change' ? 'active' : ''} onClick={() => setMessageMode('change')}>任务变更</button></div>}
            <span><ShieldCheck size={13} />前端模拟</span>
            <button className="send-button" onClick={submit} disabled={!draft.trim()}><Send size={16} /><span>发送</span></button>
          </div>
        </div>
        <small className="composer-boundary">新目标发给 MO；重大调整请选择“任务变更”。</small>
      </footer> : <footer className="closed-thread-banner"><LockKeyhole size={14} /><span>{thread.status === 'terminated' ? '目标已终止，当前记录为只读；消息、岗位结果和事件链仍可查看。' : '本轮已结束，协作记录保持只读。'}</span></footer>}
    </section>
  )
}

function MessageBubble({ message }: { message: CollaborationThread['messages'][number] }) {
  const isHuman = message.sender === 'human'
  return (
    <article className={`message-bubble ${message.sender}`}>
      {!isHuman && <span className={`agent-monogram ${message.channel.toLowerCase()}`}>{message.sender === 'system' ? 'SYS' : message.channel}</span>}
      <div className="message-body">
        <header><strong>{message.actor}</strong><time>{formatTime(message.createdAt)}</time>{message.intent === 'change_request' && <StatusBadge tone="warning">变更请求</StatusBadge>}{message.intent === 'result' && <StatusBadge tone="success">结果</StatusBadge>}</header>
        <p>{message.body}</p>
        {message.attachments && message.attachments.length > 0 && <div className="message-attachments">{message.attachments.map(file => <span key={file.id}><Paperclip size={12} />{file.name}<small>{Math.max(1, Math.round(file.size / 1024))} KB · 元数据</small></span>)}</div>}
      </div>
      {isHuman && <span className="human-monogram">你</span>}
    </article>
  )
}

function PlanCard({ thread, plan, onConfirm, onReturn }: { thread: CollaborationThread; plan: CollaborationThread['plans'][number]; onConfirm: () => void; onReturn: () => void }) {
  const { state, savePlanDraft, replanWithHumanInput } = useStore()
  const initialDraft: PlanHumanDraft = plan.humanDraft ?? {
    objective: thread.objective,
    scope: '只处理当前目标，不补充未经确认的外部事实。',
    acceptance: thread.acceptance,
    priority: thread.priority,
    deadline: '无真实截止时间',
    requiredEvidence: '由岗位任务列出证据缺口',
    deliverables: plan.steps.filter(step => step.owner !== 'MO').map(step => step.deliverable).join('；'),
    agents: plan.steps.map(step => step.owner).filter((owner): owner is 'PMA' | 'BGA' => owner === 'PMA' || owner === 'BGA'),
    publishBoundary: 'MANUAL：不自动发布、不投放。',
    note: '', updatedAt: new Date().toISOString(), updatedBy: roleCopy[state.role].label,
  }
  const [editing, setEditing] = useState(Boolean(plan.changeSummary))
  const [draft, setDraft] = useState<PlanHumanDraft>(initialDraft)
  const setField = <K extends keyof PlanHumanDraft>(key: K, value: PlanHumanDraft[K]) => setDraft(current => ({ ...current, [key]: value }))

  function toggleAgent(agent: 'PMA' | 'BGA') {
    setField('agents', draft.agents.includes(agent) ? draft.agents.filter(item => item !== agent) : [...draft.agents, agent])
  }

  return (
    <article className="plan-card">
      <header><div><GitBranch size={18} /><strong>Plan v{plan.version}</strong></div><StatusBadge tone="warning">待确认</StatusBadge></header>
      {plan.diff && plan.diff.length > 0 && <div className="plan-diff">{plan.diff.map(item => <span key={item}>{item}</span>)}</div>}
      {!editing ? <>
        <h3>{plan.summary}</h3>
        <div className="plan-steps compact-plan-steps">
          {plan.steps.map((step, index) => <div key={step.id}><span>{String(index + 1).padStart(2, '0')}</span><div><small>{step.owner}</small><strong>{step.title}</strong><p>{step.deliverable}</p></div></div>)}
        </div>
        <p className="plan-boundary"><ShieldCheck size={15} />{plan.boundary}</p>
      </> : <section className="plan-editor">
        <header><Edit3 size={16} /><div><strong>人工修订</strong><small>你编辑业务约束，MO 负责重新拆解。</small></div></header>
        <label className="full"><span>目标</span><textarea value={draft.objective} onChange={event => setField('objective', event.target.value)} /></label>
        <div className="plan-editor-grid">
          <label><span>优先级</span><select value={draft.priority} onChange={event => setField('priority', event.target.value as PlanHumanDraft['priority'])}><option>P0</option><option>P1</option><option>P2</option></select></label>
          <label><span>期限</span><input value={draft.deadline} onChange={event => setField('deadline', event.target.value)} /></label>
        </div>
        <label className="full"><span>验收标准（每行一项）</span><textarea value={draft.acceptance.join('\n')} onChange={event => setField('acceptance', event.target.value.split('\n').filter(Boolean))} /></label>
        <label className="full"><span>范围</span><input value={draft.scope} onChange={event => setField('scope', event.target.value)} /></label>
        <label className="full"><span>必须证据</span><input value={draft.requiredEvidence} onChange={event => setField('requiredEvidence', event.target.value)} /></label>
        <label className="full"><span>交付物</span><input value={draft.deliverables} onChange={event => setField('deliverables', event.target.value)} /></label>
        <fieldset><legend>参与岗位</legend><label><input type="checkbox" checked={draft.agents.includes('PMA')} onChange={() => toggleAgent('PMA')} />PMA</label><label><input type="checkbox" checked={draft.agents.includes('BGA')} onChange={() => toggleAgent('BGA')} />BGA</label></fieldset>
        <label className="full"><span>发布边界</span><input value={draft.publishBoundary} onChange={event => setField('publishBoundary', event.target.value)} /></label>
        <label className="full"><span>给 MO 的修订说明</span><textarea value={draft.note} onChange={event => setField('note', event.target.value)} placeholder="说明为什么修改，以及必须保留的约束" /></label>
        <footer><button className="secondary-button" onClick={() => savePlanDraft(thread.id, plan.id, draft)}>保存人工草稿</button><button className="primary-button" onClick={() => replanWithHumanInput(thread.id, plan.id, draft)}><RefreshCcw size={14} />交给 MO 重排</button></footer>
      </section>}
      <footer className="plan-actions"><button className="text-button" onClick={() => setEditing(value => !value)}>{editing ? '收起编辑' : '参与修订'}</button><button className="text-button danger-text" onClick={onReturn}>退回</button><button className="primary-button" onClick={onConfirm}><Check size={15} />确认 v{plan.version}</button></footer>
    </article>
  )
}

function TaskObserver({ thread, open, onClose }: { thread: CollaborationThread; open: boolean; onClose: () => void }) {
  const { resumeThread } = useStore()
  const currentPlan = [...thread.plans].reverse()[0]
  const pendingDecision = thread.status === 'awaiting_human' && thread.decisions.some(item => item.status === 'pending')
  return (
    <aside className={`task-observer ${open ? 'observer-open' : ''}`}>
      <header><div><span>task observer</span><h2>任务观察器</h2></div><button className="icon-button observer-close" aria-label="关闭任务观察器" onClick={onClose}><PanelRightClose size={18} /></button></header>
      <div className="observer-scroll">
        <section className="observer-status">
          <div><StatusBadge tone={threadStatusCopy[thread.status].tone}>{threadStatusCopy[thread.status].label}</StatusBadge><span>{thread.code} · {thread.priority}</span></div>
          <h3>{thread.title}</h3>
          <dl className="owner-next"><div><dt>当前责任人</dt><dd>{thread.currentOwner}</dd></div><div><dt>下一步</dt><dd>{thread.nextStep}</dd></div></dl>
        </section>

        <ObserverSection icon={<BadgeCheck size={16} />} title="目标与验收">
          <ul className="check-list">{thread.acceptance.map(item => <li key={item}><Check size={13} />{item}</li>)}</ul>
        </ObserverSection>

        {currentPlan && <ObserverSection icon={<GitBranch size={16} />} title={`Plan v${currentPlan.version}`} meta={currentPlan.status}>
          <p className="observer-copy">{currentPlan.summary}</p>
          {currentPlan.changeSummary && <p className="observer-alert">变更：{currentPlan.changeSummary}</p>}
        </ObserverSection>}

        <ObserverSection icon={<Bot size={16} />} title="岗位任务" meta={`${thread.assignments.filter(item => item.status !== 'cancelled').length} 项`}>
          <div className="observer-assignments">
            {thread.assignments.filter(item => item.status !== 'cancelled').map(item => (
              <article key={item.id}>
                <header><span className={`agent-monogram ${item.agent.toLowerCase()}`}>{item.agent}</span><div><strong>{item.title}</strong><small>{item.id}</small></div><StatusBadge tone={statusTone(item.status)}>{statusLabel(item.status)}</StatusBadge></header>
                <p>{item.currentAction}</p>
                <dl><div><dt>交付物</dt><dd>{item.deliverable}</dd></div><div><dt>期限 / 依赖</dt><dd>{item.deadline ?? item.dueLabel}{item.dependsOn?.length ? ` · 等待 ${item.dependsOn.join('、')}` : ''}</dd></div></dl>
              </article>
            ))}
            {thread.assignments.length === 0 && <p className="observer-empty">计划尚未确认，因此没有岗位任务。</p>}
          </div>
        </ObserverSection>

        {thread.changeRequests.length > 0 && <ObserverSection icon={<RefreshCcw size={16} />} title="任务变更">
          {thread.changeRequests.map(change => <div className="change-request" key={change.id}><StatusBadge tone="warning">{change.status}</StatusBadge><strong>{change.summary}</strong><p>{change.impact}</p></div>)}
        </ObserverSection>}

        <details className="observer-details"><summary><span><Database size={15} />证据与对象</span><small>{thread.objects.length}</small></summary><div className="object-mini-list">{thread.objects.map(object => <div key={object.id}><span>{object.type}</span><p><strong>{object.title}</strong><small>{object.version} · {object.status}</small></p></div>)}</div></details>
        <details className="observer-details"><summary><span><History size={15} />事件链</span><small>{thread.trace.length}</small></summary><ol className="trace-list">{[...thread.trace].reverse().map(event => <li key={event.id}><span className="trace-dot" /><div><header><strong>{event.title}</strong><time>{formatTime(event.createdAt, true)}</time></header><p>{event.detail}</p><small>{event.actor}</small></div></li>)}</ol></details>
      </div>

      {(pendingDecision || thread.status === 'HOLD') && <footer className="observer-decision-bar">
        {pendingDecision && <DecisionControls thread={thread} compact />}
        {thread.status === 'HOLD' && !pendingDecision && <button className="primary-button wide" onClick={() => resumeThread(thread.id)}><Edit3 size={14} />参与恢复计划</button>}
      </footer>}
    </aside>
  )
}

function ObserverSection({ icon, title, meta, children }: { icon: ReactNode; title: string; meta?: string; children: ReactNode }) {
  return <section className="observer-section"><header><span>{icon}</span><h3>{title}</h3>{meta && <small>{meta}</small>}</header>{children}</section>
}

function ObjectsView() {
  const { state, openThread } = useStore()
  const targetAssets = [...state.threads].sort((a, b) => +new Date(b.updatedAt) - +new Date(a.updatedAt))
  const assetGroups = [
    { type: 'Fact', label: '已验证事实', description: '可回溯的输入与证据' },
    { type: 'Claim', label: '可用表达', description: '在边界内可使用的说法' },
    { type: 'Campaign', label: '营销计划', description: '主题、受众与渠道安排' },
    { type: 'Content', label: '内容草稿', description: '脚本、图文与发布包' },
  ] as const
  function openObject(thread: CollaborationThread, type: CollaborationThread['objects'][number]['type']) {
    const preferred: AgentKey = type === 'Fact' || type === 'Claim' ? 'PMA' : type === 'Campaign' || type === 'Content' ? 'BGA' : 'MO'
    const channel = preferred === 'MO' || thread.assignments.some(item => item.agent === preferred) || thread.messages.some(item => item.channel === preferred) ? preferred : 'MO'
    openThread(thread.id, channel)
  }
  return (
    <div className="page-container">
      <PageHeader eyebrow="business object registry" title="业务对象" description="先看目标，再看其下的事实、表达、计划、内容和决策记录。" />
      <section className="target-asset-list" aria-label="按目标归档的业务对象">
        {targetAssets.map(thread => {
          const assetCount = thread.objects.length + thread.decisions.length
          return <article className="target-asset-card" key={thread.id}>
            <header>
              <div><span>{thread.code} · {thread.priority}</span><h2>{thread.title}</h2></div>
              <StatusBadge tone={threadStatusCopy[thread.status].tone}>{threadStatusCopy[thread.status].label}</StatusBadge>
            </header>
            <div className="target-asset-summary" aria-label={`${thread.code} 对象概览`}>
              {assetGroups.map(group => <div key={group.type}><span>{group.label}</span><strong>{thread.objects.filter(object => object.type === group.type).length}</strong></div>)}
              <div><span>决策记录</span><strong>{thread.decisions.length}</strong></div>
            </div>
            <details>
              <summary><span>查看 {assetCount} 项对象明细</span><small>版本、状态与来源都保留在目标内</small></summary>
              <div className="target-asset-groups">
                {assetGroups.map(group => {
                  const items = thread.objects.filter(object => object.type === group.type)
                  return <section key={group.type}>
                    <header><div><strong>{group.label}</strong><small>{group.description}</small></div><em>{items.length}</em></header>
                    {items.length > 0 ? <ul>{items.map(object => <li key={object.id}><button onClick={() => openObject(thread, object.type)}><div><strong>{object.title}</strong><small>{object.id} · {object.version}</small></div><StatusBadge tone={object.status === 'approved' || object.status === 'verified' ? 'success' : object.status === 'blocked' ? 'danger' : 'neutral'}>{objectStatusLabel(object.status)}</StatusBadge><span className="object-jump">打开{object.type === 'Fact' || object.type === 'Claim' ? 'PMA' : 'BGA'} <ArrowUpRight size={12} /></span></button></li>)}</ul> : <p>暂无</p>}
                  </section>
                })}
                <section>
                  <header><div><strong>决策记录</strong><small>对该目标作出的正式判断</small></div><em>{thread.decisions.length}</em></header>
                  {thread.decisions.length > 0 ? <ul>{thread.decisions.map(decision => <li key={decision.id}><button onClick={() => openThread(thread.id, 'MO')}><div><strong>{decision.title}</strong><small>{decision.reason}</small></div><StatusBadge tone={decisionStatusTone(decision.status)}>{decisionStatusLabel(decision.status)}</StatusBadge><span className="object-jump">打开 MO <ArrowUpRight size={12} /></span></button></li>)}</ul> : <p>暂无</p>}
                </section>
              </div>
              <button className="text-button asset-thread-link" onClick={() => openThread(thread.id)}>打开该目标协作记录 <ArrowUpRight size={14} /></button>
            </details>
          </article>
        })}
        {targetAssets.length === 0 && <EmptyState icon={<Database />} title="还没有业务对象" body="当目标形成事实、表达、内容或正式决定后，会按目标归档在这里。" />}
      </section>
    </div>
  )
}

function ReviewsView() {
  const { state, openThread } = useStore()
  const [filter, setFilter] = useState<'all' | 'pending' | 'history'>('all')
  const decisions = state.threads.flatMap(thread => thread.decisions.map(decision => ({ thread, decision }))).sort((a, b) => +new Date(b.decision.resolvedAt ?? b.decision.createdAt) - +new Date(a.decision.resolvedAt ?? a.decision.createdAt))
  const visibleDecisions = decisions.filter(item => filter === 'all' || (filter === 'pending' ? item.decision.status === 'pending' : item.decision.status !== 'pending'))
  return (
    <div className="page-container">
      <PageHeader eyebrow="decision register" title="决策台账" description="查看正式决定及其依据；需要你立即处理的事项仍在任务中心。" />
      <section className="decision-ledger">
        <header className="decision-ledger-header"><div><ClipboardCheck size={18} /><h2>正式决策</h2><span>{decisions.length} 条</span></div><nav aria-label="决策记录范围"><button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>全部</button><button className={filter === 'pending' ? 'active' : ''} onClick={() => setFilter('pending')}>待决定</button><button className={filter === 'history' ? 'active' : ''} onClick={() => setFilter('history')}>已处理</button></nav></header>
        <div className="decision-ledger-list">
          {visibleDecisions.map(({ thread, decision }) => <button className="decision-ledger-row" key={decision.id} onClick={() => openThread(thread.id)}><div><strong>{decision.title}</strong><small>{decision.reason}</small></div><StatusBadge tone={decisionStatusTone(decision.status)}>{decisionStatusLabel(decision.status)}</StatusBadge><div><span>{thread.code}</span><small>{thread.title}</small></div><time>{formatTime(decision.resolvedAt ?? decision.createdAt, true)}</time><ArrowUpRight size={15} /></button>)}
          {visibleDecisions.length === 0 && <EmptyState icon={<ClipboardCheck />} title={filter === 'pending' ? '没有待决定事项' : '暂无决策记录'} body={filter === 'pending' ? '需要你处理的决策会同步出现在任务中心。' : '决策一旦形成，会在这里保留理由、状态和关联目标。'} />}
        </div>
      </section>
    </div>
  )
}

function HoldsView() {
  const { state, openThread, resumeThread } = useStore()
  const holds = state.threads.filter(thread => thread.status === 'HOLD')
  return (
    <div className="page-container">
      <PageHeader eyebrow="exception desk" title="异常处置" description="处理暂停目标、补齐条件与人工接管；正常待办仍在任务中心。" />
      <div className="hold-grid">
        {holds.map(thread => <article className="hold-view-card" key={thread.id}><header><CirclePause size={19} /><StatusBadge tone="danger">已暂停</StatusBadge><span>{thread.code}</span></header><h2>{thread.title}</h2><p>{thread.decisions.at(-1)?.reason ?? thread.nextStep}</p><div><span>处置条件</span><strong>{thread.nextStep}</strong></div><footer><button className="secondary-button" onClick={() => openThread(thread.id)}>查看上下文</button><button className="primary-button" onClick={() => { resumeThread(thread.id); openThread(thread.id) }}><Edit3 size={14} />参与恢复计划</button></footer></article>)}
        {holds.length === 0 && <EmptyState icon={<CheckCircle2 />} title="没有异常事项" body="暂停、恢复和人工接管记录仍保留在对应目标的事件链中。" />}
      </div>
    </div>
  )
}

function DailyView() {
  const { state, openThread } = useStore()
  const active = state.threads.filter(thread => thread.status === 'active')
  const needsHuman = state.threads.filter(thread => ['awaiting_plan', 'awaiting_human', 'HOLD'].includes(thread.status))
  const submitted = state.threads.flatMap(thread => thread.assignments).filter(item => item.status === 'submitted')
  return (
    <div className="page-container">
      <PageHeader eyebrow="2026 · 08 · 14" title="Daily Brief" description="一页只回答三件事：你今天要判断什么、Agent 在推进什么、哪些证据或异常需要关注。" />
      <article className="daily-brief">
        <header><div><span>S2 / DAILY</span><h2>{roleCopy[state.role].label}的运行摘要</h2></div><strong>{String(needsHuman.length).padStart(2, '0')}<small>项需要你</small></strong></header>
        <DailyBlock number="01" title="今天需要你的判断" items={needsHuman.map(thread => ({ title: thread.title, detail: thread.nextStep, thread }))} onOpen={openThread} />
        <DailyBlock number="02" title="Agent 正在推进" items={active.map(thread => ({ title: thread.title, detail: `${thread.currentOwner} · ${thread.nextStep}`, thread }))} onOpen={openThread} />
        <DailyBlock number="03" title="新证据与结果" items={submitted.map(assignment => { const thread = state.threads.find(item => item.assignments.some(candidate => candidate.id === assignment.id))!; return { title: `${assignment.agent} · ${assignment.title}`, detail: `${assignment.evidence.length} 项证据，${assignment.gaps.length} 项缺口`, thread } })} onOpen={openThread} />
        <footer><ShieldCheck size={17} /><span>本摘要来自浏览器内演示数据；没有读取模型、数据库或平台实时状态。</span></footer>
      </article>
    </div>
  )
}

function DailyBlock({ number, title, items, onOpen }: { number: string; title: string; items: { title: string; detail: string; thread: CollaborationThread }[]; onOpen: (id: string) => void }) {
  return <section className="daily-block"><header><span>{number}</span><h3>{title}</h3></header><div>{items.length > 0 ? items.map(item => <button key={`${number}-${item.thread.id}-${item.title}`} onClick={() => onOpen(item.thread.id)}><CircleDot size={14} /><span><strong>{item.title}</strong><small>{item.detail}</small></span><ArrowUpRight size={15} /></button>) : <p>当前没有相关事项。</p>}</div></section>
}

type AgentConfigTab = 'overview' | 'sixpack' | 'skills' | 'model'

const agentConfigStatusCopy: Record<AgentProfileConfig['status'], { label: string; tone: StatusTone }> = {
  published: { label: '已发布', tone: 'success' },
  draft: { label: '草稿', tone: 'warning' },
  validated: { label: '已校验', tone: 'info' },
  invalid: { label: '校验失败', tone: 'danger' },
}

function getAgentConfigDiff(current: AgentProfileConfig, published?: AgentProfileConfig) {
  if (!published) return ['尚无已发布快照']
  const changes: string[] = []
  if (current.profileName !== published.profileName) changes.push('Profile 名称')
  if (JSON.stringify(current.model) !== JSON.stringify(published.model)) changes.push('模型 / API')
  current.sixPack.forEach(resource => {
    const old = published.sixPack.find(item => item.key === resource.key)
    if (!old || JSON.stringify(resource) !== JSON.stringify(old)) changes.push(resource.name)
  })
  current.skills.forEach(skill => {
    const old = published.skills.find(item => item.id === skill.id)
    if (!old || JSON.stringify(skill) !== JSON.stringify(old)) changes.push(`Skill：${skill.name}`)
  })
  if (JSON.stringify(current.permissions) !== JSON.stringify(published.permissions)) changes.push('工具与权限')
  if (current.memorySummary !== published.memorySummary) changes.push('Memory Policy')
  return [...new Set(changes)]
}

function AgentConfigView() {
  const { state, setRole, updateAgentConfig, validateAgentConfig, publishAgentConfig, rollbackAgentConfig } = useStore()
  const [selectedAgent, setSelectedAgent] = useState<AgentKey>('MO')
  const [tab, setTab] = useState<AgentConfigTab>('overview')
  const [editingResource, setEditingResource] = useState<SixPackResource | null>(null)
  const [editingSkill, setEditingSkill] = useState<AgentSkillBinding | null>(null)
  const config = state.agentConfigs.find(item => item.agent === selectedAgent)!
  const history = state.agentConfigHistory.filter(item => item.agent === selectedAgent).sort((a, b) => b.version - a.version)
  const latestPublished = history[0]?.config
  const diff = getAgentConfigDiff(config, latestPublished)
  const status = agentConfigStatusCopy[config.status]
  const editable = state.role === 'tech'

  function update(next: AgentProfileConfig) {
    if (editable) updateAgentConfig(next)
  }

  function saveResource(resource: SixPackResource) {
    update({ ...config, sixPack: config.sixPack.map(item => item.key === resource.key ? resource : item) })
    setEditingResource(null)
  }

  function saveSkill(skill: AgentSkillBinding) {
    update({ ...config, skills: config.skills.map(item => item.id === editingSkill?.id ? skill : item) })
    setEditingSkill(null)
  }

  return (
    <div className="page-container agent-config-page">
      <PageHeader eyebrow="hermes profile control" title="Agent 配置" description="查看、修订和发布三名数字岗位的影子配置。" />

      {!editable && <section className="config-readonly"><LockKeyhole size={16} /><span>当前为只读。切换到“技术管理员”后可编辑和发布。</span></section>}
      <LocalDeepSeekSetup editable={editable} onRequestAdmin={() => setRole('tech')} />

      <nav className="agent-config-switcher" aria-label="选择 Agent">
        {state.agentConfigs.map(item => <button key={item.agent} className={selectedAgent === item.agent ? 'active' : ''} onClick={() => { setSelectedAgent(item.agent); setEditingResource(null); setEditingSkill(null) }}>
          <span className={`agent-monogram ${item.agent.toLowerCase()}`}>{item.agent}</span>
          <span><strong>{item.roleName}</strong><small>{item.profileName}</small></span>
          <StatusBadge tone={agentConfigStatusCopy[item.status].tone}>{agentConfigStatusCopy[item.status].label}</StatusBadge>
        </button>)}
      </nav>

      <section className="config-profile-bar">
        <div><span className={`agent-monogram ${config.agent.toLowerCase()}`}>{config.agent}</span><div><small>PROFILE v{config.profileVersion}</small><h2>{config.roleName}</h2></div></div>
        <div className="config-profile-status"><StatusBadge tone={status.tone}>{status.label}</StatusBadge><span>{config.model.model}</span><span>{config.skills.filter(skill => skill.enabled).length} Skills</span></div>
        <div className="config-profile-actions">
          <button className="secondary-button" disabled={!editable} onClick={() => validateAgentConfig(config.agent)}><ShieldCheck size={14} />校验草稿</button>
          <button className="primary-button" disabled={!editable || config.status !== 'validated'} onClick={() => publishAgentConfig(config.agent)}><Save size={14} />发布版本</button>
        </div>
      </section>

      <nav className="config-tabs" aria-label="配置分类">
        {([['overview', '概览'], ['sixpack', '岗位六件套'], ['skills', 'Skills'], ['model', '模型与权限']] as const).map(([key, label]) => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}
      </nav>

      <div className="config-workspace">
        <section className="config-main">
          {tab === 'overview' && <AgentConfigOverview config={config} historyCount={history.length} />}
          {tab === 'sixpack' && <>
            {editingResource && <SixPackEditor resource={editingResource} onSave={saveResource} onClose={() => setEditingResource(null)} editable={editable} />}
            <div className="config-resource-list">{config.sixPack.map(resource => <article key={resource.key}><div><span className="config-file-icon"><FileText size={16} /></span><div><strong>{resource.name}</strong><small>{resource.summary}</small></div></div><div><StatusBadge tone={resource.status === 'ready' ? 'success' : resource.status === 'warning' ? 'warning' : 'danger'}>{resource.status}</StatusBadge><span>{resource.version}</span><button className="text-button" disabled={!editable} onClick={() => setEditingResource(resource)}>编辑</button></div></article>)}</div>
          </>}
          {tab === 'skills' && <>
            {editingSkill && <SkillEditor skill={editingSkill} onSave={saveSkill} onClose={() => setEditingSkill(null)} editable={editable} />}
            <div className="config-skill-list">{config.skills.map((skill, index) => <article key={`${skill.id}-${index}`}><span className="skill-number">{String(index + 1).padStart(2, '0')}</span><div><strong>{skill.name}</strong><small>{skill.capability}</small><em>{skill.source} · {skill.version}</em></div><StatusBadge tone={skill.status === 'ready' ? 'success' : skill.status === 'warning' ? 'warning' : 'danger'}>{skill.status}</StatusBadge><label className="config-toggle"><input type="checkbox" checked={skill.enabled} disabled={!editable} onChange={() => update({ ...config, skills: config.skills.map(item => item.id === skill.id ? { ...item, enabled: !item.enabled } : item) })} /><span /></label><button className="text-button" disabled={!editable} onClick={() => setEditingSkill(skill)}>更换</button></article>)}</div>
          </>}
          {tab === 'model' && <ModelPermissionEditor config={config} onChange={update} editable={editable} />}
        </section>

        <aside className="config-side">
          <section className="config-diff-panel"><header><GitBranch size={15} /><h3>未发布变更</h3><span>{diff.length}</span></header>{diff.length ? <ul>{diff.map(item => <li key={item}>{item}</li>)}</ul> : <p>与已发布版本一致。</p>}</section>
          <section className="config-publish-flow"><h3>发布流程</h3><ol><li className={config.status !== 'published' ? 'active' : ''}><span>1</span>编辑草稿</li><li className={config.status === 'validated' ? 'active' : ''}><span>2</span>配置校验</li><li className={config.status === 'published' ? 'active' : ''}><span>3</span>发布版本</li></ol><p>运行中的任务继续使用原配置快照。</p></section>
          <details className="config-history"><summary>版本记录 <span>{history.length}</span></summary><div>{history.map(item => <article key={item.id}><div><strong>v{item.version}</strong><small>{formatTime(item.createdAt, true)}</small></div><p>{item.summary}</p><button className="text-button" disabled={!editable || item.version === config.profileVersion} onClick={() => rollbackAgentConfig(config.agent, item.id)}><Undo2 size={13} />恢复为草稿</button></article>)}</div></details>
        </aside>
      </div>
    </div>
  )
}

function AgentConfigOverview({ config, historyCount }: { config: AgentProfileConfig; historyCount: number }) {
  return <div className="config-overview">
    <div className="config-overview-grid">
      <article><KeyRound size={18} /><span>模型 / API</span><strong>{config.model.model}</strong><small>{config.model.provider} · {config.model.credentialStatus}</small></article>
      <article><Layers3 size={18} /><span>岗位六件套</span><strong>{config.sixPack.filter(item => item.status === 'ready').length}/6</strong><small>{config.sixPack.every(item => item.status === 'ready') ? '配置完整' : '需要检查'}</small></article>
      <article><Library size={18} /><span>Skills</span><strong>{config.skills.filter(item => item.enabled).length}/6</strong><small>{config.skills.filter(item => item.status !== 'ready').length} 项需注意</small></article>
      <article><History size={18} /><span>已发布版本</span><strong>{historyCount}</strong><small>当前 v{config.profileVersion}</small></article>
    </div>
    <section className="config-memory"><div><Database size={17} /><h3>Memory</h3></div><p>{config.memorySummary}</p></section>
    <section className="config-runtime-boundary"><Wrench size={17} /><div><strong>工具边界</strong><p>{config.permissions.tools.join(' · ')}</p></div><span>{config.permissions.network ? '允许联网' : '禁止联网'}</span></section>
  </div>
}

function SixPackEditor({ resource, onSave, onClose, editable }: { resource: SixPackResource; onSave: (resource: SixPackResource) => void; onClose: () => void; editable: boolean }) {
  const [draft, setDraft] = useState(resource)
  return <section className="config-inline-editor"><header><div><FileText size={16} /><div><strong>{resource.name}</strong><small>保存后进入配置草稿。</small></div></div><button className="icon-button" onClick={onClose}><X size={16} /></button></header><div className="config-form-grid"><label><span>版本</span><input value={draft.version} onChange={event => setDraft({ ...draft, version: event.target.value })} /></label><label><span>状态</span><select value={draft.status} onChange={event => setDraft({ ...draft, status: event.target.value as SixPackResource['status'] })}><option value="ready">ready</option><option value="warning">warning</option><option value="missing">missing</option></select></label><label className="full"><span>来源</span><input value={draft.source} onChange={event => setDraft({ ...draft, source: event.target.value })} /></label><label className="full"><span>摘要</span><textarea value={draft.summary} onChange={event => setDraft({ ...draft, summary: event.target.value })} /></label></div><footer><button className="secondary-button" onClick={onClose}>取消</button><button className="primary-button" disabled={!editable || !draft.version || !draft.source} onClick={() => onSave(draft)}>保存为草稿</button></footer></section>
}

const sharedSkillOptions: AgentSkillBinding[] = [
  { id: 'douyin-growth', name: '抖音增长 Playbook', version: 'v1.0', source: 'shared/douyin-growth-playbook', capability: '抖音内容结构与增长检查', enabled: true, permissions: ['对象只读'], status: 'ready' },
  { id: 'evidence-guard', name: 'Evidence Guard', version: 'v0.8', source: 'shared/evidence-guard', capability: '阻断无证据 Claim', enabled: true, permissions: ['Fact 只读'], status: 'ready' },
  { id: 'content-review', name: 'Content Review', version: 'v1.2', source: 'shared/content-review', capability: '内容风险与白名单检查', enabled: true, permissions: ['Content 只读'], status: 'ready' },
]

function SkillEditor({ skill, onSave, onClose, editable }: { skill: AgentSkillBinding; onSave: (skill: AgentSkillBinding) => void; onClose: () => void; editable: boolean }) {
  const [draft, setDraft] = useState(skill)
  function chooseShared(id: string) {
    const selected = sharedSkillOptions.find(item => item.id === id)
    if (selected) setDraft(selected)
  }
  return <section className="config-inline-editor"><header><div><Library size={16} /><div><strong>更换 Skill</strong><small>保持六个岗位 Skill 插槽。</small></div></div><button className="icon-button" onClick={onClose}><X size={16} /></button></header><div className="config-form-grid"><label className="full"><span>共享 Skill 库</span><select value={draft.id} onChange={event => chooseShared(event.target.value)}><option value={skill.id}>{skill.name}</option>{sharedSkillOptions.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label><span>版本</span><input value={draft.version} onChange={event => setDraft({ ...draft, version: event.target.value })} /></label><label><span>状态</span><select value={draft.status} onChange={event => setDraft({ ...draft, status: event.target.value as AgentSkillBinding['status'] })}><option value="ready">ready</option><option value="warning">warning</option><option value="blocked">blocked</option></select></label><label className="full"><span>来源</span><input value={draft.source} onChange={event => setDraft({ ...draft, source: event.target.value })} /></label><label className="full"><span>能力</span><input value={draft.capability} onChange={event => setDraft({ ...draft, capability: event.target.value })} /></label></div><footer><button className="secondary-button" onClick={onClose}>取消</button><button className="primary-button" disabled={!editable || !draft.id || !draft.source} onClick={() => onSave(draft)}>保存为草稿</button></footer></section>
}

function ModelPermissionEditor({ config, onChange, editable }: { config: AgentProfileConfig; onChange: (config: AgentProfileConfig) => void; editable: boolean }) {
  const setModel = <K extends keyof AgentProfileConfig['model']>(key: K, value: AgentProfileConfig['model'][K]) => onChange({ ...config, model: { ...config.model, [key]: value } })
  const setPermission = <K extends keyof AgentProfileConfig['permissions']>(key: K, value: AgentProfileConfig['permissions'][K]) => onChange({ ...config, permissions: { ...config.permissions, [key]: value } })
  return <div className="model-permission-editor">
    <section><header><KeyRound size={17} /><div><h3>模型与 API</h3><p>只保存凭据引用，不保存真实 Key。</p></div></header><div className="config-form-grid"><label><span>Provider</span><input disabled={!editable} value={config.model.provider} onChange={event => setModel('provider', event.target.value)} /></label><label><span>Model</span><input disabled={!editable} value={config.model.model} onChange={event => setModel('model', event.target.value)} /></label><label><span>Endpoint 别名</span><input disabled={!editable} value={config.model.endpointAlias} onChange={event => setModel('endpointAlias', event.target.value)} /></label><label><span>凭据引用</span><input disabled={!editable} value={config.model.credentialRef} onChange={event => setModel('credentialRef', event.target.value)} /></label><label><span>推理等级</span><select disabled={!editable} value={config.model.reasoningLevel} onChange={event => setModel('reasoningLevel', event.target.value as AgentProfileConfig['model']['reasoningLevel'])}><option value="low">low</option><option value="medium">medium</option><option value="high">high</option></select></label><label><span>max_turns</span><input disabled={!editable} type="number" min="1" max="20" value={config.model.maxTurns} onChange={event => setModel('maxTurns', Number(event.target.value))} /></label><label><span>超时（秒）</span><input disabled={!editable} type="number" min="10" max="600" value={config.model.timeoutSeconds} onChange={event => setModel('timeoutSeconds', Number(event.target.value))} /></label></div></section>
    <section><header><Wrench size={17} /><div><h3>权限</h3><p>按最小权限发布。</p></div></header><div className="permission-list">{([['network', '联网'], ['terminal', '终端'], ['browser', '浏览器'], ['otherAgents', '调用其他 Agent'], ['memoryWrite', '写入岗位 Memory']] as const).map(([key, label]) => <label key={key}><span>{label}</span><input type="checkbox" disabled={!editable} checked={config.permissions[key]} onChange={event => setPermission(key, event.target.checked)} /></label>)}</div><label className="tools-field"><span>允许工具（逗号分隔）</span><textarea disabled={!editable} value={config.permissions.tools.join(', ')} onChange={event => setPermission('tools', event.target.value.split(',').map(item => item.trim()).filter(Boolean))} /></label></section>
    <section><header><Database size={17} /><div><h3>Memory</h3><p>只保存岗位偏好和协作习惯。</p></div></header><label className="tools-field"><span>策略摘要</span><textarea disabled={!editable} value={config.memorySummary} onChange={event => onChange({ ...config, memorySummary: event.target.value })} /></label></section>
  </div>
}

function LocalDeepSeekSetup({ editable, onRequestAdmin }: { editable: boolean; onRequestAdmin: () => void }) {
  const [status, setStatus] = useState<LocalModelStatus | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [busy, setBusy] = useState(false)
  const [testing, setTesting] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  async function refresh() {
    try {
      setStatus(await localModelAdmin.status())
    } catch (caught) {
      setStatus(null)
      setError(caught instanceof Error ? caught.message : '本机模型配置服务不可用。')
    }
  }

  useEffect(() => { void refresh() }, [])

  async function connect() {
    const submittedKey = apiKey.trim()
    setApiKey('')
    setBusy(true)
    setNotice('正在安全保存并验证 DeepSeek，通常需要几十秒。')
    setError('')
    try {
      const next = await localModelAdmin.configure(submittedKey || undefined)
      setStatus(next)
      setNotice(next.message || 'DeepSeek 已连接并启用。')
    } catch (caught) {
      setError(caught instanceof RuntimeApiError ? caught.message : 'DeepSeek 配置失败。')
      setNotice('')
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  async function testModel() {
    setTesting(true)
    setNotice('正在发送最小 Chat Completion 测试请求。')
    setError('')
    try {
      const next = await localModelAdmin.test()
      setStatus(next)
      setNotice(next.message || '模型调用测试通过。')
    } catch (caught) {
      setError(caught instanceof RuntimeApiError ? caught.message : '模型调用测试失败。')
      setNotice('')
      await refresh()
    } finally {
      setTesting(false)
    }
  }

  const stateLabel = status?.execution_enabled
    ? '真实执行已启用'
    : status?.credential_configured
      ? '密钥已保存，等待验证'
      : '尚未配置密钥'

  return <section className="local-model-setup">
    <header><ShieldCheck size={17} /><div><h3>本机真实模型连接</h3><p>Key 直接写入本机受限 Secret 文件；浏览器不保存、不回显。</p></div><StatusBadge tone={status?.execution_enabled ? 'success' : status?.credential_configured ? 'warning' : 'neutral'}>{stateLabel}</StatusBadge></header>
    {!editable && <div className="local-model-admin-hint"><LockKeyhole size={14} /><span>只有技术管理员可以修改运行密钥。</span><button className="secondary-button" onClick={onRequestAdmin}>切换到技术管理员</button></div>}
    <div className="local-model-summary"><span>Provider<strong>{status?.provider || 'deepseek'}</strong></span><span>Model<strong>{status?.model || 'deepseek-v4-pro'}</strong></span><span>执行模式<strong>{status?.mode || 'deepseek-api-key'}</strong></span></div>
    <div className="local-model-connect"><label><span>DeepSeek API Key</span><input type="password" autoComplete="new-password" value={apiKey} disabled={!editable || busy || testing} placeholder={status?.credential_configured ? '已安全保存；输入新 Key 可替换' : '粘贴 API Key'} onChange={event => setApiKey(event.target.value)} /></label><button className="primary-button" disabled={!editable || busy || testing || (!apiKey.trim() && !status?.credential_configured)} onClick={() => void connect()}>{busy ? <><RefreshCcw size={14} className="spin" />正在配置</> : <><KeyRound size={14} />{apiKey.trim() ? '保存、验证并启用' : '重新验证并启用'}</>}</button><button className="secondary-button" disabled={!editable || busy || testing || !status?.execution_enabled} onClick={() => void testModel()}>{testing ? <><RefreshCcw size={14} className="spin" />正在测试</> : <><Activity size={14} />测试模型调用</>}</button></div>
    {notice && <p className="local-model-notice success"><CheckCircle2 size={14} />{notice}</p>}
    {error && <p className="local-model-notice error"><CircleAlert size={14} />{error}</p>}
    <small>安全边界：该入口只通过绑定 127.0.0.1 的本机控制通道开放；Key 不进入浏览器存储，也不会回显。</small>
  </section>
}

function DiagnosticsView() {
  const { state, resetDemo, simulateResult, importDemo } = useStore()
  const [importError, setImportError] = useState('')
  const events = state.threads.reduce((sum, thread) => sum + thread.trace.length, 0)
  const messages = state.threads.reduce((sum, thread) => sum + thread.messages.length, 0)
  const activeRuns = state.threads.flatMap(thread => thread.assignments.filter(assignment => assignment.status === 'working').map(assignment => ({ thread, assignment })))

  function exportDemo() {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `s2-marketing-demo-${new Date().toISOString().slice(0, 10)}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  function importDemoFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const candidate = JSON.parse(String(reader.result))
        if (candidate.schemaVersion !== 2 || !Array.isArray(candidate.threads)) throw new Error('invalid')
        importDemo(candidate)
        setImportError('')
      } catch {
        setImportError('文件格式不符合当前演示版本。')
      }
    }
    reader.readAsText(file)
    event.target.value = ''
  }
  return (
    <div className="page-container">
      <PageHeader eyebrow="front-end observability" title="运行诊断" description="演示数据与真实 Runtime 控制。" actions={<><a className="secondary-button" href="/?view=runtime"><Activity size={15} />打开真实 Runtime</a><button className="secondary-button" onClick={resetDemo}><RotateCcw size={15} />恢复初始数据</button></>} />
      <section className="diagnostic-banner"><AlertCircle size={20} /><div><strong>双层运行边界</strong><p>八类页面的本地交互不调用模型；真实 Runtime 与 DeepSeek 只由完整流程工作台显式启动。所有发布仍为 simulated。</p></div></section>
      <section className="demo-tools">
        <header><div><Sparkles size={17} /><div><h2>演示控制</h2><p>模拟岗位提交只放在这里。</p></div></div><div><button className="secondary-button" onClick={exportDemo}><Download size={14} />导出演示</button><label className="secondary-button import-button"><FileText size={14} />导入演示<input type="file" accept="application/json" hidden onChange={importDemoFile} /></label></div></header>
        {importError && <p className="inline-error">{importError}</p>}
        <div>{activeRuns.map(({ thread, assignment }) => <button key={assignment.id} className="demo-run" onClick={() => simulateResult(thread.id, assignment.id)}><span className={`agent-monogram ${assignment.agent.toLowerCase()}`}>{assignment.agent}</span><span><strong>{assignment.title}</strong><small>{thread.code} · {assignment.currentAction}</small></span><Sparkles size={14} /></button>)}{activeRuns.length === 0 && <p className="observer-empty">没有运行中的演示任务。</p>}</div>
      </section>
      <div className="diagnostic-grid">
        <DiagnosticCard icon={<Database />} title="本地记录" status="正常" detail="刷新后保留。" />
        <DiagnosticCard icon={<Workflow />} title="事件" status={`${events} 条`} detail="指令、计划、任务与决策。" />
        <DiagnosticCard icon={<MessageSquareText />} title="消息" status={`${messages} 条`} detail="MO 与岗位子线程。" />
        <DiagnosticCard icon={<Settings />} title="连接器" status="关闭" detail="未连接外部平台。" />
      </div>
      <section className="integration-map"><header><BookOpenCheck size={18} /><div><h2>真实接入状态与保留边界</h2><p>完整流程工作台直接读取服务端事实；八类页面保留原 Reducer，只叠加当前案例的只读摘要。</p></div></header><div><span>MarketingCase / Step <ArrowRight size={14} /> 已接入九阶段状态机</span><span>Commitment / Handoff / Approval <ArrowRight size={14} /> 已接入人工门禁</span><span>Knowledge / Run / Attempt / Timeline <ArrowRight size={14} /> 已接入执行证据</span><span>CollaborationThread / AgentAssignment <ArrowRight size={14} /> 保留为本地演练</span><span>平台连接器 <ArrowRight size={14} /> 未接入，发布仅 simulated</span></div></section>
    </div>
  )
}

function DiagnosticCard({ icon, title, status, detail }: { icon: ReactNode; title: string; status: string; detail: string }) {
  return <article className="diagnostic-card"><div>{icon}</div><span>{title}</span><strong>{status}</strong><p>{detail}</p></article>
}

function RolePlaceholder({ role, onDiagnostics }: { role: RoleKey; onDiagnostics: () => void }) {
  return (
    <div className="page-container role-placeholder">
      <div className="role-placeholder-mark"><UserRound size={34} /></div>
      <span className="eyebrow">role experience pending</span>
      <h1>{roleCopy[role].label}界面尚未展开</h1>
      <p>{roleCopy[role].responsibility}</p>
      <div><ShieldCheck size={18} /><span>{roleCopy[role].boundary}</span></div>
      <button className="secondary-button" onClick={onDiagnostics}>查看当前演示边界 <ArrowRight size={15} /></button>
    </div>
  )
}

function EmptyState({ icon, title, body, action }: { icon: ReactNode; title: string; body: string; action?: ReactNode }) {
  return <div className="empty-state"><div>{icon}</div><strong>{title}</strong><p>{body}</p>{action}</div>
}

export default App
