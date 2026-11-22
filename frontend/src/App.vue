<!-- Copyright (c) 2026 Lumen Solutions. All rights reserved.
     SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
     Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions. -->
<template>
  <div class="min-h-screen">
    <header v-if="!embed" class="hd">
      <div class="mx-auto max-w-7xl px-6">
        <div class="row">
          <router-link to="/" class="brand">
            <img class="tile" :src="appIcon" alt="" width="36" height="36" />
            <span>
              <span v-if="lang === 'ar'" class="wm">لومن <b>تقارير</b></span>
              <span v-else class="wm">Lumen<b>Reports</b></span>
              <small>{{ t('ANALYTICS') }}</small>
            </span>
          </router-link>
          <span class="sp" style="flex: 1"></span>
          <router-link to="/ask" class="theme-btn" style="text-decoration: none; border-color: transparent; background: color-mix(in srgb, var(--blue) 10%, transparent); color: var(--blue)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3v2M12 19v2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M3 12h2M19 12h2M5.6 18.4 7 17M17 7l1.4-1.4" />
              <circle cx="12" cy="12" r="4" />
            </svg>
            {{ t('Ask AI') }}
          </router-link>
          <router-link
            v-if="brand.can_manage"
            to="/brand"
            class="theme-btn"
            :title="t('Visual identity')"
            style="text-decoration: none"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3a9 9 0 0 0 0 18c1.1 0 2-.9 2-2 0-.5-.2-1-.6-1.4-.3-.4-.4-.8-.4-1.1 0-.8.7-1.5 1.5-1.5H16a5 5 0 0 0 5-5c0-3.9-4-7-9-7Z" />
              <circle cx="7.6" cy="12.2" r="1.1" fill="currentColor" stroke="none" />
              <circle cx="9.6" cy="7.8" r="1.1" fill="currentColor" stroke="none" />
              <circle cx="14.4" cy="7.8" r="1.1" fill="currentColor" stroke="none" />
              <circle cx="17.2" cy="11" r="1.1" fill="currentColor" stroke="none" />
            </svg>
            {{ t('Identity') }}
          </router-link>
          <router-link
            v-if="isAuditor"
            to="/audit"
            class="theme-btn"
            :title="t('Audit trail')"
            style="text-decoration: none"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" />
              <path d="M14 3v5h5M9 13h4M9 17h6" />
            </svg>
            {{ t('Audit') }}
          </router-link>
          <!-- each language names itself, so the switch is findable from either side -->
          <button class="theme-btn" :title="lang === 'ar' ? 'English' : 'العربية'" @click="setLang(lang === 'ar' ? 'en' : 'ar')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="9" />
              <path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
            </svg>
            {{ lang === 'ar' ? 'English' : 'العربية' }}
          </button>
          <button class="theme-btn" @click="toggleTheme">
            <svg v-if="theme === 'light'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
            </svg>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
            </svg>
            {{ theme === 'light' ? t('Dark') : t('Light') }}
          </button>
        </div>
      </div>
    </header>
    <div v-if="licenseNotice" class="lic-bar">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16.5v.01" /></svg>
      <span>{{ licenseNotice }}</span>
    </div>
    <router-view />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { call } from 'frappe-ui'
import { theme, toggleTheme, applyTheme } from '@/lib/theme'
import { brand } from '@/lib/brand'
import { applyLang, lang, setLang, t } from '@/lib/i18n'

applyTheme()
applyLang()

// inside another app's page the host has its own header. The path check covers
// the first paint, before the router has resolved the route
const route = useRoute()
const embed = computed(() => Boolean(route.meta.embed) || window.location.pathname.startsWith('/lumen/embed/'))

// served by Frappe from the app's public folder, not bundled — bound rather than
// a literal src so Vite doesn't try to resolve it at build time
const appIcon = '/assets/lumen_reports/logo/svg/app-icon.svg'

// handed over at page load, like the identity, so the header does not have to ask
const isAuditor = computed(() => Boolean(window.lumen_auditor))

// unlicensed use should be visible rather than silent; a failure to check
// must never keep the app from loading
const licenseNotice = ref('')
async function loadNotice() {
  try {
    const result = await call('lumen_reports.licensing.get_license_notice', { lang: lang.value })
    licenseNotice.value = result?.notice || ''
  } catch (e) {
    licenseNotice.value = ''
  }
}
onMounted(loadNotice)
watch(lang, loadNotice)
</script>

<style scoped>
.lic-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 18px;
  background: var(--warning-bg);
  color: var(--warning);
  border-bottom: 1px solid color-mix(in srgb, var(--warning) 30%, transparent);
  font-size: 13px;
  font-weight: 600;
  text-align: center;
}
</style>
