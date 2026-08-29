import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowLeft, Bot, Check, CheckCircle2, Clock3, ExternalLink,
  Download, FileCheck2, FileText, GitBranch, History, LogOut, Play, RefreshCw, ShieldCheck, UserCheck,
} from 'lucide-react'
import {
  AgentRun, MarketingCase, MarketingCaseResource, RunAttempt, RunTransition,
  RuntimeApiError, RuntimeModel, runtimeApi, runtimeSession,
} from './runtimeApi'

const STAGE_LABELS: Record<string, string> = {
  brief: '创建 Brief', mo_plan: 'MO 规划', pma: 'PMA Fact / Claim', product_review: '人工产品审核',
  bga: 'BGA Campaign / Content', content_review: '人工内容审核', simulated_publish: '模拟人工发布',
  feedback: '合成 Lead / 销售反馈', mo_retrospective: 'MO 复盘',
}
const PLATFORM_LABELS: Record<string, string> = {
  bilibili: '哔哩哔哩', douyin: '抖音', xiaohongshu: '小红书', wechat_official: '微信公众号',
}
const POLLABLE = new Set(['running'])
const JAEGER_URL = import.meta.env.VITE_JAEGER_URL || 'http://127.0.0.1:16686'
const STAGE_STATUS_LABELS: Record<string, string> = {
  pending: '等待前置阶段', ready: '可开始', running: 'Agent 执行中', awaiting_human: '等待人工确认',
  completed: '已完成', blocked: '已阻塞',
}
const RESOURCE_LABELS: Record<string, string> = {
  commitment: '岗位承诺', handoff: '岗位交接', approval: '人工审批', knowledge: '知识候选',
  manual_task: '人工发布任务', lead: '合成 Lead', sales_feedback: '销售反馈', deliverable: '最终营销方案',
}

type RunEvidence = { run: AgentRun; attempts: RunAttempt[]; timeline: RunTransition[] }

function formatTime(value?: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(new Date(value))
}

function WorkflowLogin({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try { await runtimeApi.login(username, password); onLogin() }
    catch (reason) { setError(reason instanceof Error ? reason.message : '登录失败') }
    finally { setBusy(false) }
  }
  return <main className="workflow-login">
    <section>
      <span className="workflow-eyebrow">THREE-AGENT · HUMAN-GATED</span>
      <h1>完整流程工作台</h1>
      <p>从 Brief 到 MO 复盘，以服务端事实连接 MO、PMA、BGA 与人工门禁。发布始终为模拟回执。</p>
      <div className="workflow-boundary"><ShieldCheck size={18} />无真实平台写入 · 无 PII · 不自动认定营销效果</div>
    </section>
    <form className="workflow-card workflow-login-card" onSubmit={submit}>
      <h2>登录 Runtime</h2>
      <label>用户名<input value={username} onChange={event => setUsername(event.target.value)} /></label>
      <label>密码<input type="password" value={password} onChange={event => setPassword(event.target.value)} /></label>
      {error && <p className="workflow-error"><AlertTriangle size={15} />{error}</p>}
      <button className="workflow-primary" disabled={busy || !password}>{busy ? '正在验证…' : '进入工作台'}</button>
      <a href="/?view=workspace"><ArrowLeft size={14} />返回八类业务页面</a>
    </form>
  </main>
}

function CreateCase({ model, onCreated }: { model: RuntimeModel | null; onCreated: (item: MarketingCase) => void }) {
  const [title, setTitle] = useState('开发者增长内容闭环')
  const [objective, setObjective] = useState('为 Agent Runtime 项目形成一组可审核、可追踪的开发者内容候选。')
  const [brief, setBrief] = useState('使用合成业务事实说明 Agent Runtime 的状态持久化、人工门禁与故障边界；不含 PII。')
  const [sourceRef, setSourceRef] = useState('synthetic://workflow-ui/brief-v1')
  const [platform, setPlatform] = useState('bilibili')
  const [mode, setMode] = useState<'synthetic' | 'real'>('synthetic')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      onCreated(await runtimeApi.createMarketingCase({
        title, objective, brief_body: brief, source_refs: [sourceRef], target_platform: platform, execution_mode: mode,
      }))
    } catch (reason) { setError(reason instanceof Error ? reason.message : '创建案例失败') }
    finally { setBusy(false) }
  }
  return <section className="workflow-card workflow-create">
    <div className="workflow-section-title"><span>NEW CASE</span><h2>建立营销案例</h2></div>
    <form onSubmit={submit}>
      <label>案例标题<input value={title} onChange={event => setTitle(event.target.value)} required /></label>
      <label>业务目标<textarea value={objective} onChange={event => setObjective(event.target.value)} required /></label>
      <label>Brief 正文<textarea value={brief} onChange={event => setBrief(event.target.value)} required /></label>
      <label>SourceRef<input value={sourceRef} onChange={event => setSourceRef(event.target.value)} required /></label>
      <div className="workflow-form-row">
        <label>目标平台<select value={platform} onChange={event => setPlatform(event.target.value)}>
          {Object.entries(PLATFORM_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
        <label>执行模式<select value={mode} onChange={event => setMode(event.target.value as 'synthetic' | 'real')}>
          <option value="synthetic">合成模式（默认）</option><option value="real">真实 DeepSeek</option>
        </select></label>
      </div>
      {mode === 'real' && <p className="workflow-mode-warning"><AlertTriangle size={15} />
        将产生 4 次 DeepSeek Agent Run；当前连通性：{model?.execution_enabled ? '已验证' : '未启用，提交会被拒绝'}。
      </p>}
      {error && <p className="workflow-error"><AlertTriangle size={15} />{error}</p>}
      <button className="workflow-primary" disabled={busy || (mode === 'real' && !model?.execution_enabled)}>
        {busy ? '正在创建…' : '创建并进入流程'}
      </button>
    </form>
  </section>
}

function StageStepper({ item }: { item: MarketingCase }) {
  return <ol className="workflow-stepper">
    {item.stages.map(stage => <li key={stage.id} className={`${stage.status} ${item.current_stage === stage.step_key ? 'current' : ''}`}>
      <div className="workflow-step-marker">{stage.status === 'completed' ? <Check size={14} /> : stage.ordinal}</div>
      <div><strong>{STAGE_LABELS[stage.step_key]}</strong><small>{STAGE_STATUS_LABELS[stage.status] || stage.status}</small></div>
      {stage.active_run_id && <code>{stage.active_run_id.slice(0, 8)}</code>}
    </li>)}
  </ol>
}

function AttemptEvidence({ attempt, current }: { attempt: RunAttempt; current: boolean }) {
  const hasOutput = Object.keys(attempt.output || {}).length > 0
  const hasFailure = Object.keys(attempt.failure || {}).length > 0 || Boolean(attempt.failure_class)
  return <article className={`workflow-attempt ${current ? 'current' : ''}`}>
    <header>
      <div><span>ATTEMPT {attempt.attempt_no}</span><strong>{attempt.status}</strong></div>
      <small>{current ? '当前不可覆盖记录' : '历史不可覆盖记录'}</small>
    </header>
    <dl>
      <div><dt>Worker</dt><dd>{attempt.worker_id || '—'}</dd></div>
      <div><dt>Hermes Run</dt><dd>{attempt.hermes_run_id || '未派发'}</dd></div>
      <div><dt>Retryability</dt><dd>{attempt.retryability || '—'}</dd></div>
      <div><dt>Heartbeat</dt><dd>{formatTime(attempt.heartbeat_at)}</dd></div>
      <div><dt>Lease until</dt><dd>{formatTime(attempt.lease_until)}</dd></div>
      <div><dt>Completed</dt><dd>{formatTime(attempt.completed_at)}</dd></div>
    </dl>
    {hasOutput && <details><summary>Attempt 输出</summary><pre>{JSON.stringify(attempt.output, null, 2)}</pre></details>}
    {hasFailure && <details open><summary>故障事实</summary><pre>{JSON.stringify({ failure_class: attempt.failure_class, ...attempt.failure }, null, 2)}</pre></details>}
  </article>
}

function ResourceCard({ ref }: { ref: MarketingCaseResource }) {
  const item = ref.resource || {}
  const title = item.title || item.purpose || item.task_type || item.kind || item.id || ref.resource_id
  const detail = item.body || item.objective || item.instructions || item.reason_code || item.status || ref.relation
  return <article className="workflow-resource">
    <header><span>{ref.resource_type}</span><small>{ref.relation}</small></header>
    <strong>{String(title)}</strong>
    <p>{typeof detail === 'string' ? detail : JSON.stringify(detail)}</p>
    {item.receipt && Object.keys(item.receipt).length > 0 && <p className="workflow-receipt">回执 · {JSON.stringify(item.receipt)}</p>}
    <footer><code>{ref.resource_id.slice(0, 12)}</code>{item.version && <span>v{item.version}</span>}</footer>
  </article>
}

function FinalDeliverablePanel({ item }: { item: MarketingCase }) {
  const deliverable = item.final_deliverable
  if (!deliverable) return null
  const sections = deliverable.document?.sections || []
  const downloadMarkdown = () => {
    const blob = new Blob([deliverable.markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${item.title.replace(/[\\/:*?"<>|]/g, '-')}-完整营销方案.md`
    anchor.click()
    URL.revokeObjectURL(url)
  }
  return <article className="workflow-card workflow-deliverable">
    <header>
      <div><span>FINAL DELIVERABLE</span><h2><FileText size={18} />{deliverable.title}</h2></div>
      <div className="workflow-deliverable-actions">
        <span className={`deliverable-status ${deliverable.status}`}>{deliverable.status === 'accepted' ? '人工已确认' : '等待人工确认'}</span>
        <button onClick={downloadMarkdown}><Download size={14} />下载 Markdown</button>
      </div>
    </header>
    <p className="workflow-deliverable-meta">
      {deliverable.format_version} · v{deliverable.version} · {sections.length} 个章节 · {deliverable.source_refs.length} 个知识来源
      {deliverable.accepted_at ? ` · ${formatTime(deliverable.accepted_at)} 确认` : ''}
    </p>
    <nav>{sections.map((section, index) => <a key={section.key} href={`#deliverable-${section.key}`}>{index + 1}. {section.title}</a>)}</nav>
    <div className="workflow-document">
      {sections.map((section, index) => <section key={section.key} id={`deliverable-${section.key}`}>
        <span>{String(index + 1).padStart(2, '0')}</span>
        <div><h3>{section.title}</h3><p>{section.content}</p>
          {section.source_refs?.length > 0 && <small>来源 · {section.source_refs.map(ref => `${ref.kind || ref.type}:${ref.id.slice(0, 10)}@v${ref.version || '-'}`).join(' · ')}</small>}
        </div>
      </section>)}
    </div>
    <footer><ShieldCheck size={14} />方案已持久化并可追溯；发布 simulated，external_effect=false。</footer>
  </article>
}

function CaseWorkspace({ initial, onLogout, onNew }: { initial: MarketingCase; onLogout: () => void; onNew: () => void }) {
  const [item, setItem] = useState(initial)
  const [recent, setRecent] = useState<MarketingCase[]>([])
  const [evidence, setEvidence] = useState<Record<string, RunEvidence>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const loadCase = useCallback(async (id: string) => {
    try {
      const next = await runtimeApi.getMarketingCase(id)
      setItem(next); runtimeSession.rememberCase(next.id); setError('')
      const runs = next.resources.filter(ref => ref.resource_type === 'run' && ref.resource)
      const pairs = await Promise.all(runs.map(async ref => {
        const runId = ref.resource_id
        const [run, attempts, timeline] = await Promise.all([
          runtimeApi.getRun(runId), runtimeApi.getAttempts(runId), runtimeApi.getTimeline(runId),
        ])
        return [runId, { run, attempts, timeline }] as const
      }))
      setEvidence(Object.fromEntries(pairs))
    } catch (reason) {
      if (reason instanceof RuntimeApiError && reason.status === 401) onLogout()
      setError(reason instanceof Error ? reason.message : '刷新失败')
    }
  }, [onLogout])

  const loadRecent = useCallback(async () => {
    try { setRecent(await runtimeApi.listMarketingCases()) }
    catch (reason) { if (reason instanceof RuntimeApiError && reason.status === 401) onLogout() }
  }, [onLogout])

  useEffect(() => { void loadRecent(); void loadCase(initial.id) }, [initial.id, loadCase, loadRecent])
  useEffect(() => {
    if (!POLLABLE.has(item.status)) return
    const timer = window.setInterval(() => void loadCase(item.id), 2000)
    return () => window.clearInterval(timer)
  }, [item.id, item.status, loadCase])

  async function execute(action: string) {
    setBusy(true); setError('')
    try {
      const payload = action === 'record_simulated_publish'
        ? { note: '演示流程，未登录或写入真实平台' }
        : action === 'record_synthetic_feedback'
          ? { touchpoint: item.target_platform, inquiry_status: 'valid', reason_code: 'synthetic_demo_signal' }
          : {}
      const next = await runtimeApi.commandMarketingCase(item, action, payload)
      setItem(next); await loadRecent()
    } catch (reason) {
      if (reason instanceof RuntimeApiError && reason.status === 401) onLogout()
      if (reason instanceof RuntimeApiError && reason.status === 412) await loadCase(item.id)
      setError(reason instanceof Error ? reason.message : '操作失败')
    } finally { setBusy(false) }
  }

  const grouped = useMemo(() => {
    const result: Record<string, MarketingCaseResource[]> = {}
    item.resources.forEach(ref => { (result[ref.resource_type] ||= []).push(ref) })
    return result
  }, [item.resources])
  const activeStage = item.stages.find(stage => stage.step_key === item.current_stage)
  const hasUnknownRun = Object.values(evidence).some(value => value.run.status === 'unknown')

  return <main className="workflow-shell">
    <header className="workflow-header">
      <div><span className="workflow-eyebrow">1CAT · MARKETING WORKFLOW</span><h1>{item.title}</h1></div>
      <div className="workflow-header-actions">
        <button onClick={onNew}>新建案例</button>
        <a href="/?view=runtime"><Activity size={14} />PMA Runtime</a>
        <a href="/?view=workspace"><ArrowLeft size={14} />八类页面</a>
        <button onClick={() => void loadCase(item.id)}><RefreshCw size={14} />刷新</button>
        <button onClick={() => { runtimeSession.clear(); onLogout() }}><LogOut size={14} />退出</button>
      </div>
    </header>

    <section className="workflow-case-bar">
      <div><span>案例 ID</span><code>{item.id}</code></div>
      <div><span>模式</span><strong>{item.execution_mode === 'real' ? '真实 DeepSeek' : '确定性合成'}</strong></div>
      <div><span>平台</span><strong>{PLATFORM_LABELS[item.target_platform] || item.target_platform}</strong></div>
      <div><span>状态</span><strong className={`case-status ${item.status}`}>{item.status}</strong></div>
      <label><History size={14} /><span>历史案例</span><select value={item.id} onChange={event => void loadCase(event.target.value)}>
        {recent.map(entry => <option key={entry.id} value={entry.id}>{entry.title} · {entry.status}</option>)}
      </select></label>
    </section>

    <div className="workflow-layout">
      <aside className="workflow-card workflow-stages"><div className="workflow-section-title"><span>01</span><h2>九阶段状态机</h2></div><StageStepper item={item} /></aside>
      <section className="workflow-center">
        <article className="workflow-card workflow-action-panel">
          <div className="workflow-section-title"><span>02</span><h2>当前阶段 · {STAGE_LABELS[item.current_stage]}</h2></div>
          <p>{item.objective}</p>
          <div className="workflow-current-state">
            {POLLABLE.has(item.status) ? <Clock3 size={18} /> : item.status === 'blocked' ? <AlertTriangle size={18} /> : <UserCheck size={18} />}
            <div><strong>{activeStage?.status || item.status}</strong><small>版本 {item.version} · 页面仅呈现服务端允许动作</small></div>
          </div>
          {activeStage?.failure && Object.keys(activeStage.failure).length > 0 && <pre className="workflow-failure">{JSON.stringify(activeStage.failure, null, 2)}</pre>}
          {hasUnknownRun && <div className="workflow-reconciliation">
            <AlertTriangle size={18} /><div><strong>需要人工对账</strong><p>系统无法确认外部执行结果，已禁止自动重试。请核对 Run、Attempt、Hermes Run ID 与日志；确认副作用后再决定是否取消案例。</p></div>
          </div>}
          {error && <p className="workflow-error"><AlertTriangle size={15} />{error}</p>}
          <div className="workflow-actions">
            {item.next_actions.map(action => <button key={action.action} className={action.action === 'cancel_case' ? 'workflow-danger' : 'workflow-primary'} disabled={busy} onClick={() => void execute(action.action)}>
              {action.action.startsWith('start_') ? <Play size={15} /> : <CheckCircle2 size={15} />}{busy ? '处理中…' : action.label}
            </button>)}
            {!item.next_actions.length && item.status === 'running' && <span><Bot size={16} />Agent 正在执行，2 秒后自动刷新</span>}
          </div>
        </article>

        <FinalDeliverablePanel item={item} />

        {Object.entries(evidence).map(([runId, value]) => <article className="workflow-card workflow-run" key={runId}>
          <header><div><span>{value.run.profile_id.toUpperCase()} RUN</span><strong>{value.run.status}</strong></div>
            {value.run.trace_id && <a href={`${JAEGER_URL}/trace/${value.run.trace_id}`} target="_blank" rel="noreferrer"><ExternalLink size={14} />Trace</a>}
          </header>
          <dl><div><dt>Run</dt><dd>{runId}</dd></div><div><dt>岗位 / 阶段</dt><dd>{value.run.role_id} · {STAGE_LABELS[value.run.stage_key || ''] || value.run.stage_key || '独立 Run'}</dd></div><div><dt>模式</dt><dd>{value.run.execution_mode || item.execution_mode}</dd></div><div><dt>Correlation</dt><dd>{value.run.correlation_id}</dd></div></dl>
          <div className="workflow-timeline">{value.timeline.map(event => <span key={event.id}><i />{event.to_status}<small>{formatTime(event.created_at)}</small></span>)}</div>
          {Object.keys(value.run.failure || {}).length > 0 && <pre className="workflow-failure">{JSON.stringify(value.run.failure, null, 2)}</pre>}
          <details className="workflow-attempt-list" open>
            <summary>Attempt 历史 <span>{value.attempts.length}</span></summary>
            <div>{value.attempts.map(attempt => <AttemptEvidence key={attempt.id} attempt={attempt} current={attempt.id === value.run.current_attempt_id} />)}</div>
          </details>
        </article>)}

        {item.status === 'completed' && <article className="workflow-complete">
          <CheckCircle2 size={28} /><div><h2>完整方案已确认，技术链路已完成</h2><p>{item.execution_mode === 'real' ? '本次真实 DeepSeek Agent 技术链路与最终方案已由人确认' : '本次合成业务案例及最终方案已完成'}。发布回执为 <strong>simulated</strong>，未访问真实内容平台，也不代表真实营销效果。</p></div>
        </article>}
      </section>

      <aside className="workflow-card workflow-evidence">
        <div className="workflow-section-title"><span>03</span><h2>服务端事实</h2></div>
        {(['commitment', 'handoff', 'approval', 'knowledge', 'deliverable', 'manual_task', 'lead', 'sales_feedback'] as const).map(kind => grouped[kind]?.length ? <details key={kind} open={['commitment', 'knowledge', 'deliverable', 'manual_task'].includes(kind)}>
          <summary>{RESOURCE_LABELS[kind] || kind}<span>{grouped[kind].length}</span></summary>
          <div>{grouped[kind].map(ref => <ResourceCard key={ref.id} ref={ref} />)}</div>
        </details> : null)}
      </aside>
    </div>

    <footer className="workflow-footer"><ShieldCheck size={16} /><strong>边界声明</strong><span>发布 simulated</span><span>external_effect=false</span><span>PII=false</span><span>不声明营销效果</span></footer>
  </main>
}

export default function MarketingWorkflow() {
  const [authenticated, setAuthenticated] = useState(runtimeSession.hasToken())
  const [selected, setSelected] = useState<MarketingCase | null>(null)
  const [model, setModel] = useState<RuntimeModel | null>(null)
  const [recent, setRecent] = useState<MarketingCase[]>([])
  const [error, setError] = useState('')

  const bootstrap = useCallback(async () => {
    try {
      const [nextModel, cases] = await Promise.all([runtimeApi.getRuntimeModel(), runtimeApi.listMarketingCases()])
      setModel(nextModel); setRecent(cases)
      const remembered = runtimeSession.activeCaseId()
      const target = cases.find(item => item.id === remembered) || cases[0]
      if (target) setSelected(await runtimeApi.getMarketingCase(target.id))
    } catch (reason) {
      if (reason instanceof RuntimeApiError && reason.status === 401) setAuthenticated(false)
      else setError(reason instanceof Error ? reason.message : '无法加载工作台')
    }
  }, [])
  useEffect(() => { if (authenticated) void bootstrap() }, [authenticated, bootstrap])
  if (!authenticated) return <WorkflowLogin onLogin={() => setAuthenticated(true)} />
  if (selected) return <CaseWorkspace initial={selected} onNew={() => { runtimeSession.forgetCase(); setSelected(null) }} onLogout={() => { setAuthenticated(false); setSelected(null) }} />
  return <main className="workflow-shell workflow-empty-shell">
    <header className="workflow-header"><div><span className="workflow-eyebrow">1CAT · MARKETING WORKFLOW</span><h1>完整流程工作台</h1></div><a href="/?view=workspace"><ArrowLeft size={14} />八类页面</a></header>
    <div className="workflow-empty-layout">
      <CreateCase model={model} onCreated={item => { runtimeSession.rememberCase(item.id); setSelected(item) }} />
      <section className="workflow-card workflow-history"><div className="workflow-section-title"><span>RECENT</span><h2>最近案例</h2></div>
        {error && <p className="workflow-error"><AlertTriangle size={15} />{error}</p>}
        {!recent.length ? <p>还没有服务端案例。创建第一个完整流程。</p> : recent.map(item => <button key={item.id} onClick={async () => setSelected(await runtimeApi.getMarketingCase(item.id))}>
          <FileCheck2 size={17} /><span><strong>{item.title}</strong><small>{STAGE_LABELS[item.current_stage]} · {item.status}</small></span><GitBranch size={15} />
        </button>)}
      </section>
    </div>
  </main>
}
