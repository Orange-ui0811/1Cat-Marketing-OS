import {
  useEffect, useMemo, useState, type FormEvent, type ReactNode,
} from 'react'
import {
  Activity, AlertTriangle, ArrowRight, Bot, Box, CalendarDays, CheckCircle2, ChevronRight,
  CirclePause, ClipboardCheck, Clock3, Database, Download, ExternalLink, FileText, Gauge,
  GitBranch, History, KeyRound, LayoutDashboard, LogOut, Menu, MessageSquareText, Plus,
  RefreshCw, Save, Search, Send, Settings, ShieldCheck, Sparkles, UserCheck, Wrench, X,
} from 'lucide-react'
import {
  type AgentProfile, type LocalModelStatus, type MarketingCase, type MarketingCaseResource,
  localModelAdmin,
} from './runtimeApi'
import { RuntimeWorkspaceProvider, useRuntimeWorkspace, type RunEvidence } from './RuntimeWorkspaceContext'

type ViewKey = 'tasks' | 'collaboration' | 'objects' | 'reviews' | 'holds' | 'daily' | 'agent_config' | 'diagnostics'

const NAV: Array<{ key: ViewKey; label: string; icon: typeof LayoutDashboard }> = [
  { key: 'tasks', label: '任务中心', icon: LayoutDashboard },
  { key: 'collaboration', label: '协作中心', icon: MessageSquareText },
  { key: 'objects', label: '业务对象', icon: Box },
  { key: 'reviews', label: '决策台账', icon: ClipboardCheck },
  { key: 'holds', label: '异常处置', icon: CirclePause },
  { key: 'daily', label: 'Daily Brief', icon: CalendarDays },
  { key: 'agent_config', label: 'Agent 配置', icon: Settings },
  { key: 'diagnostics', label: '运行诊断', icon: Gauge },
]

const STAGE_LABELS: Record<string, string> = {
  brief: '创建 Brief', mo_plan: 'MO 规划', pma: 'PMA Fact / Claim', product_review: '人工产品审核',
  bga: 'BGA Campaign / Content', content_review: '人工内容审核', simulated_publish: '模拟人工发布',
  feedback: '合成 Lead / 销售反馈', mo_retrospective: 'MO 复盘',
}

const PLATFORM_LABELS: Record<string, string> = {
  bilibili: '哔哩哔哩', douyin: '抖音', xiaohongshu: '小红书', wechat_official: '微信公众号',
}

const ACTION_HOME: Record<string, ViewKey> = {
  approve_mo_plan: 'reviews', return_mo_plan: 'reviews', approve_product: 'reviews', return_product: 'reviews',
  approve_content: 'reviews', return_content: 'reviews', accept_retrospective: 'reviews', return_retrospective: 'reviews',
  hold_case: 'reviews', takeover_case: 'reviews', retry_safe_step: 'holds', resume_case: 'holds',
  resolve_unknown: 'holds', cancel_case: 'holds',
}

function dateTime(value?: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(new Date(value))
}

function statusLabel(value: string) {
  return ({
    active: '可推进', running: '执行中', awaiting_human: '待人工', blocked: '已阻塞', completed: '已完成',
    cancelled: '已取消', pending: '等待中', ready: '可开始', evidence_accepted: '证据已接受', unknown: '结果未知',
    draft: '草稿', accepted: '已确认', published: '已发布', validated: '已校验', simulated: '模拟完成',
  } as Record<string, string>)[value] || value
}

function PageTitle({ eyebrow, title, body, action }: { eyebrow: string; title: string; body: string; action?: ReactNode }) {
  return <header className="server-page-title"><div><span>{eyebrow}</span><h1>{title}</h1><p>{body}</p></div>{action}</header>
}

function StatusPill({ value }: { value: string }) {
  return <span className={`server-status ${value}`}>{statusLabel(value)}</span>
}

function Empty({ title, body }: { title: string; body: string }) {
  return <div className="server-empty"><Database size={28} /><strong>{title}</strong><p>{body}</p></div>
}

function Login() {
  const { login, busy, error } = useRuntimeWorkspace()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault()
    try { await login(username, password) } catch { /* context renders the error */ }
  }
  return <main className="server-login">
    <section className="server-login-copy"><span>1CAT · SERVER WORKSPACE</span><h1>营销组织运行台</h1><p>八类页面直接操作同一套服务端案例、任务、人工门禁和运行证据。</p><div><ShieldCheck size={18} />发布仍为 simulated · 无真实平台写入 · 无 PII</div></section>
    <form onSubmit={submit}><h2>登录 Runtime</h2><label>用户名<input value={username} onChange={event => setUsername(event.target.value)} /></label><label>密码<input type="password" value={password} onChange={event => setPassword(event.target.value)} autoFocus /></label>{error && <p className="server-error"><AlertTriangle size={14} />{error}</p>}<button disabled={busy || !password}>{busy ? '正在验证…' : '进入八类工作台'}</button></form>
  </main>
}

function GlobalCaseBar({ onNew }: { onNew: () => void }) {
  const { cases, current, selectCase, refresh, loading, logout } = useRuntimeWorkspace()
  return <section className="server-case-bar">
    <div className="server-case-identity"><span>当前案例</span><strong>{current?.title || '尚未建立案例'}</strong><small>{current?.id || '从任务中心建立第一个 Brief'}</small></div>
    <div><span>阶段</span><strong>{current ? STAGE_LABELS[current.current_stage] : '—'}</strong><small>{current ? `v${current.version}` : '—'}</small></div>
    <div><span>状态</span>{current ? <StatusPill value={current.status} /> : <strong>—</strong>}<small>{current ? PLATFORM_LABELS[current.target_platform] : '—'}</small></div>
    <label><History size={14} /><span>案例历史</span><select value={current?.id || ''} disabled={!cases.length} onChange={event => void selectCase(event.target.value)}><option value="" disabled>选择案例</option>{cases.map(item => <option key={item.id} value={item.id}>{item.title} · {statusLabel(item.status)}</option>)}</select></label>
    <div className="server-case-actions"><button onClick={onNew}><Plus size={14} />新建案例</button><button title="刷新服务端状态" onClick={() => void refresh()} disabled={loading}><RefreshCw size={14} className={loading ? 'spin' : ''} /></button><button title="退出" onClick={logout}><LogOut size={14} /></button></div>
  </section>
}

function CreateCaseDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { createCase, model, busy, error } = useRuntimeWorkspace()
  const [title, setTitle] = useState('Agent Runtime 开发者内容方案')
  const [objective, setObjective] = useState('形成一套可审核、可追踪、可直接执行的开发者营销内容方案。')
  const [brief, setBrief] = useState('围绕 Agent Runtime 的状态持久化、故障恢复、人工门禁和可观测性形成单平台内容；不使用 PII，不访问真实平台。')
  const [source, setSource] = useState('synthetic://workspace/brief-v1')
  const [platform, setPlatform] = useState('bilibili')
  const [mode, setMode] = useState<'synthetic' | 'real'>('synthetic')
  if (!open) return null
  async function submit(event: FormEvent) {
    event.preventDefault()
    try { await createCase({ title, objective, brief_body: brief, source_refs: [source], target_platform: platform, execution_mode: mode }); onClose() } catch { /* rendered globally */ }
  }
  return <div className="server-modal" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}><form className="server-dialog create" onSubmit={submit}><header><div><span>NEW MARKETING CASE</span><h2>建立新任务与 Brief</h2></div><button type="button" onClick={onClose}><X size={17} /></button></header><div className="server-form-grid"><label>案例标题<input value={title} onChange={event => setTitle(event.target.value)} required /></label><label>目标平台<select value={platform} onChange={event => setPlatform(event.target.value)}>{Object.entries(PLATFORM_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="full">业务目标<textarea value={objective} onChange={event => setObjective(event.target.value)} required /></label><label className="full">Brief 正文<textarea value={brief} onChange={event => setBrief(event.target.value)} required /></label><label>SourceRef<input value={source} onChange={event => setSource(event.target.value)} required /></label><label>执行模式<select value={mode} onChange={event => setMode(event.target.value as 'synthetic' | 'real')}><option value="synthetic">合成模式</option><option value="real">真实 DeepSeek</option></select></label></div>{mode === 'real' && <p className="server-warning"><AlertTriangle size={14} />将执行四次真实模型调用；当前状态：{model?.execution_enabled ? '已连通' : '未启用'}</p>}{error && <p className="server-error"><AlertTriangle size={14} />{error}</p>}<footer><button type="button" onClick={onClose}>取消</button><button className="primary" disabled={busy || (mode === 'real' && !model?.execution_enabled)}>{busy ? '正在创建…' : '创建案例'}</button></footer></form></div>
}

function StageStrip({ item }: { item: MarketingCase }) {
  return <ol className="server-stage-strip">{item.stages.map(stage => <li key={stage.id} className={`${stage.status} ${item.current_stage === stage.step_key ? 'current' : ''}`}><span>{stage.ordinal}</span><div><strong>{STAGE_LABELS[stage.step_key]}</strong><small>{statusLabel(stage.status)}</small></div></li>)}</ol>
}

function TaskAction({ action }: { action: { action: string; label: string } }) {
  const { command, busy } = useRuntimeWorkspace()
  const [note, setNote] = useState(action.action === 'record_simulated_publish' ? '演示流程，未登录或写入真实平台' : '')
  async function execute() {
    const payload = action.action === 'record_simulated_publish' ? { note }
      : action.action === 'record_synthetic_feedback' ? { touchpoint: 'workspace', inquiry_status: 'valid', reason_code: 'synthetic_demo_signal' }
        : {}
    try { await command(action.action, payload) } catch { /* context renders error */ }
  }
  return <article className="server-action-card"><div><span>{action.action.startsWith('start_') ? <Bot size={17} /> : <UserCheck size={17} />}</span><div><strong>{action.label}</strong><small>{action.action.startsWith('start_') ? '创建 Commitment 和 Run，由 Worker 执行' : action.action === 'record_simulated_publish' ? '填写人工任务回执，不访问真实平台' : '登记服务端业务事实'}</small></div></div>{action.action === 'record_simulated_publish' && <textarea value={note} onChange={event => setNote(event.target.value)} aria-label="模拟发布说明" />}<button disabled={busy} onClick={() => void execute()}>{busy ? '处理中…' : '执行任务'}<ArrowRight size={14} /></button></article>
}

function TaskPage({ onNew, navigate }: { onNew: () => void; navigate: (view: ViewKey) => void }) {
  const { current, error } = useRuntimeWorkspace()
  if (!current) return <section className="server-page"><PageTitle eyebrow="HUMAN RESPONSIBILITY DESK" title="任务中心" body="创建 Brief，并处理服务端分配给你的真实任务。" action={<button className="server-primary" onClick={onNew}><Plus size={15} />新建营销任务</button>} /><Empty title="还没有营销案例" body="建立第一个 Brief 后，MO、PMA、BGA、发布和反馈任务会依次出现在这里。" /></section>
  const operational = current.next_actions.filter(action => !ACTION_HOME[action.action])
  const activeStage = current.stages.find(stage => stage.step_key === current.current_stage)
  const manualTasks = current.resources.filter(ref => ref.resource_type === 'manual_task')
  return <section className="server-page"><PageTitle eyebrow="HUMAN RESPONSIBILITY DESK" title="任务中心" body="启动 Agent、执行人工发布任务、登记反馈；页面只允许服务端状态机认可的操作。" action={<button className="server-primary" onClick={onNew}><Plus size={15} />新建营销任务</button>} /><StageStrip item={current} />{error && <p className="server-error"><AlertTriangle size={14} />{error}</p>}<div className="server-task-grid"><main><header className="server-section-head"><div><span>01</span><h2>现在需要处理</h2></div><small>{operational.length} 项</small></header>{current.status === 'running' && <div className="server-running"><Clock3 size={20} /><div><strong>Agent 正在执行</strong><p>{STAGE_LABELS[current.current_stage]} · Run {activeStage?.active_run_id?.slice(0, 14)}</p></div><button onClick={() => navigate('diagnostics')}>查看运行证据</button></div>}{operational.map(action => <TaskAction key={action.action} action={action} />)}{!operational.length && current.status !== 'running' && <Empty title="当前没有执行任务" body={current.status === 'awaiting_human' ? '当前阶段需要正式决策，请前往决策台账。' : current.status === 'blocked' ? '当前案例已阻塞，请前往异常处置。' : current.status === 'completed' ? '案例已完成，可在业务对象查看最终方案。' : '等待服务端生成下一项任务。'} />}</main><aside><header className="server-section-head"><div><span>02</span><h2>人工发布任务</h2></div><small>{manualTasks.length} 项</small></header>{manualTasks.map(ref => <ResourceSummary key={ref.id} ref={ref} />)}{!manualTasks.length && <p className="server-muted">内容审核通过后，Runtime 才会创建人工发布任务。</p>}<header className="server-section-head compact"><div><span>03</span><h2>任务边界</h2></div></header><div className="server-boundary"><ShieldCheck size={18} /><p>本阶段发布只记录 simulated 回执，明确 <code>external_effect=false</code>；不会登录或写入真实平台。</p></div></aside></div></section>
}

function ResourceSummary({ ref }: { ref: MarketingCaseResource }) {
  const value = ref.resource || {}
  return <article className="server-resource-summary"><header><span>{ref.resource_type}</span><StatusPill value={String(value.status || 'recorded')} /></header><strong>{String(value.title || value.purpose || value.task_type || value.kind || ref.relation)}</strong><p>{String(value.instructions || value.reason_code || value.body || ref.relation).slice(0, 220)}</p><small>{ref.resource_id} {value.version ? `· v${value.version}` : ''}</small></article>
}

function CollaborationPage() {
  const { current, sendMessage, busy } = useRuntimeWorkspace()
  const [channel, setChannel] = useState<'MO' | 'PMA' | 'BGA'>('MO')
  const [body, setBody] = useState('')
  const [intent, setIntent] = useState<'message' | 'change_request'>('message')
  if (!current) return <section className="server-page"><PageTitle eyebrow="ROLE COLLABORATION" title="协作中心" body="查看真实岗位承诺、交接和沟通记录。" /><Empty title="请先建立案例" body="协作记录以 Marketing Case 为边界持久化。" /></section>
  const messages = current.messages.filter(item => item.channel === channel)
  const commitments = current.resources.filter(ref => ref.resource_type === 'commitment')
  const handoffs = current.resources.filter(ref => ref.resource_type === 'handoff')
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!body.trim()) return
    try { await sendMessage({ channel, body: body.trim(), intent }); setBody('') } catch { /* context error */ }
  }
  return <section className="server-page collaboration"><PageTitle eyebrow="ROLE COLLABORATION" title="协作中心" body="MO 主线程连接 PMA、BGA 子线程；消息、Commitment 和 Handoff 全部是服务端事实。" /><div className="server-collaboration-layout"><aside><h2>岗位频道</h2>{(['MO', 'PMA', 'BGA'] as const).map(value => <button key={value} className={channel === value ? 'active' : ''} onClick={() => setChannel(value)}><span>{value}</span><div><strong>{value === 'MO' ? 'Marketing Orchestrator' : value === 'PMA' ? 'Product Marketing Agent' : 'Brand & Growth Agent'}</strong><small>{current.messages.filter(item => item.channel === value).length} 条记录</small></div><ChevronRight size={15} /></button>)}<h3>岗位承诺</h3>{commitments.map(ref => <ResourceSummary key={ref.id} ref={ref} />)}<h3>岗位交接</h3>{handoffs.map(ref => <ResourceSummary key={ref.id} ref={ref} />)}</aside><main><header><div><span>{channel}</span><h2>{current.title}</h2></div><StatusPill value={current.status} /></header><div className="server-message-list">{messages.map(message => <article key={message.id} className={message.sender_type}><span>{message.sender_type === 'human' ? '你' : message.sender_type === 'system' ? 'SYS' : channel}</span><div><header><strong>{message.created_by}</strong><time>{dateTime(message.created_at)}</time>{message.intent === 'change_request' && <em>变更请求</em>}</header><p>{message.body}</p><small>{STAGE_LABELS[message.stage_key || ''] || message.stage_key}</small></div></article>)}{!messages.length && <Empty title="这个频道还没有消息" body="你可以补充背景或提交任务变更请求；它们会持久化到当前案例。" />}</div><form className="server-composer" onSubmit={submit}><div><button type="button" className={intent === 'message' ? 'active' : ''} onClick={() => setIntent('message')}>普通沟通</button><button type="button" className={intent === 'change_request' ? 'active' : ''} onClick={() => setIntent('change_request')}>任务变更</button></div><textarea value={body} onChange={event => setBody(event.target.value)} placeholder={intent === 'change_request' ? '说明需要修改的目标、范围、证据或交付物…' : `向 ${channel} 补充上下文…`} /><button disabled={busy || !body.trim()}><Send size={15} />发送</button></form></main></div></section>
}

function Deliverable({ item }: { item: MarketingCase }) {
  const deliverable = item.final_deliverable
  if (!deliverable) return <Empty title="最终方案尚未生成" body="MO 复盘成功后，系统会组装可追溯的完整营销方案。" />
  function download() {
    const blob = new Blob([deliverable!.markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a')
    anchor.href = url; anchor.download = `${item.title.replace(/[\\/:*?"<>|]/g, '-')}-完整营销方案.md`; anchor.click(); URL.revokeObjectURL(url)
  }
  return <article className="server-deliverable"><header><div><span>FINAL DELIVERABLE</span><h2>{deliverable.title}</h2><small>{deliverable.format_version} · v{deliverable.version} · {deliverable.document.sections.length} 个章节</small></div><div><StatusPill value={deliverable.status} /><button onClick={download}><Download size={14} />下载 Markdown</button></div></header>{item.deliverable_history?.length > 0 && <details className="server-deliverable-history"><summary><History size={13} />方案版本历史 <span>{item.deliverable_history.length}</span></summary><div>{item.deliverable_history.map(revision => <article key={revision.id}><strong>v{revision.version_no} · {statusLabel(revision.status)}</strong><small>{revision.created_by} · {dateTime(revision.created_at)}</small><code>{revision.content_hash.slice(0, 12)}</code></article>)}</div></details>}<nav>{deliverable.document.sections.map((section, index) => <a key={section.key} href={`#result-${section.key}`}>{index + 1}. {section.title}</a>)}</nav><div>{deliverable.document.sections.map((section, index) => <section id={`result-${section.key}`} key={section.key}><span>{String(index + 1).padStart(2, '0')}</span><article><h3>{section.title}</h3><p>{section.content}</p>{section.source_refs.length > 0 && <small>来源：{section.source_refs.map(ref => `${ref.kind || ref.type}:${ref.id.slice(0, 10)}@v${ref.version || '-'}`).join(' · ')}</small>}</article></section>)}</div><footer><ShieldCheck size={14} />发布 simulated · external_effect=false · 不声明真实营销效果</footer></article>
}

function ObjectsPage() {
  const { current } = useRuntimeWorkspace()
  const [kind, setKind] = useState('all')
  if (!current) return <section className="server-page"><PageTitle eyebrow="BUSINESS OBJECT REGISTRY" title="业务对象" body="查看完整结果、对象版本与来源。" /><Empty title="暂无业务对象" body="请先在任务中心建立案例。" /></section>
  const knowledge = current.resources.filter(ref => ref.resource_type === 'knowledge')
  const kinds = [...new Set(knowledge.map(ref => String(ref.resource?.kind || 'knowledge')))]
  const visible = kind === 'all' ? knowledge : knowledge.filter(ref => ref.resource?.kind === kind)
  return <section className="server-page"><PageTitle eyebrow="BUSINESS OBJECT REGISTRY" title="业务对象" body="阅读 Agent 产出的完整正文、版本与来源；最终营销方案也在这里归档和下载。" /><Deliverable item={current} /><section className="server-object-registry"><header className="server-section-head"><div><span>OBJECTS</span><h2>案例对象与版本</h2></div><label><Search size={14} /><select value={kind} onChange={event => setKind(event.target.value)}><option value="all">全部类型</option>{kinds.map(value => <option key={value} value={value}>{value}</option>)}</select></label></header><div className="server-object-grid">{visible.map(ref => { const item = ref.resource || {}; return <article key={ref.id} className={item.status === 'returned' ? 'returned' : ''}><header><span>{String(item.kind || ref.resource_type).toUpperCase()}</span><StatusPill value={String(item.status || 'candidate')} /></header><h3>{String(item.title || ref.relation)}</h3><p>{String(item.body || '')}</p><footer><span>{ref.resource_id}</span><span>v{String(item.version || ref.resource_version || 1)}</span><span>{String(item.created_by || '')}</span></footer>{Array.isArray(item.source_refs) && item.source_refs.length > 0 && <details><summary>查看来源</summary><pre>{JSON.stringify(item.source_refs, null, 2)}</pre></details>}</article>})}</div></section><section className="server-related-objects"><h2>发布、Lead 与反馈</h2>{current.resources.filter(ref => ['manual_task', 'lead', 'sales_feedback'].includes(ref.resource_type)).map(ref => <ResourceSummary key={ref.id} ref={ref} />)}</section></section>
}

function DecisionDialog({ action, onClose }: { action: { action: string; label: string }; onClose: () => void }) {
  const { command, busy } = useRuntimeWorkspace()
  const [reason, setReason] = useState(action.action.startsWith('approve') || action.action === 'accept_retrospective' ? '已核对当前对象正文、来源与版本，同意进入下一阶段。' : '')
  async function submit(event: FormEvent) {
    event.preventDefault()
    try { await command(action.action, { reason }); onClose() } catch { /* context error */ }
  }
  return <div className="server-modal"><form className="server-dialog decision" onSubmit={submit}><header><div><span>HUMAN GATE</span><h2>{action.label}</h2></div><button type="button" onClick={onClose}><X size={17} /></button></header><p>决定将绑定当前案例、阶段及对象版本，提交后不可从审计历史中删除。</p><label>决策理由<textarea value={reason} onChange={event => setReason(event.target.value)} autoFocus /></label><footer><button type="button" onClick={onClose}>取消</button><button className={action.action.startsWith('return_') || action.action.includes('hold') || action.action.includes('takeover') ? 'danger' : 'primary'} disabled={busy || reason.trim().length < 2}>{busy ? '正在记录…' : '确认并记录'}</button></footer></form></div>
}

function ReviewsPage() {
  const { current } = useRuntimeWorkspace()
  const [selected, setSelected] = useState<{ action: string; label: string } | null>(null)
  if (!current) return <section className="server-page"><PageTitle eyebrow="DECISION REGISTER" title="决策台账" body="执行人工门禁并查看不可覆盖的决策历史。" /><Empty title="暂无决策案例" body="请先建立案例。" /></section>
  const actions = current.next_actions.filter(action => ACTION_HOME[action.action] === 'reviews')
  const gateProducer = current.current_stage === 'product_review' ? 'pma' : current.current_stage === 'content_review' ? 'bga' : current.current_stage
  const subjects = current.resources.filter(ref => ref.resource_type === 'knowledge' && ref.resource?.metadata?.stage_key === gateProducer && ref.resource?.status !== 'returned')
  const approvals = current.resources.filter(ref => ref.resource_type === 'approval')
  return <section className="server-page"><PageTitle eyebrow="DECISION REGISTER" title="决策台账" body="先审阅正文和版本，再批准、退回、HOLD 或接管；正式理由永久保留。" /><div className="server-review-layout"><main><header className="server-section-head"><div><span>CURRENT GATE</span><h2>{STAGE_LABELS[current.current_stage]}</h2></div><StatusPill value={current.status} /></header>{subjects.map(ref => <ResourceSummary key={ref.id} ref={ref} />)}{current.final_deliverable && current.current_stage === 'mo_retrospective' && <div className="server-final-preview"><FileText size={20} /><div><strong>{current.final_deliverable.title}</strong><p>{current.final_deliverable.document.sections.length} 个章节 · v{current.final_deliverable.version}</p></div></div>}<div className="server-decision-actions">{actions.map(action => <button key={action.action} className={action.action.startsWith('return_') || action.action.includes('hold') || action.action.includes('takeover') ? 'danger' : 'primary'} onClick={() => setSelected(action)}>{action.label}</button>)}</div>{!actions.length && <Empty title="当前没有待决策门禁" body="需要人工判断时，服务端允许动作会出现在这里。" />}</main><aside><header className="server-section-head"><div><span>HISTORY</span><h2>正式决策历史</h2></div><small>{current.decisions.length} 条</small></header>{[...current.decisions].reverse().map(item => <article className="server-decision-record" key={item.id}><header><StatusPill value={item.decision} /><time>{dateTime(item.created_at)}</time></header><strong>{STAGE_LABELS[item.stage_key]}</strong><p>{item.reason}</p><small>{item.actor_id} · {item.subject_refs.length} 个对象版本</small></article>)}{!current.decisions.length && <p className="server-muted">尚无正式决策。</p>}<h3>Approval Grants</h3>{approvals.map(ref => <ResourceSummary key={ref.id} ref={ref} />)}</aside></div>{selected && <DecisionDialog action={selected} onClose={() => setSelected(null)} />}</section>
}

function ReconcileForm() {
  const { command, busy } = useRuntimeWorkspace()
  const [resolution, setResolution] = useState('confirmed_failed')
  const [note, setNote] = useState('已核对 Run、Attempt 与外部执行记录，确认本次执行未产生可接受结果。')
  async function submit(event: FormEvent) { event.preventDefault(); try { await command('resolve_unknown', { resolution, note, evidence: { checked_by: 'workspace-human' } }) } catch { /* context error */ } }
  return <form className="server-reconcile" onSubmit={submit}><h3>Unknown 人工对账</h3><label>对账结论<select value={resolution} onChange={event => setResolution(event.target.value)}><option value="confirmed_failed">确认失败，可安全重试</option><option value="confirmed_cancelled">确认已取消，可安全重试</option><option value="confirmed_succeeded">确认成功，继续校验证据</option><option value="abandoned">放弃并取消案例</option></select></label><label>核对依据<textarea value={note} onChange={event => setNote(event.target.value)} /></label><button disabled={busy || note.trim().length < 2}>提交对账结论</button></form>
}

function HoldsPage() {
  const { cases, current, selectCase, command, busy } = useRuntimeWorkspace()
  const blocked = cases.filter(item => item.status === 'blocked')
  const actions = current?.next_actions.filter(action => ACTION_HOME[action.action] === 'holds') || []
  const activeStep = current?.stages.find(stage => stage.step_key === current.current_stage)
  return <section className="server-page"><PageTitle eyebrow="EXCEPTION DESK" title="异常处置" body="处理阻塞、Unknown、人工暂停、恢复、安全重试和取消。" /><div className="server-hold-layout"><aside><h2>阻塞案例</h2>{blocked.map(item => <button className={current?.id === item.id ? 'active' : ''} key={item.id} onClick={() => void selectCase(item.id)}><AlertTriangle size={17} /><span><strong>{item.title}</strong><small>{STAGE_LABELS[item.current_stage]} · {item.id.slice(0, 14)}</small></span></button>)}{!blocked.length && <p className="server-muted">最近案例中没有阻塞项。</p>}</aside><main>{current?.status === 'blocked' ? <><header><div><span>当前阻塞</span><h2>{current.title}</h2></div><StatusPill value={current.status} /></header><pre>{JSON.stringify(activeStep?.failure || {}, null, 2)}</pre>{activeStep?.failure?.run_status === 'unknown' && <ReconcileForm />}<div className="server-hold-actions">{actions.filter(action => action.action !== 'resolve_unknown').map(action => <button key={action.action} className={action.action === 'cancel_case' ? 'danger' : 'primary'} disabled={busy} onClick={() => void command(action.action, { reason: action.label })}>{action.label}</button>)}</div><section><h3>处置历史</h3>{current.reconciliations.map(item => <article key={item.id}><strong>{item.resolution}</strong><p>{item.note}</p><small>{item.actor_id} · {dateTime(item.created_at)}</small></article>)}</section></> : current ? <><header><div><span>当前案例控制</span><h2>{current.title}</h2></div><StatusPill value={current.status} /></header><p className="server-muted">当前案例没有异常。若确认不再继续，可在这里执行服务端取消；已完成或已取消的案例不会再提供操作。</p><div className="server-hold-actions">{actions.map(action => <button key={action.action} className={action.action === 'cancel_case' ? 'danger' : 'primary'} disabled={busy} onClick={() => void command(action.action, { reason: action.label })}>{action.label}</button>)}</div>{!actions.length && <Empty title="当前案例没有异常" body="选择左侧阻塞案例，或在决策台账对当前案例执行 HOLD/接管。" />}</> : <Empty title="还没有案例" body="先在任务中心建立一个营销任务。" />}</main></div></section>
}

function DailyPage({ navigate }: { navigate: (view: ViewKey) => void }) {
  const { cases, current, selectCase } = useRuntimeWorkspace()
  const human = cases.filter(item => item.status === 'awaiting_human')
  const running = cases.filter(item => item.status === 'running')
  const blocked = cases.filter(item => item.status === 'blocked')
  const completed = cases.filter(item => item.status === 'completed')
  function open(item: MarketingCase, view: ViewKey) { void selectCase(item.id).then(() => navigate(view)) }
  return <section className="server-page"><PageTitle eyebrow="TODAY · SERVER FACTS" title="Daily Brief" body="聚合真实案例的人工待办、Agent 运行、异常和最新结果。" /><article className="server-daily"><header><div><span>1CAT / DAILY</span><h2>营销组织运行摘要</h2></div><strong>{human.length + blocked.length}<small>项需要人工</small></strong></header><DailyGroup number="01" title="等待你的判断" items={human} empty="当前没有待审批门禁" onOpen={item => open(item, 'reviews')} /><DailyGroup number="02" title="Agent 正在推进" items={running} empty="当前没有运行中的 Agent" onOpen={item => open(item, 'diagnostics')} /><DailyGroup number="03" title="异常与对账" items={blocked} empty="当前没有阻塞案例" onOpen={item => open(item, 'holds')} /><DailyGroup number="04" title="已完成方案" items={completed} empty="尚无已完成案例" onOpen={item => open(item, 'objects')} /><footer><ShieldCheck size={15} />本摘要完全来自服务端 Marketing Case；不再读取浏览器演示业务数据。</footer></article>{current?.final_deliverable && <section className="server-latest-result"><FileText size={20} /><div><span>当前案例最终方案</span><strong>{current.final_deliverable.title}</strong></div><button onClick={() => navigate('objects')}>查看结果</button></section>}</section>
}

function DailyGroup({ number, title, items, empty, onOpen }: { number: string; title: string; items: MarketingCase[]; empty: string; onOpen: (item: MarketingCase) => void }) {
  return <section><header><span>{number}</span><h3>{title}</h3><small>{items.length}</small></header><div>{items.map(item => <button key={item.id} onClick={() => onOpen(item)}><CirclePause size={14} /><span><strong>{item.title}</strong><small>{STAGE_LABELS[item.current_stage]} · {statusLabel(item.status)}</small></span><ChevronRight size={14} /></button>)}{!items.length && <p>{empty}</p>}</div></section>
}

function ModelConnection() {
  const [status, setStatus] = useState<LocalModelStatus | null>(null)
  const [key, setKey] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  async function refresh() { try { setStatus(await localModelAdmin.status()) } catch (reason) { setNotice(reason instanceof Error ? reason.message : '模型配置服务不可用') } }
  useEffect(() => { void refresh() }, [])
  async function save() { setBusy(true); setNotice(''); try { const next = await localModelAdmin.configure(key.trim() || undefined); setStatus(next); setKey(''); setNotice(next.message || 'DeepSeek 已验证并启用') } catch (reason) { setNotice(reason instanceof Error ? reason.message : '配置失败') } finally { setBusy(false) } }
  async function test() { setBusy(true); try { const next = await localModelAdmin.test(); setStatus(next); setNotice(next.message || '模型调用通过') } catch (reason) { setNotice(reason instanceof Error ? reason.message : '模型测试失败') } finally { setBusy(false) } }
  return <section className="server-model-connection"><header><KeyRound size={18} /><div><h2>DeepSeek 真实执行连接</h2><p>密钥只写入本机 Secret，不进入浏览器存储。</p></div><StatusPill value={status?.execution_enabled ? 'validated' : 'draft'} /></header><div><label>API Key<input type="password" value={key} onChange={event => setKey(event.target.value)} placeholder={status?.credential_configured ? '已保存；输入新 Key 可替换' : '输入 DeepSeek API Key'} /></label><button disabled={busy || (!key.trim() && !status?.credential_configured)} onClick={() => void save()}>保存并验证</button><button disabled={busy || !status?.execution_enabled} onClick={() => void test()}>测试调用</button></div>{notice && <p>{notice}</p>}</section>
}

function AgentConfigPage() {
  const { profiles, updateProfile, commandProfile, busy } = useRuntimeWorkspace()
  const [agent, setAgent] = useState<'MO' | 'PMA' | 'BGA'>('MO')
  const selected = profiles.find(item => item.agent_key === agent)
  const [draft, setDraft] = useState<Record<string, any>>({})
  useEffect(() => { if (selected) setDraft(structuredClone(selected.config)) }, [selected?.id, selected?.version])
  if (!selected) return <section className="server-page"><PageTitle eyebrow="AGENT PROFILE CONTROL" title="Agent 配置" body="管理真实生效的岗位配置版本。" /><Empty title="配置尚未加载" body="请确认 Runtime API 已升级到最新数据库版本。" /></section>
  const model = draft.model || {}
  return <section className="server-page"><PageTitle eyebrow="AGENT PROFILE CONTROL" title="Agent 配置" body="编辑、校验、发布和回滚服务端 Profile；新 Run 会使用已发布配置语义。" /><ModelConnection /><nav className="server-agent-tabs">{profiles.map(item => <button key={item.agent_key} className={agent === item.agent_key ? 'active' : ''} onClick={() => setAgent(item.agent_key)}><span>{item.agent_key}</span><div><strong>{String(item.config.role_name)}</strong><small>发布版本 {item.published_version}</small></div><StatusPill value={item.status} /></button>)}</nav><div className="server-config-layout"><main><header><div><span>{selected.agent_key} PROFILE</span><h2>{String(draft.role_name || selected.agent_key)}</h2></div><StatusPill value={selected.status} /></header><div className="server-form-grid"><label>模型<input value={String(model.model || '')} onChange={event => setDraft({ ...draft, model: { ...model, model: event.target.value } })} /></label><label>推理等级<select value={String(model.reasoning_level || 'low')} onChange={event => setDraft({ ...draft, model: { ...model, reasoning_level: event.target.value } })}><option value="low">low</option><option value="medium">medium</option><option value="high">high</option></select></label><label>最大轮数<input type="number" value={Number(model.max_turns || 1)} onChange={event => setDraft({ ...draft, model: { ...model, max_turns: Number(event.target.value) } })} /></label><label>超时秒数<input type="number" value={Number(model.timeout_seconds || 90)} onChange={event => setDraft({ ...draft, model: { ...model, timeout_seconds: Number(event.target.value) } })} /></label><label className="full">Memory 策略<textarea value={String(draft.memory_summary || '')} onChange={event => setDraft({ ...draft, memory_summary: event.target.value })} /></label></div><section className="server-config-facts"><div><span>岗位六件套</span><strong>{Array.isArray(draft.six_pack) ? draft.six_pack.length : 0}/6</strong></div><div><span>Skills</span><strong>{Array.isArray(draft.skills) ? draft.skills.filter((item: any) => item.enabled).length : 0}</strong></div><div><span>允许工具</span><strong>{Array.isArray(draft.permissions?.tools) ? draft.permissions.tools.length : 0}</strong></div></section><footer><button disabled={busy} onClick={() => void updateProfile(selected, draft, '八类工作台更新配置草稿')}><Save size={14} />保存草稿</button><button disabled={busy || selected.status !== 'draft'} onClick={() => void commandProfile(selected, 'validate')}><ShieldCheck size={14} />校验草稿</button><button className="primary" disabled={busy || selected.status !== 'validated'} onClick={() => void commandProfile(selected, 'publish')}><Sparkles size={14} />发布版本</button></footer></main><aside><h2>不可覆盖版本历史</h2>{selected.revisions.map(revision => <article key={revision.id}><header><strong>v{revision.version_no}</strong><StatusPill value={revision.status} /></header><p>{revision.summary}</p><small>{revision.created_by} · {dateTime(revision.created_at)}</small><button disabled={busy || revision.version_no === selected.published_version} onClick={() => void commandProfile(selected, 'rollback', revision.version_no)}>恢复为新草稿</button></article>)}</aside></div></section>
}

function DiagnosticsPage() {
  const { current, model, loadRunEvidence } = useRuntimeWorkspace()
  const [evidence, setEvidence] = useState<Record<string, RunEvidence>>({})
  const [loading, setLoading] = useState(false)
  const runRefs = current?.resources.filter(ref => ref.resource_type === 'run') || []
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all(runRefs.map(async ref => [ref.resource_id, await loadRunEvidence(ref.resource_id)] as const)).then(items => { if (!cancelled) setEvidence(Object.fromEntries(items)) }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [current?.id, current?.version])
  return <section className="server-page"><PageTitle eyebrow="RUNTIME OBSERVABILITY" title="运行诊断" body="查看真实 Run、Attempt、Lease、Heartbeat、状态迁移和 Trace。" /><div className="server-diagnostic-summary"><article><Activity size={18} /><span>Runtime</span><strong>已连接</strong><small>{current?.correlation_id || '尚无当前案例'}</small></article><article><Bot size={18} /><span>模型</span><strong>{model?.model || '未读取'}</strong><small>{model?.execution_enabled ? '真实执行可用' : '仅合成执行'}</small></article><article><GitBranch size={18} /><span>Runs</span><strong>{runRefs.length}</strong><small>{loading ? '正在读取证据' : 'Attempt 与 Timeline 已加载'}</small></article><article><ShieldCheck size={18} /><span>发布边界</span><strong>SIMULATED</strong><small>external_effect=false</small></article></div>{Object.values(evidence).map(value => <article className="server-run" key={value.run.id}><header><div><span>{String(value.run.profile_id).toUpperCase()} · {STAGE_LABELS[value.run.stage_key || '']}</span><h2>{value.run.id}</h2></div><StatusPill value={value.run.status} />{value.run.trace_id && <a href={`http://127.0.0.1:16686/trace/${value.run.trace_id}`} target="_blank" rel="noreferrer"><ExternalLink size={14} />打开 Trace</a>}</header><dl><div><dt>Correlation</dt><dd>{value.run.correlation_id}</dd></div><div><dt>Execution</dt><dd>{value.run.execution_mode}</dd></div><div><dt>Started</dt><dd>{dateTime(value.run.started_at)}</dd></div><div><dt>Completed</dt><dd>{dateTime(value.run.completed_at)}</dd></div></dl><div className="server-run-timeline">{value.timeline.map(event => <span key={event.id}><i /><strong>{event.to_status}</strong><small>{dateTime(event.created_at)}</small></span>)}</div><details open><summary>Attempt 历史 <span>{value.attempts.length}</span></summary>{value.attempts.map(attempt => <article className="server-attempt" key={attempt.id}><header><strong>Attempt {attempt.attempt_no}</strong><StatusPill value={attempt.status} /></header><dl><div><dt>Worker</dt><dd>{attempt.worker_id}</dd></div><div><dt>Heartbeat</dt><dd>{dateTime(attempt.heartbeat_at)}</dd></div><div><dt>Lease until</dt><dd>{dateTime(attempt.lease_until)}</dd></div><div><dt>Retryability</dt><dd>{attempt.retryability}</dd></div></dl>{(attempt.failure_class || Object.keys(attempt.failure || {}).length > 0) && <pre>{JSON.stringify({ failure_class: attempt.failure_class, ...attempt.failure }, null, 2)}</pre>}</article>)}</details></article>)}{!runRefs.length && <Empty title="当前案例还没有 Run" body="在任务中心启动 MO/PMA/BGA 后，执行证据会显示在这里。" />}</section>
}

function Shell() {
  const { authenticated, current } = useRuntimeWorkspace()
  const rawView = new URLSearchParams(window.location.search).get('view')
  const initial = NAV.some(item => item.key === rawView) ? rawView as ViewKey : 'tasks'
  const [view, setView] = useState<ViewKey>(initial)
  const [mobile, setMobile] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  if (!authenticated) return <Login />
  function navigate(next: ViewKey) {
    setView(next); setMobile(false)
    const url = new URL(window.location.href); url.searchParams.set('view', next); window.history.replaceState({}, '', url)
  }
  const pending = current?.status === 'awaiting_human' || current?.status === 'blocked' ? 1 : 0
  return <div className="app-shell server-workspace"><button className="server-mobile-menu" onClick={() => setMobile(true)}><Menu size={18} /></button>{mobile && <button className="nav-scrim" onClick={() => setMobile(false)} />}<aside className={`sidebar ${mobile ? 'sidebar-open' : ''}`}><header className="brand-block"><div className="brand-mark"><span>S2</span></div><div><strong>营销组织运行台</strong><small>server-backed workspace</small></div><button className="icon-button sidebar-close" onClick={() => setMobile(false)}><X size={17} /></button></header><div className="environment-note"><Activity size={14} /><div><strong>真实 Runtime</strong><small>八类页面统一服务端状态</small></div></div><nav className="main-nav"><p>工作台</p>{NAV.map(item => { const Icon = item.icon; return <button key={item.key} className={view === item.key ? 'active' : ''} onClick={() => navigate(item.key)}><Icon size={18} /><span>{item.label}</span>{item.key === 'tasks' && pending > 0 && <em>{pending}</em>}</button> })}</nav><footer className="sidebar-footer"><button onClick={() => setCreateOpen(true)}><Plus size={16} /><span>建立新营销任务</span></button><div className="boundary-line"><ShieldCheck size={14} /><span>平台发布 simulated · 人类最终决策</span></div></footer></aside><div className="main-area"><header className="server-topbar"><div><span>1Cat Marketing OS</span><ChevronRight size={13} /><strong>{NAV.find(item => item.key === view)?.label}</strong></div><span className="server-truth-badge"><Database size={13} />SERVER SOURCE OF TRUTH</span></header><main className="main-content server-main"><GlobalCaseBar onNew={() => setCreateOpen(true)} />{view === 'tasks' && <TaskPage onNew={() => setCreateOpen(true)} navigate={navigate} />}{view === 'collaboration' && <CollaborationPage />}{view === 'objects' && <ObjectsPage />}{view === 'reviews' && <ReviewsPage />}{view === 'holds' && <HoldsPage />}{view === 'daily' && <DailyPage navigate={navigate} />}{view === 'agent_config' && <AgentConfigPage />}{view === 'diagnostics' && <DiagnosticsPage />}</main></div><CreateCaseDialog open={createOpen} onClose={() => setCreateOpen(false)} /></div>
}

export default function ServerWorkspace() {
  return <RuntimeWorkspaceProvider><Shell /></RuntimeWorkspaceProvider>
}
