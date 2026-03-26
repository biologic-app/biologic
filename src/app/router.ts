import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/shared/layouts/MainLayout.vue'
import ErrorLayout from '@/shared/layouts/ErrorLayout.vue'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'
import NotFoundPage from '@/shared/pages/NotFoundPage.vue'
import CrudModulePage from '@/shared/pages/CrudModulePage.vue'
import { crudModules } from '@/shared/config/crud-modules'
import CustomersPage from '@/modules/customers/pages/CustomersPage.vue'
import DashboardPage from '@/modules/dashboard/pages/DashboardPage.vue'
import InboxPage from '@/modules/inbox/pages/InboxPage.vue'
import SettingsLayoutPage from '@/modules/settings/pages/SettingsLayoutPage.vue'
import SettingsIndexPage from '@/modules/settings/pages/SettingsIndexPage.vue'
import SettingsMembersPage from '@/modules/settings/pages/SettingsMembersPage.vue'
import SettingsNotificationsPage from '@/modules/settings/pages/SettingsNotificationsPage.vue'
import SettingsSecurityPage from '@/modules/settings/pages/SettingsSecurityPage.vue'
import LoginPage from '@/modules/auth/pages/LoginPage.vue'
import ForbiddenPage from '@/modules/auth/pages/ForbiddenPage.vue'
import UsersPage from '@/modules/admin/pages/UsersPage.vue'
import UserTypesPage from '@/modules/user-types/pages/UserTypesPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: AuthLayout,
      meta: { public: true },
      children: [
        {
          path: '',
          name: 'login',
          component: LoginPage,
          meta: { public: true }
        }
      ]
    },
    {
      path: '/forbidden',
      component: ErrorLayout,
      meta: { public: true },
      children: [
        {
          path: '',
          name: 'forbidden',
          component: ForbiddenPage,
          meta: { public: true }
        }
      ]
    },
    {
      path: '/',
      component: MainLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: { name: 'dashboard' }
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: DashboardPage,
          meta: { requiresAuth: true, resource: 'dashboard', action: 'view' }
        },
        {
          path: 'customers',
          name: 'customers',
          component: CustomersPage,
          meta: { requiresAuth: true, resource: 'customers', action: 'view' }
        },
        {
          path: 'inbox',
          name: 'inbox',
          component: InboxPage,
          meta: { requiresAuth: true, resource: 'inbox', action: 'view' }
        },
        {
          path: 'directions',
          name: 'directions',
          component: CrudModulePage,
          props: { config: crudModules.directions },
          meta: { requiresAuth: true, resource: 'directions', action: 'view' }
        },
        {
          path: 'samples',
          name: 'samples',
          component: CrudModulePage,
          props: { config: crudModules.samples },
          meta: { requiresAuth: true, resource: 'samples', action: 'view' }
        },
        {
          path: 'protocols',
          name: 'protocols',
          component: CrudModulePage,
          props: { config: crudModules.protocols },
          meta: { requiresAuth: true, resource: 'protocols', action: 'view' }
        },
        {
          path: 'results',
          name: 'results',
          component: CrudModulePage,
          props: { config: crudModules.results },
          meta: { requiresAuth: true, resource: 'results', action: 'view' }
        },
        {
          path: 'conclusions',
          name: 'conclusions',
          component: CrudModulePage,
          props: { config: crudModules.conclusions },
          meta: { requiresAuth: true, resource: 'conclusions', action: 'view' }
        },
        {
          path: 'tests',
          name: 'tests',
          component: CrudModulePage,
          props: { config: crudModules.tests },
          meta: { requiresAuth: true, resource: 'tests', action: 'view' }
        },
        {
          path: 'doctors',
          name: 'doctors',
          component: CrudModulePage,
          props: { config: crudModules.doctors },
          meta: { requiresAuth: true, resource: 'doctors', action: 'view' }
        },
        {
          path: 'branches',
          name: 'branches',
          component: CrudModulePage,
          props: { config: crudModules.branches },
          meta: { requiresAuth: true, resource: 'branches', action: 'view' }
        },
        {
          path: 'labs',
          name: 'labs',
          component: CrudModulePage,
          props: { config: crudModules.labs },
          meta: { requiresAuth: true, resource: 'labs', action: 'view' }
        },
        {
          path: 'research-goals',
          name: 'research-goals',
          component: CrudModulePage,
          props: { config: crudModules['research-goals'] },
          meta: { requiresAuth: true, resource: 'research-goals', action: 'view' }
        },
        {
          path: 'sample-targets',
          name: 'sample-targets',
          component: CrudModulePage,
          props: { config: crudModules['sample-targets'] },
          meta: { requiresAuth: true, resource: 'sample-targets', action: 'view' }
        },
        {
          path: 'sample-types',
          name: 'sample-types',
          component: CrudModulePage,
          props: { config: crudModules['sample-types'] },
          meta: { requiresAuth: true, resource: 'sample-types', action: 'view' }
        },
        {
          path: 'indicators',
          name: 'indicators',
          component: CrudModulePage,
          props: { config: crudModules.indicators },
          meta: { requiresAuth: true, resource: 'indicators', action: 'view' }
        },
        {
          path: 'protocol-types',
          name: 'protocol-types',
          component: CrudModulePage,
          props: { config: crudModules['protocol-types'] },
          meta: { requiresAuth: true, resource: 'protocol-types', action: 'view' }
        },
        {
          path: 'statuses',
          name: 'statuses',
          component: CrudModulePage,
          props: { config: crudModules.statuses },
          meta: { requiresAuth: true, resource: 'statuses', action: 'view' }
        },
        {
          path: 'objects',
          name: 'objects',
          component: CrudModulePage,
          props: { config: crudModules.objects },
          meta: { requiresAuth: true, resource: 'objects', action: 'view' }
        },
        {
          path: 'users',
          name: 'users',
          component: UsersPage,
          meta: { requiresAuth: true, resource: 'users', action: 'view' }
        },
        {
          path: 'user-types',
          name: 'user-types',
          component: UserTypesPage,
          meta: { requiresAuth: true, resource: 'user-types', action: 'view' }
        },
        {
          path: 'settings',
          component: SettingsLayoutPage,
          children: [
            { path: '', name: 'settings', component: SettingsIndexPage, meta: { requiresAuth: true } },
            { path: 'members', name: 'settings-members', component: SettingsMembersPage, meta: { requiresAuth: true } },
            { path: 'notifications', name: 'settings-notifications', component: SettingsNotificationsPage, meta: { requiresAuth: true } },
            { path: 'security', name: 'settings-security', component: SettingsSecurityPage, meta: { requiresAuth: true } }
          ]
        }
      ]
    },
    {
      path: '/not-found',
      component: ErrorLayout,
      meta: { public: true },
      children: [
        {
          path: '',
          name: 'not-found',
          component: NotFoundPage,
          meta: { public: true }
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      component: ErrorLayout,
      meta: { public: true },
      children: [
        {
          path: '',
          component: NotFoundPage,
          meta: { public: true }
        }
      ]
    }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!auth.initialized) {
    await auth.restoreSession()
  }

  if (to.meta.public) {
    if (to.name === 'login' && auth.isAuthenticated) {
      return { name: 'dashboard' }
    }
    return true
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login' }
  }

  if (to.meta.resource && to.meta.action && !auth.can(String(to.meta.resource), String(to.meta.action))) {
    return { name: 'dashboard' }
  }

  return true
})
