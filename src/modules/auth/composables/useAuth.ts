import { defineStore } from "pinia";
import { useStorage } from "@vueuse/core";
import { computed, ref } from "vue";
import * as authApi from "../auth.api";
import type { Action, Permission, Resource } from "@/shared/types/permissions";
import type { AuthUser } from "@/shared/types/auth";
import {
  defaultUserModeId,
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
  const loading = ref(false);
  const initialized = ref(false);

  const isAuthenticated = computed(() => !!user.value);

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

  const setSession = (newUser: AuthUser, newPermissions: Permission[]) => {
    user.value = newUser;
    permissions.value = newPermissions;
    initialized.value = true;
  };

  const clearSession = () => {
    user.value = null;
    permissions.value = [];
    loading.value = false;
    initialized.value = true;
  };

  const login = async (loginValue: string, password: string) => {
    loading.value = true;
    try {
      const response = await authApi.login(loginValue, password);
      setSession(response.user, response.permissions);
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
      setSession(response.user, response.permissions);
    } catch {
      clearSession();
    } finally {
      loading.value = false;
    }
  };

  const can: (resource: Resource, action: Action) => boolean = (
    resource,
    action,
  ) => modeAllows(effectivePermissions.value, resource, action);

  return {
    user,
    permissions,
    loading,
    initialized,
    isAuthenticated,
    activeModeId,
    activeMode,
    effectivePermissions,
    setMode,
    setSession,
    clearSession,
    login,
    loginAs,
    logout,
    restoreSession,
    logoutLocal: clearSession,
    can,
  };
});
