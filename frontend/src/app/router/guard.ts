import type { Router } from "vue-router";
import { useAuth } from "@/modules/auth";
import type { Action, Resource } from "@/shared/types/permissions";

export const registerGuard = (router: Router) => {
  router.beforeEach(async (to) => {
    if (!to.meta.requiresAuth) return true;

    const auth = useAuth();
    if (!auth.initialized) {
      await auth.restoreSession();
    }
    if (!auth.isAuthenticated) {
      return { name: "login", query: { redirect: to.fullPath } };
    }

    const permission = to.meta.permission;
    if (!permission || auth.isSuperAdmin) return true;
    const separator = permission.indexOf(".");
    if (separator <= 0) return { name: "forbidden" };
    const resource = permission.slice(0, separator);
    const action = permission.slice(separator + 1);
    if (auth.can(resource as Resource, action as Action)) return true;
    return { name: "forbidden" };
  });
};
