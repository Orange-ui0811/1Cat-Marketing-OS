import { useCallback, useEffect, useMemo, useState } from 'react'
import { Activity, AlertTriangle, ArrowUpRight, Database, RefreshCw, Server, Workflow } from 'lucide-react'
import {
  MarketingCase, RuntimeApiError, RuntimeModel, runtimeApi, runtimeSession,
} from './runtimeApi'
import type { ViewKey } from './types'

const STAGE_LABELS: Record<string, string> = {
  brief: '创建 Brief',
  mo_plan: 'MO 规划',
  pma: 'PMA Fact / Claim',
  product_review: '人工产品审核',
  bga: 'BGA Campaign / Content',
  content_review: '人工内容审核',
  simulated_publish: '模拟人工发布',
  feedback: '合成 Lead / 销售反馈',
  mo_retrospective: 'MO 复盘',
}

type SummaryFact = { label: string; value: string | number; detail: string }

function resourceCount(item: MarketingCase, kind: string) {
  return item.resources.filter(resource => resource.resource_type === kind).length
}

function knowledgeKinds(item: MarketingCase) {
  return [...new Set(item.resources
    .filter(resource => resource.resource_type === 'knowledge')
    .map(resource => String(resource.resource?.kind || 'knowledge')))]
}

function factsFor(
  view: ViewKey,
  item: MarketingCase,
  cases: MarketingCase[],
  model: RuntimeModel | null,
): SummaryFact[] {
  const activeStage = item.stages.find(stage => stage.step_key === item.current_stage)
  const runs = item.resources.filter(resource => resource.resource_type === 'run')
  const unknownRuns = runs.filter(resource => resource.resource?.status === 'unknown').length
  const waiting = cases.filter(entry => entry.status === 'awaiting_human').length
  const completed = cases.filter(entry => entry.status === 'completed').length
  const blocked = cases.filter(entry => entry.status === 'blocked').length
  const common: SummaryFact[] = [
    { label: '当前案例', value: item.title, detail: item.id },
    { label: '服务端阶段', value: STAGE_LABELS[item.current_stage] || item.current_stage, detail: `${item.status} · v${item.version}` },
  ]
  const byView: Record<ViewKey, SummaryFact[]> = {
    tasks: [
      ...common,
      { label: '当前 Run', value: activeStage?.active_run_id ? activeStage.active_run_id.slice(0, 12) : '等待人工动作', detail: activeStage?.status || item.status },
      { label: '下一动作', value: item.next_actions[0]?.label || '无待办', detail: `${item.next_actions.length} 个服务端允许动作` },
    ],
    collaboration: [
      ...common,
      { label: 'Commitment', value: resourceCount(item, 'commitment'), detail: '岗位责任承诺' },
      { label: 'Handoff', value: resourceCount(item, 'handoff'), detail: 'MO → PMA → BGA' },
    ],
    objects: [
      ...common,
      { label: 'Knowledge', value: resourceCount(item, 'knowledge'), detail: knowledgeKinds(item).join(' · ') || '暂无候选' },
      { label: '业务回执', value: resourceCount(item, 'lead') + resourceCount(item, 'sales_feedback'), detail: 'Lead + SalesFeedback' },
    ],
    reviews: [
      ...common,
      { label: 'Approval', value: resourceCount(item, 'approval'), detail: '均绑定对象版本' },
      { label: '人工门禁', value: item.status === 'awaiting_human' ? '待处理' : '无待处理', detail: item.next_actions[0]?.label || '等待 Agent 或已完成' },
    ],
    holds: [
      ...common,
      { label: '阻塞案例', value: blocked, detail: '最近 20 个案例' },
      { label: 'Unknown Run', value: unknownRuns, detail: unknownRuns ? '禁止自动重试，需人工对账' : '当前案例无未知副作用' },
    ],
    daily: [
      ...common,
      { label: '今日待办', value: waiting, detail: '等待人工门禁' },
      { label: '已完成案例', value: completed, detail: '最近 20 个案例' },
    ],
    agent_config: [
      ...common,
      { label: '模型', value: model ? `${model.provider} / ${model.model}` : '未读取', detail: model?.mode || '—' },
      { label: '真实执行', value: model?.execution_enabled ? '可用' : '未启用', detail: '真实模式仍需显式选择' },
    ],
    diagnostics: [
      ...common,
      { label: 'Runtime', value: '已连接', detail: item.correlation_id },
      { label: '运行事实', value: `${runs.length} Runs`, detail: `${resourceCount(item, 'knowledge')} Knowledge · ${resourceCount(item, 'approval')} Approvals` },
    ],
  }
  return byView[view]
}

export default function RuntimeCaseSummary({ view }: { view: ViewKey }) {
  const [cases, setCases] = useState<MarketingCase[]>([])
  const [item, setItem] = useState<MarketingCase | null>(null)
  const [model, setModel] = useState<RuntimeModel | null>(null)
  const [loading, setLoading] = useState(runtimeSession.hasToken())
  const [error, setError] = useState('')
  const connected = runtimeSession.hasToken()

  const load = useCallback(async () => {
    if (!runtimeSession.hasToken()) return
    setLoading(true)
    try {
      const [recent, nextModel] = await Promise.all([
        runtimeApi.listMarketingCases(),
        runtimeApi.getRuntimeModel(),
      ])
      setCases(recent); setModel(nextModel)
      const remembered = runtimeSession.activeCaseId()
      const target = recent.find(entry => entry.id === remembered) || recent[0]
      setItem(target ? await runtimeApi.getMarketingCase(target.id) : null)
      setError('')
    } catch (reason) {
      setError(reason instanceof RuntimeApiError && reason.status === 401
        ? 'Runtime 登录已失效'
        : reason instanceof Error ? reason.message : '无法读取服务端案例')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])
  useEffect(() => {
    if (item?.status !== 'running') return
    const timer = window.setInterval(() => void load(), 2000)
    return () => window.clearInterval(timer)
  }, [item?.status, load])

  const facts = useMemo(() => item ? factsFor(view, item, cases, model) : [], [view, item, cases, model])

  if (!connected) return <section className="runtime-case-summary disconnected" aria-label="服务端案例摘要">
    <div className="runtime-summary-lead"><Server size={17} /><div><strong>服务端案例尚未连接</strong><small>本页仍是本地演练视图；登录完整流程工作台后显示真实 Runtime 摘要。</small></div></div>
    <a href="/?view=workflow"><Workflow size={14} />连接完整流程 <ArrowUpRight size={13} /></a>
  </section>

  if (loading && !item) return <section className="runtime-case-summary loading" aria-label="服务端案例摘要">
    <div className="runtime-summary-lead"><Activity size={17} /><div><strong>正在读取服务端案例</strong><small>业务页面保持现有本地状态，不会被覆盖。</small></div></div>
  </section>

  if (error) return <section className="runtime-case-summary error" aria-label="服务端案例摘要">
    <div className="runtime-summary-lead"><AlertTriangle size={17} /><div><strong>服务端摘要暂不可用</strong><small>{error}；本地演练数据保持不变。</small></div></div>
    <button onClick={() => void load()}><RefreshCw size={13} />重试</button>
    <a href="/?view=workflow">打开完整流程</a>
  </section>

  if (!item) return <section className="runtime-case-summary" aria-label="服务端案例摘要">
    <div className="runtime-summary-lead"><Database size={17} /><div><strong>Runtime 已连接，暂无营销案例</strong><small>建立第一个案例后，八类页面会显示对应服务端事实。</small></div></div>
    <a href="/?view=workflow"><Workflow size={14} />新建案例 <ArrowUpRight size={13} /></a>
  </section>

  return <section className="runtime-case-summary connected" aria-label="服务端案例摘要">
    <div className="runtime-summary-title"><span><Database size={15} />SERVER FACTS</span><small>八类页面只读摘要</small></div>
    <div className="runtime-summary-facts">
      {facts.map(fact => <div key={fact.label}><span>{fact.label}</span><strong>{fact.value}</strong><small>{fact.detail}</small></div>)}
    </div>
    <div className="runtime-summary-actions">
      <button aria-label="刷新服务端案例摘要" onClick={() => void load()}><RefreshCw size={13} /></button>
      <a href="/?view=workflow">进入完整流程 <ArrowUpRight size={13} /></a>
    </div>
  </section>
}
