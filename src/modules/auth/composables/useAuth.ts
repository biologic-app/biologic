import { defineStore } from "pinia";
import { useStorage } from "@vueuse/core";
import { computed, ref } from "vue";
import * as authApi from "../auth.api";
import type { Action, Permission, Resource } from "@/shared/types/permissions";
import type { AuthUser } from "@/shared/types/auth";

export const useAuth = defineStore("auth", () => {
  const user = useStorage<AuthUser | null>("auth:user", null);
  const permissions = useStorage<Permission[]>("auth:permissions", []);
  const loading = ref(false);
  const initialized = ref(false);

  const isAuthenticated = computed(() => !!user.value);

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

  const logout = async () => {
    loading.value = true;
    try {
      await authApi.logout();
    } finally {
      clearSession();
      loading.value = false;
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

  const can: (resource: Resource, action: Action) => boolean = () => true;

  return {
    user,
    permissions,
    loading,
    initialized,
    isAuthenticated,
    setSession,
    clearSession,
    login,
    logout,
    restoreSession,
    logoutLocal: clearSession,
    can,
  };
});
