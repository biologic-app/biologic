import type { Router } from 'vue-router'
import { apiRequest, buildApiUrl } from '@/shared/api/client.api'
import { useAuth } from '@/modules/auth'

/**
 * Passive UI telemetry (ROADMAP A2.3): anonymous interaction events used to
 * spot which screens/actions "stick" and where errors happen. Only element
 * identifiers are collected — never form values or other user-entered
 * content. Off by default; enabled via `VITE_TELEMETRY_ENABLED=true`.
 */
interface TelemetryEvent {
  event: string
  element_id: string | null
  route: string
  role: string | null
  ts: string
  session_id: string
}

const SESSION_STORAGE_KEY = 'telemetry_session_id'
const ENDPOINT = '/telemetry/events'
const FLUSH_INTERVAL_MS = 5000
const MAX_BUFFER_SIZE = 20

const isTelemetryEnabled = (): boolean => import.meta.env.VITE_TELEMETRY_ENABLED === 'true'

let cachedSessionId: string | null = null

const generateId = (): string => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

const getSessionId = (): string => {
  if (cachedSessionId) return cachedSessionId
  if (typeof window === 'undefined') return 'server'

  try {
    const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY)
    if (existing) {
      cachedSessionId = existing
      return existing
    }
    const generated = generateId()
    window.sessionStorage.setItem(SESSION_STORAGE_KEY, generated)
    cachedSessionId = generated
    return generated
  } catch {
    // Private mode or storage disabled — fall back to an in-memory id for
    // the lifetime of the page.
    cachedSessionId = generateId()
    return cachedSessionId
  }
}

let buffer: TelemetryEvent[] = []
let flushTimer: ReturnType<typeof setInterval> | null = null
let initialized = false

const flush = (useBeacon = false): void => {
  if (buffer.length === 0) return
  const events = buffer
  buffer = []

  if (useBeacon && typeof navigator !== 'undefined' && 'sendBeacon' in navigator) {
    const blob = new Blob([JSON.stringify({ events })], { type: 'application/json' })
    navigator.sendBeacon(buildApiUrl(ENDPOINT), blob)
    return
  }

  // Fire-and-forget: telemetry must never surface errors to the user.
  apiRequest(ENDPOINT, { method: 'POST', body: { events } }).catch(() => {})
}

const track = (event: string, elementId: string | null = null): void => {
  if (!isTelemetryEnabled() || typeof window === 'undefined') return

  const auth = useAuth()
  buffer.push({
    event,
    element_id: elementId,
    route: window.location.pathname,
    role: auth.user?.role ?? null,
    ts: new Date().toISOString(),
    session_id: getSessionId()
  })

  if (buffer.length >= MAX_BUFFER_SIZE) {
    flush()
  }
}

const handleDelegatedClick = (nativeEvent: MouseEvent): void => {
  const target = nativeEvent.target
  if (!(target instanceof Element)) return
  const el = target.closest<HTMLElement>('[data-telemetry]')
  if (!el) return
  track('click', el.getAttribute('data-telemetry'))
}

const handleWindowError = (event: ErrorEvent): void => {
  track('error', event.message ? event.message.slice(0, 200) : 'window_error')
}

const handleUnhandledRejection = (): void => {
  track('error', 'unhandled_rejection')
}

const handleVisibilityChange = (): void => {
  if (document.visibilityState === 'hidden') {
    flush(true)
  }
}

/**
 * Wire up passive telemetry collection: a delegated click listener for
 * `[data-telemetry]` elements, router navigation tracking, global error
 * capture, and a buffered fire-and-forget flush loop. No-op when the
 * `VITE_TELEMETRY_ENABLED` flag is off. Call once during app bootstrap.
 */
export function initTelemetry(router: Router): void {
  if (initialized || !isTelemetryEnabled() || typeof window === 'undefined') return
  initialized = true

  document.addEventListener('click', handleDelegatedClick, true)
  window.addEventListener('error', handleWindowError)
  window.addEventListener('unhandledrejection', handleUnhandledRejection)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('pagehide', () => flush(true))

  router.afterEach((to) => {
    track('navigation', to.fullPath)
  })

  flushTimer = setInterval(() => flush(false), FLUSH_INTERVAL_MS)
}

export function stopTelemetry(): void {
  if (flushTimer) {
    clearInterval(flushTimer)
    flushTimer = null
  }
  initialized = false
}

export function useTelemetry() {
  return { track }
}
