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
      {
        path: "/research",
        name: "research",
        meta: { requiresAuth: false },
        component: () => import("@/pages/ResearchPage.vue"),
      },
      {
        path: "/workflows",
        name: "workflows",
        meta: { requiresAuth: false },
        component: () => import("@/pages/UserFlowsPage.vue"),
      },
      {
        path: "/settings",
        component: () => import("@/modules/settings/pages/SettingsLayoutPage.vue"),
        meta: { requiresAuth: false },
        children: [
          {
            path: "",
            name: "settings",
            component: () => import("@/modules/settings/pages/SettingsIndexPage.vue"),
          },
          {
            path: "members",
            name: "settings-members",
            component: () => import("@/modules/settings/pages/SettingsMembersPage.vue"),
          },
          {
            path: "notifications",
            name: "settings-notifications",
            component: () => import("@/modules/settings/pages/SettingsNotificationsPage.vue"),
          },
          {
            path: "security",
            name: "settings-security",
            component: () => import("@/modules/settings/pages/SettingsSecurityPage.vue"),
          },
        ],
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
