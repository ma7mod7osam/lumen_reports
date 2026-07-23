import { ref } from 'vue'

const STORAGE_KEY = 'lumen-theme'

export const theme = ref(localStorage.getItem(STORAGE_KEY) || 'light')
// bumped on every toggle — chart components watch this and redraw so they
// pick up the new CSS variable values (charts read colors at draw time)
export const themeVersion = ref(0)

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
export function cssv(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export function chartPalette() {
  return ['--c1', '--c2', '--c3', '--c4', '--c5', '--c6', '--c7', '--c8'].map(cssv)
}
