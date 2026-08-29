import {
  createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode,
} from 'react'
import {
  type AgentProfile, type AgentRun, type MarketingCase, type RunAttempt, type RunTransition,
  type RuntimeModel, RuntimeApiError, runtimeApi, runtimeSession,
} from './runtimeApi'

export type RunEvidence = { run: AgentRun; attempts: RunAttempt[]; timeline: RunTransition[] }

type NewCaseInput = Parameters<typeof runtimeApi.createMarketingCase>[0]

type RuntimeWorkspaceValue = {
  authenticated: boolean
  loading: boolean
  busy: boolean
  error: string
  cases: MarketingCase[]
  current: MarketingCase | null
  model: RuntimeModel | null
  profiles: AgentProfile[]
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
  selectCase: (caseId: string) => Promise<void>
  createCase: (input: NewCaseInput) => Promise<MarketingCase>
  command: (action: string, payload?: Record<string, unknown>) => Promise<MarketingCase>
  sendMessage: (input: { channel: 'MO' | 'PMA' | 'BGA'; body: string; intent?: 'message' | 'change_request' | 'decision_note' }) => Promise<MarketingCase>
  loadRunEvidence: (runId: string) => Promise<RunEvidence>
  updateProfile: (item: AgentProfile, config: Record<string, unknown>, summary: string) => Promise<void>
  commandProfile: (item: AgentProfile, action: 'validate' | 'publish' | 'rollback', version?: number) => Promise<void>
  clearError: () => void
}

const RuntimeWorkspaceContext = createContext<RuntimeWorkspaceValue | null>(null)

function setCaseInUrl(caseId?: string) {
  const url = new URL(window.location.href)
  if (caseId) url.searchParams.set('case', caseId)
  else url.searchParams.delete('case')
  window.history.replaceState({}, '', url)
}

export function RuntimeWorkspaceProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(runtimeSession.hasToken())
  const [loading, setLoading] = useState(runtimeSession.hasToken())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [cases, setCases] = useState<MarketingCase[]>([])
  const [current, setCurrent] = useState<MarketingCase | null>(null)
  const [model, setModel] = useState<RuntimeModel | null>(null)
  const [profiles, setProfiles] = useState<AgentProfile[]>([])

  const handleError = useCallback((reason: unknown, fallback: string) => {
    if (reason instanceof RuntimeApiError && reason.status === 401) {
      runtimeSession.clear(); setAuthenticated(false); setCurrent(null)
    }
    setError(reason instanceof Error ? reason.message : fallback)
  }, [])

  const selectCase = useCallback(async (caseId: string) => {
    setLoading(true)
    try {
      const item = await runtimeApi.getMarketingCase(caseId)
      setCurrent(item); runtimeSession.rememberCase(item.id); setCaseInUrl(item.id); setError('')
    } catch (reason) {
      handleError(reason, '无法读取案例')
    } finally {
      setLoading(false)
    }
  }, [handleError])

  const refresh = useCallback(async () => {
    if (!runtimeSession.hasToken()) return
    setLoading(true)
    try {
      const [recent, nextModel, nextProfiles] = await Promise.all([
        runtimeApi.listMarketingCases(), runtimeApi.getRuntimeModel(), runtimeApi.listAgentConfigs(),
      ])
      setCases(recent); setModel(nextModel); setProfiles(nextProfiles)
      const urlCase = new URLSearchParams(window.location.search).get('case')
      const requested = urlCase || runtimeSession.activeCaseId()
      const target = recent.find(item => item.id === requested) || recent[0]
      if (target) {
        const detail = await runtimeApi.getMarketingCase(target.id)
        setCurrent(detail); runtimeSession.rememberCase(detail.id); setCaseInUrl(detail.id)
      } else {
        setCurrent(null); setCaseInUrl()
      }
      setError('')
    } catch (reason) {
      handleError(reason, '无法加载服务端工作区')
    } finally {
      setLoading(false)
    }
  }, [handleError])

  useEffect(() => { if (authenticated) void refresh() }, [authenticated, refresh])
  useEffect(() => {
    if (!current || current.status !== 'running') return
    const timer = window.setInterval(async () => {
      try {
        const next = await runtimeApi.getMarketingCase(current.id)
        setCurrent(next)
        if (next.status !== 'running') setCases(await runtimeApi.listMarketingCases())
      } catch (reason) { handleError(reason, '自动刷新失败') }
    }, 2000)
    return () => window.clearInterval(timer)
  }, [current?.id, current?.status, handleError])

  async function login(username: string, password: string) {
    setBusy(true); setError('')
    try { await runtimeApi.login(username, password); setAuthenticated(true) }
    catch (reason) { handleError(reason, '登录失败'); throw reason }
    finally { setBusy(false) }
  }

  function logout() {
    runtimeSession.clear(); setAuthenticated(false); setCases([]); setCurrent(null); setCaseInUrl()
  }

  async function createCase(input: NewCaseInput) {
    setBusy(true); setError('')
    try {
      const item = await runtimeApi.createMarketingCase(input)
      setCurrent(item); runtimeSession.rememberCase(item.id); setCaseInUrl(item.id)
      setCases(await runtimeApi.listMarketingCases())
      return item
    } catch (reason) {
      handleError(reason, '创建案例失败'); throw reason
    } finally { setBusy(false) }
  }

  async function command(action: string, payload: Record<string, unknown> = {}) {
    if (!current) throw new Error('请先选择案例')
    setBusy(true); setError('')
    try {
      const next = await runtimeApi.commandMarketingCase(current, action, payload)
      setCurrent(next); setCases(await runtimeApi.listMarketingCases())
      return next
    } catch (reason) {
      if (reason instanceof RuntimeApiError && reason.status === 412) await selectCase(current.id)
      handleError(reason, '操作失败'); throw reason
    } finally { setBusy(false) }
  }

  async function sendMessage(input: { channel: 'MO' | 'PMA' | 'BGA'; body: string; intent?: 'message' | 'change_request' | 'decision_note' }) {
    if (!current) throw new Error('请先选择案例')
    setBusy(true); setError('')
    try {
      const next = await runtimeApi.createMarketingCaseMessage(current, input)
      setCurrent(next); setCases(await runtimeApi.listMarketingCases())
      return next
    } catch (reason) {
      handleError(reason, '发送失败'); throw reason
    } finally { setBusy(false) }
  }

  async function loadRunEvidence(runId: string) {
    const [run, attempts, timeline] = await Promise.all([
      runtimeApi.getRun(runId), runtimeApi.getAttempts(runId), runtimeApi.getTimeline(runId),
    ])
    return { run, attempts, timeline }
  }

  async function updateProfile(item: AgentProfile, config: Record<string, unknown>, summary: string) {
    setBusy(true); setError('')
    try {
      const next = await runtimeApi.updateAgentConfig(item, config, summary)
      setProfiles(values => values.map(value => value.agent_key === next.agent_key ? next : value))
    } catch (reason) { handleError(reason, '保存配置失败'); throw reason }
    finally { setBusy(false) }
  }

  async function commandProfile(item: AgentProfile, action: 'validate' | 'publish' | 'rollback', version?: number) {
    setBusy(true); setError('')
    try {
      const next = await runtimeApi.commandAgentConfig(item, action, version)
      setProfiles(values => values.map(value => value.agent_key === next.agent_key ? next : value))
    } catch (reason) { handleError(reason, '配置操作失败'); throw reason }
    finally { setBusy(false) }
  }

  const value = useMemo<RuntimeWorkspaceValue>(() => ({
    authenticated, loading, busy, error, cases, current, model, profiles,
    login, logout, refresh, selectCase, createCase, command, sendMessage, loadRunEvidence,
    updateProfile, commandProfile, clearError: () => setError(''),
  }), [authenticated, loading, busy, error, cases, current, model, profiles, selectCase, refresh])

  return <RuntimeWorkspaceContext.Provider value={value}>{children}</RuntimeWorkspaceContext.Provider>
}

export function useRuntimeWorkspace() {
  const value = useContext(RuntimeWorkspaceContext)
  if (!value) throw new Error('useRuntimeWorkspace must be used inside RuntimeWorkspaceProvider')
  return value
}
