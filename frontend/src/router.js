// Copyright (c) 2026 Lumen Solutions. All rights reserved.
// SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
// Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
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
  {
    path: '/dashboard/:slug/report',
    name: 'DashboardReport',
    component: () => import('@/pages/DashboardReport.vue'),
    props: true,
  },
  {
    // for another app's page, such as LumenPOS Insights: the dashboard without
    // the app's header, navigation or edit controls
    path: '/embed/:slug',
    name: 'DashboardEmbed',
    component: () => import('@/pages/DashboardView.vue'),
    props: (route) => ({ slug: route.params.slug, embed: true }),
    meta: { embed: true },
  },
]

export default createRouter({
  history: createWebHistory('/lumen'),
  routes,
})
