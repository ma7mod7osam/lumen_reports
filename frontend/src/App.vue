<template>
  <div class="min-h-screen">
    <header class="hd">
      <div class="mx-auto max-w-7xl px-6">
        <div class="row">
          <router-link to="/" class="brand">
            <img class="tile" :src="appIcon" alt="" width="36" height="36" />
            <span>
              <span class="wm">Lumen<b>Reports</b></span>
              <small>ANALYTICS</small>
            </span>
          </router-link>
          <span class="sp" style="flex: 1"></span>
          <router-link to="/ask" class="theme-btn" style="text-decoration: none; border-color: transparent; background: color-mix(in srgb, var(--blue) 10%, transparent); color: var(--blue)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3v2M12 19v2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M3 12h2M19 12h2M5.6 18.4 7 17M17 7l1.4-1.4" />
              <circle cx="12" cy="12" r="4" />
            </svg>
            Ask AI
          </router-link>
          <button class="theme-btn" @click="toggleTheme">
            <svg v-if="theme === 'light'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
            </svg>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
            </svg>
            {{ theme === 'light' ? 'Dark' : 'Light' }}
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
import { onMounted, ref } from 'vue'
import { call } from 'frappe-ui'
import { theme, toggleTheme, applyTheme } from '@/lib/theme'

applyTheme()

// served by Frappe from the app's public folder, not bundled — bound rather than
// a literal src so Vite doesn't try to resolve it at build time
const appIcon = '/assets/lumen_reports/logo/svg/app-icon.svg'

// unlicensed use should be visible rather than silent; a failure to check
// must never keep the app from loading
const licenseNotice = ref('')
onMounted(async () => {
  try {
    const result = await call('lumen_reports.licensing.get_license_notice')
    licenseNotice.value = result?.notice || ''
  } catch (e) {
    licenseNotice.value = ''
  }
})
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
