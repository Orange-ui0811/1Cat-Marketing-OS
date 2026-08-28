import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, CheckCircle2, Clock3, ExternalLink, LogOut, Play, RefreshCw, Settings, ShieldCheck, Square,
} from 'lucide-react'
import {
  AgentRun, Commitment, RunAttempt, RunTransition, RuntimeApiError, RuntimeModel, runtimeApi, runtimeSession,
} from './runtimeApi'

const TERMINAL = new Set(['evidence_accepted', 'failed', 'cancelled', 'unknown'])
const RUN_STAGES = ['queued', 'accepted', 'running', 'evidence_accepted']
const JAEGER_URL = import.meta.env.VITE_JAEGER_URL || 'http://127.0.0.1:16686'
const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL || 'http://127.0.0.1:3000'
const PROMETHEUS_URL = import.meta.env.VITE_PROMETHEUS_URL || 'http://127.0.0.1:9090'

function formatTime(value?: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value))
}

function Login({ onLogin }: { onLogin: () => void }) {
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
  return <main className="runtime-shell runtime-login">
    <section className="runtime-login-copy">
      <span className="runtime-eyebrow">DEMO1 · API MODE</span>
      <h1>PMA Agent Runtime<br />黄金链路</h1>
      <p>这个页面读取服务端事实，用于演示 Commitment、Run、Attempt 和人工决策的真实边界。</p>
      <div className="runtime-guard"><ShieldCheck size={18} /> 候选产出不等于业务履约，最终确认仍由人类完成。</div>
    </section>
    <form className="runtime-card runtime-login-form" onSubmit={submit}>
      <h2>进入 Runtime 研修界面</h2>
      <label>用户名<input value={username} onChange={event => setUsername(event.target.value)} /></label>
      <label>密码<input type="password" value={password} onChange={event => setPassword(event.target.value)} /></label>
      {error && <p className="runtime-error"><AlertTriangle size={16} />{error}</p>}
      <button className="runtime-primary" disabled={busy || !password}>{busy ? '正在验证…' : '安全登录'}</button>
      <a className="runtime-secondary runtime-config-link" href="/?view=workspace"><Settings size={16} />打开 Agent 配置</a>
    </form>
  </main>
}

function RuntimeWorkspace({ onLogout }: { onLogout: () => void }) {
  const [title, setTitle] = useState('PMA 产品价值表达候选')
  const [objective, setObjective] = useState('基于合成产品信息，生成一份可送审的产品价值表达，不包含 PII，不执行发布。')
  const [instruction, setInstruction] = useState('输出三条核心价值主张、一段候选文案与需要人工确认的风险项。')
  const [commitment, setCommitment] = useState<Commitment | null>(null)
  const [run, setRun] = useState<AgentRun | null>(null)
  const [attempts, setAttempts] = useState<RunAttempt[]>([])
  const [timeline, setTimeline] = useState<RunTransition[]>([])
  const [recentRuns, setRecentRuns] = useState<AgentRun[]>([])
  const [busy, setBusy] = useState(false)
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const [runtimeModel, setRuntimeModel] = useState<RuntimeModel | null>(null)
  const [error, setError] = useState('')

  const loadRecentRuns = useCallback(async () => {
    try {
      const items = await runtimeApi.listRuns()
      setRecentRuns([...items].sort((left, right) => right.created_at.localeCompare(left.created_at)).slice(0, 8))
    } catch (reason) {
      if (reason instanceof RuntimeApiError && reason.status === 401) onLogout()
    }
  }, [onLogout])

  const loadRun = useCallback(async (runId: string) => {
    try {
      const [latest, nextAttempts, nextTimeline, commitments] = await Promise.all([
        runtimeApi.getRun(runId), runtimeApi.getAttempts(runId), runtimeApi.getTimeline(runId), runtimeApi.listCommitments(),
      ])
      setRun(latest); setAttempts(nextAttempts); setTimeline(nextTimeline)
      const latestCommitment = commitments.find(item => item.id === latest.commitment_id) || null
      setCommitment(latestCommitment)
      if (latestCommitment) {
        setTitle(latestCommitment.title)
        setObjective(latestCommitment.objective)
      }
      setError('')
    } catch (reason) {
      if (reason instanceof RuntimeApiError && reason.status === 401) onLogout()
      if (reason instanceof RuntimeApiError && reason.status === 404) runtimeSession.forgetRun()
      setError(reason instanceof Error ? reason.message : '刷新失败')
    }
  }, [onLogout])

  const refresh = useCallback(async () => {
    if (run) await loadRun(run.id)
  }, [run, loadRun])

  useEffect(() => {
    Promise.all([runtimeApi.ready(), runtimeApi.getRuntimeModel(), runtimeApi.listRuns()])
      .then(([, model, items]) => {
        setRuntimeModel(model); setHealthy(true)
        setRecentRuns([...items].sort((left, right) => right.created_at.localeCompare(left.created_at)).slice(0, 8))
      })
      .catch(reason => {
        if (reason instanceof RuntimeApiError && reason.status === 401) onLogout()
        setHealthy(false)
      })
  }, [onLogout])
  useEffect(() => {
    const activeRunId = runtimeSession.activeRunId()
    if (activeRunId) void loadRun(activeRunId)
  }, [loadRun])
  useEffect(() => {
    if (!run || TERMINAL.has(run.status)) return
    const timer = window.setInterval(refresh, 2000)
    return () => window.clearInterval(timer)
  }, [run, refresh])

  async function start() {
    setBusy(true); setError('')
    try {
      const proposed = await runtimeApi.createCommitment({ title, objective })
      const accepted = await runtimeApi.transitionCommitment(proposed.id, 'accepted', '人类已确认目标与边界')
      const created = await runtimeApi.createRun(accepted.id, instruction)
      runtimeSession.rememberRun(created.id)
      setCommitment(accepted); setRun(created); setAttempts([])
      setTimeline(await runtimeApi.getTimeline(created.id))
      void loadRecentRuns()
    } catch (reason) {
      if (reason instanceof RuntimeApiError && reason.status === 401) onLogout()
      setError(reason instanceof Error ? reason.message : '创建 Run 失败')
    } finally { setBusy(false) }
  }

  function selectRun(runId: string) {
    runtimeSession.rememberRun(runId)
    void loadRun(runId)
  }

  function resetBuilder() {
    runtimeSession.forgetRun()
    setRun(null); setCommitment(null); setAttempts([]); setTimeline([]); setError('')
  }

  async function cancel() {
    if (!run) return
    try { setRun(await runtimeApi.cancelRun(run.id)); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : '取消失败') }
  }

  async function confirmEvidence() {
    if (!commitment) return
    setBusy(true)
    try {
      setCommitment(await runtimeApi.transitionCommitment(commitment.id, 'fulfilled', '人类已审阅并接受候选证据'))
    } catch (reason) { setError(reason instanceof Error ? reason.message : '人工确认失败') }
    finally { setBusy(false) }
  }

  const stageIndex = useMemo(() => run ? RUN_STAGES.indexOf(run.status) : -1, [run])
  const recoveryInsight = useMemo(() => {
    if (!run || !attempts.length) return null
    if (run.status === 'unknown') return {
      tone: 'unsafe',
      title: '不确定副作用已隔离',
      detail: '外部派发边界之后 Lease 过期，Runtime 禁止自动重试并等待人工对账。',
    }
    if (attempts.some(item => item.status === 'lost') && attempts.some(item => item.status === 'succeeded')) return {
      tone: 'safe',
      title: '安全恢复已完成',
      detail: '旧 Attempt 已永久标记 lost，新 Worker 使用新 Lease 创建后续 Attempt 并完成写回。',
    }
    if (attempts.some(item => item.status === 'lost')) return {
      tone: 'warning',
      title: '正在等待恢复 Worker',
      detail: '旧 Attempt 已失去 Lease，Run 已重新入队，旧 Worker 的写回会被 fencing 拒绝。',
    }
    return {
      tone: 'active',
      title: 'Lease 正在生效',
      detail: '只有当前 Attempt、Worker 和有效 Lease Token 同时匹配时才能续约或写回。',
    }
  }, [attempts, run])
  return <main className="runtime-shell runtime-workspace">
    <header className="runtime-header">
      <div><span className="runtime-eyebrow">1CAT · AGENT RUNTIME LAB</span><h1>PMA 黄金链路</h1></div>
      <div className="runtime-header-actions">
        <a className="runtime-secondary" href="/?view=workspace"><Settings size={15} />Agent 配置</a>
        <span className={healthy ? 'runtime-health ok' : 'runtime-health'}><Activity size={15} />{healthy ? 'Runtime 就绪' : '正在检查'}</span>
        {runtimeModel && <span className="runtime-health ok">
          {runtimeModel.provider} / {runtimeModel.model} · {runtimeModel.execution_enabled ? '真实执行' : '合成执行'}
        </span>}
        <button className="runtime-ghost" onClick={() => { runtimeSession.clear(); onLogout() }}><LogOut size={16} />退出</button>
      </div>
    </header>

    <section className="runtime-grid">
      <div className="runtime-card runtime-builder">
        <div className="runtime-section-title"><span>01</span><div><h2>定义 Commitment</h2><p>由人类创建任务边界，再交给 PMA Agent。</p></div></div>
        {recentRuns.length > 0 && <div className="runtime-recent-runs">
          <div><strong>最近服务端 Run</strong><small>可直接检查真实恢复与 unknown 时间线</small></div>
          <select aria-label="切换最近 Run" value={run?.id || ''} onChange={event => selectRun(event.target.value)}>
            <option value="" disabled>选择一条 Run</option>
            {recentRuns.map(item => <option key={item.id} value={item.id}>{item.status} · {item.id}</option>)}
          </select>
          {run && <button className="runtime-ghost" onClick={resetBuilder}>新建 Run</button>}
        </div>}
        <label>任务名称<input value={title} onChange={event => setTitle(event.target.value)} disabled={Boolean(run)} /></label>
        <label>目标与验收边界<textarea value={objective} onChange={event => setObjective(event.target.value)} disabled={Boolean(run)} /></label>
        <label>Agent 输入<textarea value={instruction} onChange={event => setInstruction(event.target.value)} disabled={Boolean(run)} /></label>
        {!run && <button className="runtime-primary" onClick={start} disabled={busy || !healthy}><Play size={17} />{busy ? '正在创建…' : '创建并启动 PMA Run'}</button>}
        {run && <div className="runtime-button-row">
          <button className="runtime-secondary" onClick={refresh}><RefreshCw size={16} />立即刷新</button>
          {!TERMINAL.has(run.status) && <button className="runtime-danger" onClick={cancel}><Square size={14} />请求取消</button>}
        </div>}
        {error && <p className="runtime-error"><AlertTriangle size={16} />{error}<button onClick={refresh}>重试</button></p>}
      </div>

      <div className="runtime-card runtime-run-panel">
        <div className="runtime-section-title"><span>02</span><div><h2>Run 状态机</h2><p>每 2 秒从服务端读取，进入终态后停止轮询。</p></div></div>
        {run && <span className={`runtime-state-chip runtime-state-${run.status}`}>{run.status}</span>}
        <div className="runtime-stage-list">
          {RUN_STAGES.map((stage, index) => <div key={stage} className={`runtime-stage ${index <= stageIndex ? 'active' : ''}`}>
            <span>{index < stageIndex || run?.status === 'evidence_accepted' ? <CheckCircle2 size={18} /> : <Clock3 size={18} />}</span>
            <div><strong>{stage}</strong><small>{index === 0 ? '入队' : index === 1 ? 'Worker 取得 Lease' : index === 2 ? 'Agent 执行' : '候选证据已接收'}</small></div>
          </div>)}
        </div>
        {run && <dl className="runtime-facts">
          <div><dt>Runtime Run ID</dt><dd>{run.id}</dd></div>
          <div><dt>Correlation ID</dt><dd>{run.correlation_id}</dd></div>
          <div><dt>Trace ID</dt><dd>{run.trace_id || '本 Run 创建于观测开启前'}</dd></div>
          <div><dt>当前 Attempt</dt><dd>{run.current_attempt?.id || '等待 Worker'}</dd></div>
          <div><dt>Hermes Run ID</dt><dd>{run.current_attempt?.hermes_run_id || '尚未启动'}</dd></div>
        </dl>}
        {!run && <div className="runtime-empty">启动一次 PMA Run 后，这里会显示可验证的运行状态。</div>}
      </div>
    </section>

    {run && <section className="runtime-grid runtime-detail-grid">
      <div className="runtime-card">
        <div className="runtime-section-title"><span>03</span><div><h2>Attempt 与恢复</h2><p>历史只追加，旧 Attempt 不会覆盖新结果。</p></div></div>
        {recoveryInsight && <div className={`runtime-recovery-insight ${recoveryInsight.tone}`}>
          {recoveryInsight.tone === 'unsafe' ? <AlertTriangle size={18} /> : <ShieldCheck size={18} />}
          <div><strong>{recoveryInsight.title}</strong><p>{recoveryInsight.detail}</p></div>
        </div>}
        <div className="runtime-attempts">{attempts.length ? attempts.map(item => <article className={`runtime-attempt runtime-attempt-${item.status}`} key={item.id}>
          <header><strong>Attempt #{item.attempt_no}</strong><span>{item.status}</span></header>
          <code>{item.id}</code><span>Worker · {item.worker_id}</span>
          <small>heartbeat {formatTime(item.heartbeat_at)} · lease {formatTime(item.lease_until)}</small>
          <small>started {formatTime(item.started_at)} · completed {formatTime(item.completed_at)}</small>
          <small>Hermes · {item.hermes_run_id || '未派发 / 未确认'}</small>
          {item.failure_class && <em>{item.failure_class} / {item.retryability}</em>}
        </article>) : <div className="runtime-empty">尚无 Attempt</div>}</div>
      </div>
      <div className="runtime-card">
        <div className="runtime-section-title"><span>04</span><div><h2>执行时间线</h2><p>状态、原因、执行者和 correlation ID 共同留痕。</p></div></div>
        <div className="runtime-timeline">{timeline.map(item => <article key={item.id}>
          <span className="runtime-dot" /><div><strong>{item.from_status} → {item.to_status}</strong><p>{item.reason}</p><small>{formatTime(item.created_at)} · {item.actor}</small><code>{item.attempt_id || 'run-level'} · {item.correlation_id}</code></div>
        </article>)}</div>
      </div>
    </section>}

    {run && <section className="runtime-card runtime-observability">
      <div className="runtime-section-title"><span>05</span><div><h2>可观测性联查</h2><p>用同一 Run、Correlation 和 Trace 标识核对轨迹、指标与结构化日志。</p></div></div>
      <div className="runtime-observability-body">
        <dl className="runtime-observability-ids">
          <div><dt>Run</dt><dd>{run.id}</dd></div>
          <div><dt>Correlation</dt><dd>{run.correlation_id}</dd></div>
          <div><dt>Trace</dt><dd>{run.trace_id || '未采集'}</dd></div>
        </dl>
        <div className="runtime-observability-links">
          {run.trace_id ? <a href={`${JAEGER_URL}/trace/${run.trace_id}`} target="_blank" rel="noreferrer"><ExternalLink size={16} />在 Jaeger 打开 Trace</a>
            : <span className="runtime-observability-disabled">本 Run 没有 Trace ID，请新建一条 Run</span>}
          <a href={`${GRAFANA_URL}/d/onecat-runtime-overview/1cat-agent-runtime-overview?orgId=1&from=now-1h&to=now`} target="_blank" rel="noreferrer"><ExternalLink size={16} />打开 Grafana Runtime 看板</a>
          <a href={`${PROMETHEUS_URL}/graph?g0.expr=${encodeURIComponent('onecat_run_terminal_total')}&g0.tab=1`} target="_blank" rel="noreferrer"><ExternalLink size={16} />查询 Prometheus 指标</a>
        </div>
      </div>
      <p className="runtime-observability-hint">容器日志可按上面的 Run ID 或 Correlation ID 过滤；关键 Worker 事件同时包含 Attempt、Hermes Run 与 Trace 字段。</p>
    </section>}

    {run && TERMINAL.has(run.status) && <section className="runtime-card runtime-evidence">
      <div><span className="runtime-eyebrow">HUMAN DECISION</span><h2>候选证据与人工确认</h2><p>Run 终态是 <b>{run.status}</b>；它只证明运行时执行结束，不自动声称业务 fulfilled。</p></div>
      <pre>{JSON.stringify(Object.keys(run.output || {}).length ? run.output : run.failure, null, 2)}</pre>
      {run.status === 'evidence_accepted' && commitment?.status === 'submitted' && <button className="runtime-primary" onClick={confirmEvidence} disabled={busy}><ShieldCheck size={17} />人工审阅并确认 fulfilled</button>}
      {commitment?.status === 'fulfilled' && <div className="runtime-confirmed"><CheckCircle2 size={19} />已由人类确认；Commitment 现为 fulfilled。</div>}
    </section>}
  </main>
}

export default function RuntimeLab() {
  const [loggedIn, setLoggedIn] = useState(runtimeSession.hasToken())
  return loggedIn ? <RuntimeWorkspace onLogout={() => setLoggedIn(false)} /> : <Login onLogin={() => setLoggedIn(true)} />
}
