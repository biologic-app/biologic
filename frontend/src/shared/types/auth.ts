import type { Permission } from '@/shared/types/permissions'

export interface AuthUser {
  id: string
  login: string
  email: string
  fullName: string
  role: string
  status: string
  department: {
    id: number | null
    name: string | null
  }
  deletedAt: string | null
}

export interface AuthData {
  user: AuthUser
  permissions: Permission[]
  accessExpiresAt: string
  refreshExpiresAt: string
}

export interface AuthResponse {
  data: AuthData
  meta: {
    timestamp: string
    requestId: string | null
    version: string
    operation: string | null
  }
}
