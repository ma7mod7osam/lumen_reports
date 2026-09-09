import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'DashboardList',
    component: () => import('@/pages/DashboardList.vue'),
  },
  {
    path: '/new',
    name: 'DashboardNew',
    component: () => import('@/pages/DashboardNew.vue'),
  },
  {
    path: '/new/blank',
    name: 'DashboardBlank',
    component: () => import('@/pages/DashboardBuilder.vue'),
  },
  {
    path: '/ask',
    name: 'AskAI',
    component: () => import('@/pages/AskAI.vue'),
  },
  {
    path: '/dashboard/:slug',
    name: 'DashboardView',
    component: () => import('@/pages/DashboardView.vue'),
    props: true,
  },
  {
    path: '/dashboard/:slug/edit',
    name: 'DashboardEdit',
    component: () => import('@/pages/DashboardBuilder.vue'),
    props: true,
  },
]

export default createRouter({
  history: createWebHistory('/lumen'),
  routes,
})
