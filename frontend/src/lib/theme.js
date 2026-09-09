import { ref } from 'vue'

const STORAGE_KEY = 'lumen-theme'

export const theme = ref(localStorage.getItem(STORAGE_KEY) || 'light')
// bumped on every toggle — chart components watch this and redraw so they
// pick up the new CSS variable values (charts read colors at draw time)
export const themeVersion = ref(0)

// The element a dashboard theme is painted on, registered by ThemeScope while
// a themed dashboard is on screen. Colors are read from here rather than from
// <html> so a dashboard with its own theme colors its own charts. One
// dashboard is on screen at a time, so a single scope is enough.
export const themeScope = ref(null)

export function applyTheme() {
  document.documentElement.setAttribute('data-theme', theme.value)
}

export function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem(STORAGE_KEY, theme.value)
  applyTheme()
  themeVersion.value += 1
}

/** Read a CSS custom property at call time (theme-aware). */
export function cssv(name, el) {
  const from = el || themeScope.value || document.documentElement
  return getComputedStyle(from).getPropertyValue(name).trim()
}

export function chartPalette(el) {
  return ['--c1', '--c2', '--c3', '--c4', '--c5', '--c6', '--c7', '--c8'].map((n) => cssv(n, el))
}
