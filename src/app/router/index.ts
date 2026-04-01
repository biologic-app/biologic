import { createRouter, createWebHistory } from "vue-router";
import { routes } from "./routes";
import { useAuth } from "@/modules/auth";

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from) => {
  const auth = useAuth();

  if (!auth.isAuthenticated && to.meta.requiresAuth) {
    return { name: "login" };
  } else if (
    to.meta.resource &&
    to.meta.action &&
    !auth.can(to.meta.resource, to.meta.action)
  ) {
    return { name: "forbidden", query: { redirect: from.name } };
  } else {
    return true;
  }
});
