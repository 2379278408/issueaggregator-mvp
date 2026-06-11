import { createRouter, createWebHistory } from 'vue-router';
import AdminWorkbenchPage from '../pages/AdminWorkbenchPage.vue';
import UserHomePage from '../pages/UserHomePage.vue';
const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            name: 'user-home',
            component: UserHomePage,
        },
        {
            path: '/admin',
            name: 'admin-workbench',
            component: AdminWorkbenchPage,
        },
    ],
});
export default router;
