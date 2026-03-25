import { useApi } from '@/shared/api/client'
import type { ApiError } from '@/shared/types/api'
import type { NamedRef } from '@/shared/types/api'
import type { Action, Permission, Resource } from '@/shared/types/permissions'

export interface AuthUser {
  id: string
  login: string
  email: string
  fullName: string
  role: string
  status: string
  department: NamedRef
  deletedAt: string | null
}

export interface AuthResponse {
  user: AuthUser
  permissions: Permission[]
}

interface BackendAuthEnvelope {
  data: {
    user: {
      id: string
      username: string
      role_key: string
      role_name: string
      first_name: string | null
      last_name: string | null
      patronymic: string | null
    }
    permissions: Array<{ resource: string; action: string }>
    access_expires_at: string
    refresh_expires_at: string | null
  }
  meta: {
    timestamp: string
    request_id: string | null
    version: string
    operation: string | null
  }
}

const knownResources: Resource[] = [
  'dashboard',
  'directions',
  'samples',
  'sample-targets',
  'protocols',
  'results',
  'conclusions',
  'tests',
  'doctors',
  'branches',
  'labs',
  'users',
  'research-goals',
  'sample-types',
  'indicators',
  'protocol-types',
  'statuses',
  'user-types',
  'objects'
]

const knownActions: Action[] = ['view', 'create', 'edit', 'delete']

const mapResource = (resource: string): Resource | null => {
  const normalized = resource
    .trim()
    .toLowerCase()
    .replace(/_/g, '-')
  const mapped = normalized === 'roles' || normalized === 'role-permissions' ? 'user-types' : normalized
  return knownResources.includes(mapped as Resource) ? mapped as Resource : null
}

const mapAction = (action: string): Action | null => {
  const normalized = action.trim().toLowerCase()
  const mapped = normalized === 'read' ? 'view' : normalized === 'update' ? 'edit' : normalized
  return knownActions.includes(mapped as Action) ? mapped as Action : null
}

const mapPermissions = (permissions: Array<{ resource: string; action: string }>): Permission[] => {
  const normalized = new Map<string, Permission>()

  permissions.forEach((permission) => {
    const resource = mapResource(permission.resource)
    const action = mapAction(permission.action)

    if (!resource || !action) {
      return
    }

    const key = `${resource}:${action}`
    normalized.set(key, { resource, action })
  })

  if (!normalized.has('dashboard:view')) {
    normalized.set('dashboard:view', { resource: 'dashboard', action: 'view' })
  }

  return Array.from(normalized.values())
}

const mapUser = (payload: BackendAuthEnvelope['data']['user']): AuthUser => {
  const fullName = [payload.first_name, payload.last_name, payload.patronymic].filter(Boolean).join(' ').trim()

  return {
    id: payload.id,
    login: payload.username,
    email: `${payload.username}@local`,
    fullName: fullName || payload.username,
    role: payload.role_key,
    status: 'active',
    department: { id: null, name: null } satisfies NamedRef,
    deletedAt: null
  }
}

const mapSession = (payload: BackendAuthEnvelope['data']): AuthResponse => ({
  user: mapUser(payload.user),
  permissions: mapPermissions(payload.permissions || [])
})

const unwrap = async <T>(request: {
  data: { value: T | null }
  error: { value: unknown }
  execute: (throwOnFailed?: boolean) => Promise<unknown>
}): Promise<T> => {
  await request.execute()

  if (request.error.value) {
    throw request.error.value as ApiError
  }

  if (!request.data.value) {
    throw {
      status: 0,
      message: 'Empty response'
    } satisfies ApiError
  }

  return request.data.value
}

export const login = async (loginValue: string, password: string) => {
  const request = useApi('/auth/login', { immediate: false })
    .post({ username: loginValue, password })
    .json<BackendAuthEnvelope>()

  const response = await unwrap(request)

  return mapSession(response.data)
}

export const logout = async () => {
  const request = useApi('/auth/logout', { immediate: false })
    .post()
    .json<{ meta: unknown }>()

  await unwrap(request)
}

export const me = async () => {
  const request = useApi('/auth/me', { immediate: false })
    .get()
    .json<BackendAuthEnvelope>()

  const response = await unwrap(request)
  return mapSession(response.data)
}
