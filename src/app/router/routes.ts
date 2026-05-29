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
        meta: { requiresAuth: false },
        component: () => import("@/pages/DirectionsPage.vue"),
      },
      {
        path: "/research",
        name: "research",
        meta: { requiresAuth: false },
        component: () => import("@/pages/ResearchPage.vue"),
      },
      {
        path: "/samples",
        name: "samples",
        meta: { requiresAuth: false },
        component: () => import("@/pages/SamplesPage.vue"),
      },
      {
        path: "/dictionaries/:module?",
        name: "dictionaries",
        meta: { requiresAuth: false },
        component: () => import("@/modules/dictionaries/pages/DictionariesPage.vue"),
      },
      {
        path: "/access",
        redirect: { name: "access-users" },
      },
      {
        path: "/access/users",
        name: "access-users",
        meta: { requiresAuth: false },
        component: () => import("@/modules/admin/pages/UsersPage.vue"),
      },
      {
        path: "/access/roles",
        name: "access-roles",
        meta: { requiresAuth: false },
        component: () => import("@/modules/user-types/pages/UserTypesPage.vue"),
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
