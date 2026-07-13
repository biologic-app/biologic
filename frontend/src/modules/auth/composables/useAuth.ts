import { defineStore } from "pinia";
import { useStorage } from "@vueuse/core";
import { computed, ref } from "vue";
import * as authApi from "../auth.api";
import type { Action, Permission, Resource } from "@/shared/types/permissions";
import type { AuthUser } from "@/shared/types/auth";
import {
  defaultUserModeId,
  isSuperAdminRole,
  isUserModeId,
  modeAllows,
  resolveModePermissions,
  resolveUserMode,
  type ModePermission,
  type UserModeId,
} from "@/shared/config/user-modes";
import { roleCredentials } from "@/shared/config/role-credentials";
import { router } from "@/app/router";

export const useAuth = defineStore("auth", () => {
  const user = useStorage<AuthUser | null>("auth:user", null);
  // Права роли с бэкенда (наполняются при логине/restoreSession).
  // Источник истины для can(): если массив непустой — берём его, иначе
  // фронтовый пресет активного режима (см. effectivePermissions ниже).
  const permissions = useStorage<Permission[]>("auth:permissions", []);
  const activeModeId = useStorage<UserModeId>("auth:mode", defaultUserModeId);
  // ISO timestamps returned by the backend. Persisted so a page reload can
  // reschedule the silent refresh without waiting for the next request.
  const accessExpiresAt = useStorage<string | null>("auth:accessExpiresAt", null);
  const refreshExpiresAt = useStorage<string | null>("auth:refreshExpiresAt", null);
  const loading = ref(false);
  const initialized = ref(false);

  // Refresh the access token this long before it actually expires, so an
  // in-flight request never races the expiry boundary.
  const REFRESH_LEEWAY_MS = 5 * 60 * 1000;
  let refreshTimer: ReturnType<typeof setTimeout> | null = null;
  // Single-flight guard: concurrent 401s (or a timer firing mid-request) must
  // share one refresh call, not stampede the backend.
  let refreshPromise: Promise<boolean> | null = null;

  const clearRefreshTimer = () => {
    if (refreshTimer !== null) {
      clearTimeout(refreshTimer);
      refreshTimer = null;
    }
  };

  const scheduleRefresh = () => {
    clearRefreshTimer();
    if (!accessExpiresAt.value) return;
    const expiresMs = new Date(accessExpiresAt.value).getTime();
    if (Number.isNaN(expiresMs)) return;
    const delay = Math.max(0, expiresMs - Date.now() - REFRESH_LEEWAY_MS);
    refreshTimer = setTimeout(() => {
      void refresh();
    }, delay);
  };

  const isAuthenticated = computed(() => !!user.value);
  // Суперадмин (роль developer) обходит проверку прав — см. superAdminRoles.
  const isSuperAdmin = computed(() => isSuperAdminRole(user.value?.role));

  const activeMode = computed(() => resolveUserMode(activeModeId.value));
  // Источник истины — права с бэкенда. Пустой массив ⇒ default-deny.
  // Фронтовый пресет режима остаётся только дев-удобством (см. setMode).
  const effectivePermissions = computed<ModePermission[]>(() => {
    if (permissions.value.length > 0) {
      return permissions.value as unknown as ModePermission[];
    }
    return import.meta.env.DEV
      ? resolveModePermissions(activeModeId.value)
      : [];
  });

  const setMode = (modeId: UserModeId) => {
    if (!import.meta.env.DEV) return;
    if (isUserModeId(modeId)) {
      activeModeId.value = modeId;
    }
  };

  const setSession = (
    newUser: AuthUser,
    newPermissions: Permission[],
    newAccessExpiresAt: string | null = null,
    newRefreshExpiresAt: string | null = null,
  ) => {
    user.value = newUser;
    permissions.value = newPermissions;
    accessExpiresAt.value = newAccessExpiresAt;
    refreshExpiresAt.value = newRefreshExpiresAt;
    initialized.value = true;
    scheduleRefresh();
  };

  const clearSession = () => {
    clearRefreshTimer();
    user.value = null;
    permissions.value = [];
    accessExpiresAt.value = null;
    refreshExpiresAt.value = null;
    loading.value = false;
    initialized.value = true;
  };

  // Session is unrecoverable (refresh failed / no valid session). Drop local
  // state and bounce to the login screen. Idempotent — safe to call twice.
  const handleAuthLoss = () => {
    clearSession();
    if (router.currentRoute.value.name !== "login") {
      void router.push({ name: "login" });
    }
  };

  // Exchange the refresh token for a new access token. On failure the session
  // is torn down (requirement: refresh yields no access token → logout).
  const refresh = (): Promise<boolean> => {
    if (refreshPromise) return refreshPromise;
    refreshPromise = (async () => {
      try {
        const response = await authApi.refresh();
        setSession(
          response.user,
          response.permissions,
          response.accessExpiresAt,
          response.refreshExpiresAt,
        );
        return true;
      } catch {
        handleAuthLoss();
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
    return refreshPromise;
  };

  const login = async (
    loginValue: string,
    password: string,
    rememberMe = false,
  ) => {
    loading.value = true;
    try {
      const response = await authApi.login(loginValue, password, rememberMe);
      setSession(
        response.user,
        response.permissions,
        response.accessExpiresAt,
        response.refreshExpiresAt,
      );
    } finally {
      loading.value = false;
    }
  };

  const loginAs = async (modeId: UserModeId) => {
    const creds = roleCredentials[modeId];
    if (!creds) return;
    if (isUserModeId(modeId)) {
      activeModeId.value = modeId;
    }
    await login(creds.username, creds.password);
  };

  const logout = async () => {
    loading.value = true;
    try {
      await authApi.logout();
    } finally {
      clearSession();
      loading.value = false;
      await router.push({ name: "login" });
    }
  };

  const restoreSession = async () => {
    loading.value = true;
    try {
      const response = await authApi.me();
      setSession(
        response.user,
        response.permissions,
        response.accessExpiresAt,
        response.refreshExpiresAt,
      );
    } catch {
      clearSession();
    } finally {
      loading.value = false;
    }
  };

  const can: (resource: Resource, action: Action) => boolean = (
    resource,
    action,
  ) =>
    isSuperAdmin.value ||
    modeAllows(effectivePermissions.value, resource, action);

  return {
    user,
    permissions,
    loading,
    initialized,
    isAuthenticated,
    isSuperAdmin,
    activeModeId,
    activeMode,
    effectivePermissions,
    setMode,
    setSession,
    clearSession,
    login,
    loginAs,
    logout,
    refresh,
    restoreSession,
    logoutLocal: clearSession,
    handleAuthLoss,
    can,
  };
});
