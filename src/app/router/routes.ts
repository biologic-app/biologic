import { crudModules } from "@/shared/config/crud-modules";
import { RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    component: () => import("@/app/layouts/LoginLayout.vue"),
    children: [
      {
        path: "",
        name: "login",
        meta: { requiresAuth: false },
        component: () => import("@/pages/LoginPage.vue"),
      },
    ],
  },
  {
    path: "/",
    component: () => import("@/app/layouts/MainLayout.vue"),
    children: [
      {
        path: "",
        redirect: { name: "dashboard" },
      },
      {
        path: "/dashboard",
        name: "dashboard",
        meta: { requiresAuth: false },
        component: () => import("@/pages/DashboardPage.vue"),
      },
    ],
  },

  {
    path: "/",
    component: () => import("@/app/layouts/MainLayout.vue"),
    children: [
      {
        name: "directions",
        path: "/directions",
        props: { config: crudModules.directions },
        meta: { requiresAuth: true, resource: "directions", action: "view" },
        component: () => import("@/pages/CrudModulePage.vue"),
      },
      {
        path: "/customers",
        name: "customers",
        meta: { requiresAuth: false },
        component: () => import("@/pages/CustomersPage.vue"),
      },
      {
        path: "/inbox",
        name: "inbox",
        meta: { requiresAuth: false },
        component: () => import("@/pages/InboxPage.vue"),
      },
    ],
  },
  {
    path: "/forbidden",
    component: () => import("@/app/layouts/ErrorLayout.vue"),
    children: [
      {
        path: "",
        name: "forbidden",
        meta: { requiresAuth: false },
        component: () => import("@/pages/ForbiddenPage.vue"),
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    component: () => import("@/app/layouts/ErrorLayout.vue"),
    children: [
      {
        path: "",
        meta: { requiresAuth: false },
        component: () => import("@/pages/NotFoundPage.vue"),
      },
    ],
  },
];
