import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/shared/layouts/MainLayout.vue'
import ErrorLayout from '@/shared/layouts/ErrorLayout.vue'
import NotFoundPage from '@/shared/pages/NotFoundPage.vue'
import CustomersPage from '@/modules/customers/pages/CustomersPage.vue'
import DashboardPage from '@/modules/dashboard/pages/DashboardPage.vue'
import InboxPage from '@/modules/inbox/pages/InboxPage.vue'
import SettingsLayoutPage from '@/modules/settings/pages/SettingsLayoutPage.vue'
import SettingsIndexPage from '@/modules/settings/pages/SettingsIndexPage.vue'
import SettingsMembersPage from '@/modules/settings/pages/SettingsMembersPage.vue'
import SettingsNotificationsPage from '@/modules/settings/pages/SettingsNotificationsPage.vue'
import SettingsSecurityPage from '@/modules/settings/pages/SettingsSecurityPage.vue'
import { authRouter, useAuthStore } from '@/modules/auth'



export const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...authRouter,
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
          path: 'settings',
          component: SettingsLayoutPage,
          children: [
            {
              path: '',
              name: 'settings',
              component: SettingsIndexPage
            },
            {
              path: 'members',
              name: 'settings-members',
              component: SettingsMembersPage
            },
            {
              path: 'notifications',
              name: 'settings-notifications',
              component: SettingsNotificationsPage
            },
            {
              path: 'security',
              name: 'settings-security',
              component: SettingsSecurityPage
            }
          ]
        },
        {
          path: 'directions',
          name: 'directions',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'directions', action: 'view' }
        },
        {
          path: 'samples',
          name: 'samples',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'samples', action: 'view' }
        },
        {
          path: 'protocols',
          name: 'protocols',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'protocols', action: 'view' }
        },
        {
          path: 'results',
          name: 'results',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'results', action: 'view' }
        },
        {
          path: 'conclusions',
          name: 'conclusions',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'conclusions', action: 'view' }
        },
        {
          path: 'tests',
          name: 'tests',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'tests', action: 'view' }
        },
        {
          path: 'doctors',
          name: 'doctors',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'doctors', action: 'view' }
        },
        {
          path: 'branches',
          name: 'branches',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'branches', action: 'view' }
        },
        {
          path: 'labs',
          name: 'labs',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'labs', action: 'view' }
        },
        {
          path: 'research-goals',
          name: 'research-goals',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'research-goals', action: 'view' }
        },
        {
          path: 'sample-targets',
          name: 'sample-targets',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'sample-targets', action: 'view' }
        },
        {
          path: 'sample-types',
          name: 'sample-types',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'sample-types', action: 'view' }
        },
        {
          path: 'indicators',
          name: 'indicators',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'indicators', action: 'view' }
        },
        {
          path: 'protocol-types',
          name: 'protocol-types',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'protocol-types', action: 'view' }
        },
        {
          path: 'statuses',
          name: 'statuses',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'statuses', action: 'view' }
        },
        {
          path: 'user-types',
          name: 'user-types',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'user-types', action: 'view' }
        },
        {
          path: 'objects',
          name: 'objects',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'objects', action: 'view' }
        },
        {
          path: 'users',
          name: 'users',
          component: NotFoundPage,
          meta: { requiresAuth: true, resource: 'users', action: 'view' }
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
          meta: { public: true },
        }
      ]
    }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return '/login'
  }

  if (to.meta.permission && !auth.can(to.meta.permission)) {
    return '/403'
  }

  if (to.meta.role && auth.role !== to.meta.role) {
    return '/403'
  }
})
