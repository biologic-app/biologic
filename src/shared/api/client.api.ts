import type {
  ApiCommandResponse,
  ApiCreateResponse,
  ApiDeleteResponse,
  ApiReadResponse,
  ApiUpdateResponse,
  ApiViewResponse
} from '@/shared/types/api'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
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

const isPlainObject = (value: unknown): value is Record<string, any> =>
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

const convertKeysToSnakeCase = (value: any): any => {
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

const buildUrl = (path: string, params?: Record<string, any>) => {
  const isAbsolute = /^https?:\/\//i.test(path)
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const withPrefix =
    apiPrefix && !isAbsolute && !normalizedPath.startsWith(`${apiPrefix}/`)
      ? `${apiPrefix}${normalizedPath}`
      : path

  const url = new URL(withPrefix, apiBaseUrl || window.location.origin)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      const normalizedValue = normalizeParamValue(key, value)
      if (normalizedValue === undefined || normalizedValue === null || normalizedValue === '') {
        return
      }
      url.searchParams.set(key, String(normalizedValue))
    })
  }

  return apiBaseUrl ? url.toString() : `${url.pathname}${url.search}`
}

const parseResponse = async (response: Response) => {
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json()
  }
  return response.text()
}

export interface ApiClientError {
  status: number
  code?: string
  message: string
}

export const apiRequest = async <T>(
  path: string,
  options: Omit<RequestInit, 'body'> & { params?: Record<string, any>; body?: any } = {}
): Promise<T> => {
  const requestParams =
    useSnakeCaseRequests && options.params ? convertKeysToSnakeCase(options.params) : options.params
  const url = buildUrl("/api/v1" + path, requestParams)
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  const requestBody =
    !isFormData && useSnakeCaseRequests && options.body !== undefined
      ? convertKeysToSnakeCase(options.body)
      : options.body

  const init: RequestInit = {
    method: options.method || 'GET',
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers || {})
    },
    credentials: 'include'
  }

  if (requestBody !== undefined) {
    init.body = isFormData ? requestBody : JSON.stringify(requestBody)
  }

  const response = await fetch("http://localhost:8080" +url, init)

  if (!response.ok) {
    const payload = await parseResponse(response)
    const error: ApiClientError = {
      status: response.status,
      code: payload?.code || payload?.type,
      message: payload?.message || payload?.detail || payload?.title || response.statusText
    }

    if (response.status === 401) {
      hooks.onUnauthorized()
    }

    if (response.status === 403) {
      hooks.onForbidden()
    }

    throw error
  }

  return parseResponse(response) as Promise<T>
}

export const apiReadListRequest = async <T>(
  path: string,
  options: Omit<RequestInit, 'body'> & { params?: Record<string, any>; body?: any } = {}
) => apiRequest<ApiViewResponse<T>>(path, options)

export const apiReadRequest = async <T>(
  path: string,
  options: Omit<RequestInit, 'body'> & { params?: Record<string, any>; body?: any } = {}
) => apiRequest<ApiReadResponse<T>>(path, options)

export const apiCreateRequest = async <T>(
  path: string,
  options: Omit<RequestInit, 'body'> & { params?: Record<string, any>; body?: any } = {}
) => apiRequest<ApiCreateResponse<T>>(path, options)

export const apiUpdateRequest = async <T>(
  path: string,
  options: Omit<RequestInit, 'body'> & { params?: Record<string, any>; body?: any } = {}
) => apiRequest<ApiUpdateResponse<T>>(path, options)

export const apiDeleteRequest = async <T>(
  path: string,
  options: Omit<RequestInit, 'body'> & { params?: Record<string, any>; body?: any } = {}
) => apiRequest<ApiDeleteResponse<T>>(path, options)

export const apiCommandRequest = async <T>(
  path: string,
  options: Omit<RequestInit, 'body'> & { params?: Record<string, any>; body?: any } = {}
) => apiRequest<ApiCommandResponse<T>>(path, options)

export const loadReferenceOptions = async (
  path: string,
  params: Record<string, any> = {}
): Promise<Array<{ label: string; value: string | number | boolean | null }>> => {
  const response = await apiReadListRequest<Record<string, any>>(path, {
    method: 'GET',
    params: {
      offset: 0,
      limit: 500,
      ...params
    }
  })

  return response.items.map((row) => {
    if (row.name && row.code) {
      return { label: `${row.name} (${row.code})`, value: row.id }
    }

    return {
      label: row.name || row.code || String(row.id),
      value: row.id
    }
  })
}
