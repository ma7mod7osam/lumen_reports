<template>
  <div class="min-h-screen">
    <header class="hd">
      <div class="mx-auto max-w-7xl px-6">
        <div class="row">
          <router-link to="/" class="brand">
            <span class="tile">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
                <rect x="2" y="3" width="2.4" height="12" rx="1" />
                <rect x="6" y="3" width="1.4" height="12" rx="0.7" opacity="0.85" />
                <rect x="9" y="3" width="2.4" height="12" rx="1" opacity="0.7" />
                <rect x="13" y="3" width="1.4" height="12" rx="0.7" opacity="0.5" />
              </svg>
            </span>
            <span>
              Lumen
              <small>REPORTS</small>
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
    <router-view />
  </div>
</template>

<script setup>
import { theme, toggleTheme, applyTheme } from '@/lib/theme'

applyTheme()
</script>
