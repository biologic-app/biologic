import { defineStore } from 'pinia'
import * as authApi from './auth.api'
import type { Permission } from '@/shared/types/permissions'
import type { AuthUser } from './auth.api'
import { login } from '@/modules/auth/auth.api'

interface AuthState {
  user: AuthUser | null
  permissions: Permission[]
  loading: boolean
  initialized: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    permissions: [],
    loading: false,
    initialized: false
  }),
  getters: {
    isAuthenticated: (state) => !!state.user
  },
  actions: {
    setSession(user: AuthUser, permissions: Permission[]) {
      this.user = user
      this.permissions = permissions
      this.initialized = true
    },
    clearSession() {
      this.user = null
      this.permissions = []
      this.loading = false
      this.initialized = true
    },
    async login(username: string, password: string) {
      this.loading = true
      try {
        const response = await login(username, password)
        this.setSession(response.user, response.permissions)
      } finally {
        this.loading = false
      }
    },
    async logout() {
      this.loading = true
      try {
        await authApi.logout()
      } finally {
        this.clearSession()
        this.loading = false
      }
    },
    async restoreSession() {
      this.loading = true
      try {
        const response = await authApi.me()
        this.setSession(response.user, response.permissions)
      } catch (error: any) {
        this.clearSession()
      } finally {
        this.loading = false
      }
    },
    logoutLocal() {
      this.clearSession()
    },
    can(resource: string, action: string) {
      return this.permissions.some((perm) => perm.resource === resource && perm.action === action)
    }
  }
})
