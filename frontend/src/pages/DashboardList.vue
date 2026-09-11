<template>
  <div class="mx-auto max-w-7xl px-6 py-10">
    <div class="mb-8">
      <div class="mono eyebrow-line">
        <span class="bar"></span>
        {{ t('Dashboards') }}
      </div>
      <h1 style="font-size: 32px; font-weight: 800; letter-spacing: -0.03em; margin-top: 10px">
        {{ t('Lumen Reports') }}
      </h1>
      <div class="flex items-end justify-between gap-4">
        <p style="color: var(--muted); margin-top: 6px">{{ t('Fast, live, beautiful dashboards for Frappe') }}</p>
        <router-link v-if="dashboards.data?.can_create" to="/new" class="lbtn primary" style="text-decoration: none">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          {{ t('New dashboard') }}
        </router-link>
      </div>
    </div>

    <div v-if="dashboards.loading" class="grid grid-cols-1 gap-[18px] sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="i in 3" :key="i" class="skel" style="height: 128px; border-radius: 16px"></div>
    </div>

    <div v-else-if="dashboards.data?.dashboards?.length" class="grid grid-cols-1 gap-[18px] sm:grid-cols-2 lg:grid-cols-3">
      <router-link
        v-for="d in dashboards.data.dashboards"
        :key="d.name"
        :to="{ name: 'DashboardView', params: { slug: d.route_slug } }"
        class="panel block p-[18px] transition hover:-translate-y-0.5"
        style="text-decoration: none"
      >
        <div class="flex items-start justify-between">
          <h2 style="font-size: 16px; font-weight: 700; color: var(--ink)" dir="auto">{{ d.dashboard_title }}</h2>
          <span v-if="d.is_published" class="badge b-green"><span class="dot"></span>{{ t('Live') }}</span>
        </div>
        <p class="mt-1 line-clamp-2" style="font-size: 13.5px; color: var(--muted)" dir="auto">
          {{ d.description }}
        </p>
        <p class="mono mt-4 updated">
          {{ t('Updated {0}', timeAgo(d.modified)) }}
        </p>
      </router-link>
    </div>

    <div v-else class="empty panel">
      <div class="ic">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="3" y="3" width="7.5" height="7.5" rx="2" />
          <rect x="13.5" y="3" width="7.5" height="7.5" rx="2" />
          <rect x="3" y="13.5" width="7.5" height="7.5" rx="2" />
          <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2" />
        </svg>
      </div>
      <div style="font-weight: 700; color: var(--ink)">{{ t('No dashboards yet') }}</div>
      <div style="font-size: 12.5px">{{ t('Start from a template or a blank canvas with New dashboard') }}</div>
    </div>
  </div>
</template>

<script setup>
import { createResource } from 'frappe-ui'
import { t } from '@/lib/i18n'

const dashboards = createResource({
  url: 'lumen_reports.api.get_dashboards',
  auto: true,
})

function timeAgo(dateStr) {
  const seconds = (Date.now() - new Date(dateStr.replace(' ', 'T'))) / 1000
  if (seconds < 3600) return t('{0}m ago', Math.max(1, Math.floor(seconds / 60)))
  if (seconds < 86400) return t('{0}h ago', Math.floor(seconds / 3600))
  return t('{0}d ago', Math.floor(seconds / 86400))
}
</script>

<style scoped>
.eyebrow-line {
  font-size: 12.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--blue);
  display: inline-flex;
  align-items: center;
  gap: 9px;
}
.eyebrow-line .bar {
  width: 20px;
  height: 2px;
  background: var(--blue);
  display: inline-block;
}
.updated {
  font-size: 10.5px;
  color: var(--faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
</style>
