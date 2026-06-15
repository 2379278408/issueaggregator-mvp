import { createRouter, createWebHistory } from 'vue-router'

import AdminWorkbenchPage from '../pages/AdminWorkbenchPage.vue'
import UserHomePage from '../pages/UserHomePage.vue'

const adminRouteSlug = (import.meta.env.VITE_ADMIN_ROUTE_SLUG as string | undefined)?.trim() || 'adminconsole'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'user-home',
      component: UserHomePage,
    },
    {
      path: `/${adminRouteSlug}`,
      name: 'admin-workbench',
      component: AdminWorkbenchPage,
    },
  ],
})

export default router
