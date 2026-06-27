import type { Router } from "vue-router";
import { useAuth } from "@/modules/auth";

export const registerGuard = (router: Router) => {
  router.beforeEach((to) => {
    if (!to.meta.requiresAuth) return true;

    const auth = useAuth();
    if (auth.isAuthenticated) return true;

    return { name: "login", query: { redirect: to.fullPath } };
  });
};
