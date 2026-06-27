import { createRouter, createWebHistory } from "vue-router";
import { routes } from "./routes";
import { registerGuard } from "./guard";

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

registerGuard(router);
