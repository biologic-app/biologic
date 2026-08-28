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
        meta: { requiresAuth: true, permission: "dashboard.read" },
        component: () => import("@/pages/DashboardPage.vue"),
      },
      {
        path: "/data-operations",
        name: "data-operations",
        meta: { requiresAuth: true },
        component: () => import("@/pages/DataOperationsPage.vue"),
      },
      {
        name: "directions",
        path: "/directions",
        meta: { requiresAuth: true, permission: "directions.read" },
        component: () => import("@/pages/DirectionsPage.vue"),
      },
      {
        path: "/research",
        name: "research",
        meta: { requiresAuth: true, permission: "research.read" },
        component: () => import("@/pages/ResearchPage.vue"),
      },
      {
        path: "/research-v2",
        name: "research-v2",
        meta: { requiresAuth: true, permission: "research.read" },
        component: () => import("@/pages/ResearchV2Page.vue"),
      },
      {
        path: "/workflows/:id?",
        name: "workflows",
        meta: { requiresAuth: true, permission: "research.read" },
        component: () => import("@/pages/WorkflowsPage.vue"),
      },
      {
        path: "/samples",
        name: "samples",
        meta: { requiresAuth: true, permission: "samples.read" },
        component: () => import("@/pages/SamplesPage.vue"),
      },
      {
        path: "/tests",
        name: "tests",
        meta: { requiresAuth: true, permission: "tests.read" },
        component: () => import("@/pages/TestsPage.vue"),
      },
      {
        path: "/protocols",
        name: "protocols",
        meta: { requiresAuth: true, permission: "protocols.read" },
        component: () => import("@/pages/ProtocolsPage.vue"),
      },
      {
        path: "/dictionaries/:module?",
        name: "dictionaries",
        meta: { requiresAuth: true, permission: "statuses.read" },
        component: () => import("@/modules/dictionaries/pages/DictionariesPage.vue"),
      },
      {
        path: "/access",
        redirect: { name: "access-users" },
      },
      {
        path: "/access/users",
        name: "access-users",
        meta: { requiresAuth: true, permission: "users.read" },
        component: () => import("@/modules/admin/pages/UsersPage.vue"),
      },
      {
        path: "/access/roles",
        name: "access-roles",
        meta: { requiresAuth: true, permission: "roles.read" },
        component: () => import("@/modules/user-types/pages/UserTypesPage.vue"),
      },
      {
        path: "/access/subscriptions",
        name: "access-subscriptions",
        meta: { requiresAuth: true, permission: "roles.read" },
        component: () => import("@/modules/access/pages/AccessSubscriptionsPage.vue"),
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
