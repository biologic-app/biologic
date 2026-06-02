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
  onForbidden: () => {}
}

export const setApiHooks = (next: Partial<typeof hooks>) => {
  hooks = { ...hooks, ...next }
}

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

const createHeaders = (headers: HeadersInit | undefined, hasJsonBody: boolean) => {
  const requestHeaders = new Headers(headers)

  if (hasJsonBody && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
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
  options: ApiRequestOptions = {}
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
    headers: createHeaders(headers, !isFormData && requestBody !== undefined),
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

const toOptionValue = (value: unknown) =>
  typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
    ? value
    : value === null
      ? null
      : String(value)

const REFERENCE_PAGE_SIZE = 100
const REFERENCE_MAX_ITEMS = 5000

const compact = (items: Array<string | number | null | undefined | false>) =>
  items
    .map((item) => item === null || item === undefined || item === false ? '' : String(item).trim())
    .filter(Boolean)

const formatShortId = (value: unknown) => {
  if (typeof value !== 'string' && typeof value !== 'number') {
    return 'запись'
  }

  const text = String(value)
  const uuidPrefix = text.match(/^[0-9a-f]{8}/i)?.[0]
  return (uuidPrefix ?? text.slice(0, 8)).toUpperCase()
}

const formatReferenceLabel = (row: PlainObject) => {
  if (row.name && row.code) {
    return `${String(row.name)} (${String(row.code)})`
  }

  if (row.name || row.full_name || row.code) {
    return String(row.name || row.full_name || row.code)
  }

  const personName = compact([row.last_name as string, row.first_name as string, row.patronymic as string]).join(' ')
  if (personName) {
    return personName
  }

  const documentNumber = compact([
    row.year_no ? `${row.year_no}` : null,
    row.base_no ? `№ ${row.base_no}` : null
  ]).join(' ')
  if (documentNumber) {
    return documentNumber
  }

  const researchParts = compact([
    row.sample_id ? `образец ${formatShortId(row.sample_id)}` : null,
    row.research_goal_id ? `цель ${formatShortId(row.research_goal_id)}` : null
  ])
  if (researchParts.length) {
    return `Исследование: ${researchParts.join(', ')}`
  }

  return `Запись ${formatShortId(row.id)}`
}

export const loadReferenceOptions = async (
  path: string,
  params: ApiParams = {}
): Promise<Array<{ label: string; value: string | number | boolean | null }>> => {
  const items: PlainObject[] = []
  let cursor: unknown = params.cursor

  do {
    const response = await apiReadListRequest<PlainObject>(path, {
      method: 'GET',
      params: {
        ...params,
        limit: params.limit ?? REFERENCE_PAGE_SIZE,
        cursor
      }
    })

    items.push(...response.items)
    cursor = response.meta.nextCursor ?? null
  } while (cursor && items.length < REFERENCE_MAX_ITEMS)

  return items.map((row) => {
    return {
      label: formatReferenceLabel(row),
      value: toOptionValue(row.id)
    }
  })
}

export { generatedApiClient as backendApiClient }
