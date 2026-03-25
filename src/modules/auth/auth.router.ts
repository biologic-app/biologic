import LoginPage from './pages/LoginPage.vue'
import ForbiddenPage from './pages/ForbiddenPage.vue'

import ErrorLayout from '@/shared/layouts/ErrorLayout.vue'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'

const authRouter = [
  {
    path: '/login',
    component: AuthLayout,
    meta: { public: true },
    children: [{ 
        path: '', 
        name: 'login', 
        component: LoginPage,
        meta: { public: true },
    }]
  },
  {
    path: '/forbidden',
    component: ErrorLayout,
    meta: { public: true },
    children: [{ 
        path: '', 
        name: 'forbidden', 
        component: ForbiddenPage,
        meta: { public: true },
    }]
  },
]
export { authRouter }