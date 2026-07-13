import type {
  ApiCommandResponse,
  ApiCreateResponse,
  ApiDeleteResponse,
  ApiReadResponse,
  ApiUpdateResponse,
  ApiViewResponse
} from '@/shared/types/api'
import { jsonBodySerializer } from '@/shared/api/generated/core/bodySerializer.gen'
import type { HttpMethod } from '@/shared/api/generated/core/types.gen'
import { client as generatedApiClient } from '@/shared/api/generated/client.gen'
import { formatReferenceOption } from '@/shared/api/reference-options'

type ApiParams = Record<string, unknown>
type ApiRequestOptions = Omit<RequestInit, 'body'> & { params?: ApiParams; body?: unknown }
type PlainObject = Record<string, unknown>

const apiPrefixRaw = import.meta.env.VITE_API_PREFIX || '/api/v1'
const requestCaseMode = import.meta.env.VITE_API_REQUEST_CASE || 'snake'
const useSnakeCaseRequests = requestCaseMode === 'snake'

const normalizePrefix = (value: string) => {
  if (!value) {
    return ''
  }

  const withLeadingSlash = value.startsWith('/') ? value : `/${value}`
  return withLeadingSlash.replace(/\/+$/, '')
}

const apiPrefix = normalizePrefix(apiPrefixRaw)

const normalizeApiBaseUrl = (value: string) => {
  const withoutTrailingSlash = value.replace(/\/+$/, '')
  return apiPrefix && withoutTrailingSlash.endsWith(apiPrefix)
    ? withoutTrailingSlash.slice(0, -apiPrefix.length)
    : withoutTrailingSlash
}

const apiBaseUrl = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8080'
)

generatedApiClient.setConfig({
  baseUrl: apiBaseUrl,
  credentials: 'include',
  bodySerializer: jsonBodySerializer.bodySerializer
})

const isPlainObject = (value: unknown): value is PlainObject =>
  Object.prototype.toString.call(value) === '[object Object]'

const toSnakeCase = (value: string) =>
  value
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/[-\s]+/g, '_')
    .toLowerCase()

const toSnakeFieldPath = (value: string) =>
  value
    .split('.')
    .map((segment) => toSnakeCase(segment))
    .join('.')

const convertKeysToSnakeCase = (value: unknown): unknown => {
  if (Array.isArray(value)) {
    return value.map((item) => convertKeysToSnakeCase(item))
  }

  if (isPlainObject(value)) {
    return Object.fromEntries(
      Object.entries(value).map(([key, nested]) => [toSnakeCase(key), convertKeysToSnakeCase(nested)])
    )
  }

  return value
}

const normalizeParamValue = (key: string, value: unknown) => {
  if (!useSnakeCaseRequests) {
    return value
  }

  if (key === 'sort_by' && typeof value === 'string') {
    return toSnakeFieldPath(value)
  }

  if (key === 'sort_order') {
    if (typeof value === 'number') {
      return value === -1 ? 'desc' : 'asc'
    }

    if (typeof value === 'string') {
      const normalized = value.toLowerCase()
      if (normalized === '-1' || normalized === 'desc') {
        return 'desc'
      }
      if (normalized === '1' || normalized === 'asc') {
        return 'asc'
      }
    }
  }

  if (key === 'filters' && typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return JSON.stringify(convertKeysToSnakeCase(parsed))
    } catch {
      return value
    }
  }

  return value
}

let hooks = {
  onUnauthorized: () => {},
  onForbidden: () => {},
  // Attempt a token refresh. Resolves `true` when a fresh access token was
  // obtained (the failed request should be retried), `false` otherwise (the
  // session is gone — the refresh handler is responsible for logging out).
  onRefresh: async (): Promise<boolean> => false
}

export const setApiHooks = (next: Partial<typeof hooks>) => {
  hooks = { ...hooks, ...next }
}

// Endpoints that must never trigger the refresh-and-retry flow: the refresh
// call itself (would recurse), and login/logout (a 401 there is terminal).
const NON_REFRESHABLE_PATHS = ['/auth/refresh', '/auth/login', '/auth/logout']

const isRefreshablePath = (path: string) =>
  !NON_REFRESHABLE_PATHS.some((suffix) => path.replace(apiPrefix, '').startsWith(suffix))

const buildApiPath = (path: string) => {
  const isAbsolute = /^https?:\/\//i.test(path)
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return apiPrefix && !isAbsolute && !normalizedPath.startsWith(`${apiPrefix}/`)
      ? `${apiPrefix}${normalizedPath}`
      : normalizedPath
}

export const buildApiUrl = (path: string) => `${apiBaseUrl}${buildApiPath(path)}`

const normalizeQueryParams = (params?: ApiParams) => {
  if (!params) {
    return undefined
  }

  const requestParams = (useSnakeCaseRequests ? convertKeysToSnakeCase(params) : params) as ApiParams
  return Object.fromEntries(
    Object.entries(requestParams)
      .filter(([key]) => key !== 'offset')
      .map(([key, value]) => [key, normalizeParamValue(key, value)] as const)
      .filter(([, value]) => value !== undefined && value !== null && value !== '')
  )
}

const createHeaders = (
  headers: HeadersInit | undefined,
  hasJsonBody: boolean,
  isFormData: boolean
): HeadersInit => {
  const requestHeaders = new Headers(headers)

  if (hasJsonBody && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
  }

  if (isFormData) {
    // The generated client's default config always carries
    // `Content-Type: application/json`, and its header merge only drops a
    // key when the incoming value is a literal `null` on a plain object
    // (a `Headers` instance can't express that — its values are always
    // strings). Without this, that stale default header wins over the
    // browser's own `multipart/form-data; boundary=...` header and the
    // server can't parse the upload at all.
    return {
      ...Object.fromEntries(requestHeaders.entries()),
      'Content-Type': null
    } as unknown as HeadersInit
  }

  return requestHeaders
}

const getErrorMessage = (payload: unknown, fallback: string) => {
  if (typeof payload === 'string' && payload.trim()) {
    return payload
  }

  if (!isPlainObject(payload)) {
    return fallback
  }

  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((item) => (isPlainObject(item) ? item.msg || item.message : null))
      .filter(Boolean)
      .join('; ') || fallback
  }

  if (typeof payload.detail === 'string') {
    return payload.detail
  }

  if (typeof payload.message === 'string') {
    return payload.message
  }

  if (typeof payload.title === 'string') {
    return payload.title
  }

  return fallback
}

const normalizeResponseMeta = <T>(payload: T): T => {
  if (!isPlainObject(payload) || !isPlainObject(payload.meta)) {
    return payload
  }

  return {
    ...payload,
    meta: {
      ...payload.meta,
      requestId: payload.meta.request_id ?? payload.meta.requestId ?? null,
      includesRequested: payload.meta.includes_requested ?? payload.meta.includesRequested ?? [],
      includesApplied: payload.meta.includes_applied ?? payload.meta.includesApplied ?? [],
      includesAllowed: payload.meta.includes_allowed ?? payload.meta.includesAllowed ?? [],
      nextCursor: payload.meta.next_cursor ?? payload.meta.nextCursor ?? null,
      hasMore: payload.meta.has_more ?? payload.meta.hasMore
    }
  }
}

export interface ApiClientError {
  status: number
  code?: string
  message: string
}

export const apiRequest = async <T>(
  path: string,
  options: ApiRequestOptions = {},
  allowRefresh = true
): Promise<T> => {
  const { body, headers, method = 'GET', params, ...requestInit } = options
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  const requestBody =
    !isFormData && useSnakeCaseRequests && body !== undefined ? convertKeysToSnakeCase(body) : body

  const result = await generatedApiClient.request<T, unknown, false, 'fields'>({
    ...requestInit,
    method: method.toUpperCase() as Uppercase<HttpMethod>,
    url: buildApiPath(path),
    query: normalizeQueryParams(params),
    body: requestBody,
    bodySerializer: isFormData ? undefined : jsonBodySerializer.bodySerializer,
    credentials: 'include',
    headers: createHeaders(headers, !isFormData && requestBody !== undefined, isFormData),
    responseStyle: 'fields',
    throwOnError: false
  })

  if (result.error !== undefined) {
    const payload = result.error
    const payloadRecord = isPlainObject(payload) ? payload : {}
    const status = result.response?.status ?? 0
    const error: ApiClientError = {
      status,
      code: typeof payloadRecord.code === 'string'
        ? payloadRecord.code
        : typeof payloadRecord.type === 'string'
          ? payloadRecord.type
          : undefined,
      message: getErrorMessage(payload, result.response?.statusText || 'Network error')
    }

    if (status === 401) {
      // Access token expired: refresh once, then replay the original request.
      // If refreshing fails the session is unrecoverable → sign the user out.
      if (allowRefresh && isRefreshablePath(path)) {
        const refreshed = await hooks.onRefresh()
        if (refreshed) {
          return apiRequest<T>(path, options, false)
        }
      }
      hooks.onUnauthorized()
    }

    if (status === 403) {
      hooks.onForbidden()
    }

    throw error
  }

  return normalizeResponseMeta(result.data as T)
}

export const apiReadListRequest = async <T>(
  path: string,
  options: ApiRequestOptions = {}
) => apiRequest<ApiViewResponse<T>>(path, options)

export const apiReadRequest = async <T>(
  path: string,
  options: ApiRequestOptions = {}
) => apiRequest<ApiReadResponse<T>>(path, options)

export const apiCreateRequest = async <T>(
  path: string,
  options: ApiRequestOptions = {}
) => apiRequest<ApiCreateResponse<T>>(path, options)

export const apiUpdateRequest = async <T>(
  path: string,
  options: ApiRequestOptions = {}
) => apiRequest<ApiUpdateResponse<T>>(path, options)

export const apiDeleteRequest = async <T>(
  path: string,
  options: ApiRequestOptions = {}
) => apiRequest<ApiDeleteResponse<T>>(path, options)

export const apiCommandRequest = async <T>(
  path: string,
  options: ApiRequestOptions = {}
) => apiRequest<ApiCommandResponse<T>>(path, options)

const REFERENCE_PAGE_SIZE = 100
const REFERENCE_MAX_ITEMS = 5000

export const loadReferenceOptions = async (
  path: string,
  params: ApiParams = {}
): Promise<Array<{ label: string; value: string | number | boolean | null }>> => {
  const options: Array<{ label: string; value: string | number | boolean | null }> = []
  let cursor: string | null = typeof params.cursor === 'string' ? params.cursor : null

  do {
    const page = await loadReferenceOptionsPage(path, { ...params, cursor })
    options.push(...page.options)
    cursor = page.nextCursor
  } while (cursor && options.length < REFERENCE_MAX_ITEMS)

  return options
}

export const loadReferenceOptionsPage = async (
  path: string,
  params: ApiParams = {}
): Promise<{
  options: Array<{ label: string; value: string | number | boolean | null }>
  nextCursor: string | null
}> => {
  const response = await apiReadListRequest<PlainObject>(path, {
    method: 'GET',
    params: {
      ...params,
      limit: params.limit ?? REFERENCE_PAGE_SIZE
    }
  })

  return {
    nextCursor: response.meta.nextCursor ?? null,
    options: response.items.map((row) => formatReferenceOption(row, path))
  }
}

export { generatedApiClient as backendApiClient }
