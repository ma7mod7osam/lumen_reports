/**
 * Per-dashboard theming.
 *
 * A theme is a small object saved on the dashboard. It resolves to a set of
 * CSS custom properties painted on the dashboard's own container, so two
 * dashboards on the same site can look nothing alike while the app chrome
 * around them stays consistent. Charts read their colors from the same
 * container (see lib/theme.js), so a preset recolors the data too.
 *
 * An empty theme means "follow the app", which is what every dashboard built
 * before theming had, and what a new one starts with.
 */

export const DEFAULT_THEME = {
  preset: '',
  brand: '',
  card: '',
  radius: null,
  density: '',
  font: '',
  surface: '',
}

export const FONTS = [
  { id: '', label: 'Plus Jakarta Sans', stack: "'Plus Jakarta Sans', -apple-system, 'Segoe UI', sans-serif" },
  { id: 'system', label: 'System UI', stack: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" },
  { id: 'serif', label: 'Serif', stack: "Georgia, 'Times New Roman', serif" },
  { id: 'mono', label: 'Monospace', stack: "'IBM Plex Mono', ui-monospace, Menlo, monospace" },
]

export const CARD_STYLES = [
  { id: 'flat', label: 'Flat' },
  { id: 'outlined', label: 'Outlined' },
  { id: 'elevated', label: 'Elevated' },
  { id: 'glass', label: 'Glass' },
]

export const DENSITIES = [
  { id: 'compact', label: 'Compact' },
  { id: 'comfort', label: 'Comfort' },
]

export const SURFACES = [
  { id: 'solid', label: 'Solid' },
  { id: 'gradient', label: 'Gradient' },
  { id: 'tint', label: 'Brand tint' },
]

/**
 * Each preset is a complete look: page, cards, text, lines and the eight
 * categorical chart colors. They are written out rather than derived so a
 * preset can be judged by eye instead of by formula.
 */
export const THEME_PRESETS = [
  {
    id: 'light',
    name: 'Lumen Light',
    base: 'light',
    card: 'outlined',
    vars: {
      '--bg': '#f4f6fa',
      '--panel': '#ffffff',
      '--panel-2': '#f0f3f8',
      '--panel-3': '#e9edf4',
      '--border': '#e4e8f0',
      '--border-2': '#d4dae5',
      '--ink': '#0c1322',
      '--ink-2': '#3a4456',
      '--muted': '#687386',
      '--faint': '#98a1b2',
      '--grid-line': '#eaeef4',
      '--baseline': '#ccd3e0',
      '--chip': '#f0f3f8',
      '--shadow': '0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.05)',
      '--shadow-md': '0 8px 24px rgba(16,24,40,0.08), 0 2px 6px rgba(16,24,40,0.04)',
      '--blue': '#1463ff',
      '--c1': '#1463ff',
      '--c2': '#0f9d7a',
      '--c3': '#9b5bff',
      '--c4': '#e0772c',
      '--c5': '#d6447f',
      '--c6': '#1f9bb3',
      '--c7': '#c9a21b',
      '--c8': '#5e6ad2',
      '--success': '#0f9d7a',
      '--success-bg': '#e2f6ef',
      '--warning': '#c9821b',
      '--warning-bg': '#fbf0dc',
      '--danger': '#e0413f',
      '--danger-bg': '#fce6e5',
    },
  },
  {
    id: 'dark',
    name: 'Lumen Dark',
    base: 'dark',
    card: 'flat',
    vars: {
      '--bg': '#07090f',
      '--panel': '#121826',
      '--panel-2': '#0c1018',
      '--panel-3': '#1a2233',
      '--border': '#1d2432',
      '--border-2': '#2a3346',
      '--ink': '#f2f5fa',
      '--ink-2': '#b9c2d4',
      '--muted': '#7e8aa1',
      '--faint': '#525d72',
      '--grid-line': '#1a2130',
      '--baseline': '#2c3546',
      '--chip': '#1a2233',
      '--shadow': 'none',
      '--shadow-md': '0 10px 30px rgba(0,0,0,0.45)',
      '--blue': '#3b82ff',
      '--c1': '#3b82ff',
      '--c2': '#2bc79b',
      '--c3': '#b08cff',
      '--c4': '#f0904e',
      '--c5': '#f0699f',
      '--c6': '#3fc1db',
      '--c7': '#e0ba3c',
      '--c8': '#8a96ee',
      '--success': '#2bc79b',
      '--success-bg': '#0f2a24',
      '--warning': '#e0a53c',
      '--warning-bg': '#2c2412',
      '--danger': '#ff6b66',
      '--danger-bg': '#321a1a',
    },
  },
  {
    id: 'emerald',
    name: 'Emerald',
    base: 'dark',
    card: 'elevated',
    vars: {
      '--bg': '#071310',
      '--panel': '#0d211a',
      '--panel-2': '#0a1a15',
      '--panel-3': '#143728',
      '--border': '#143728',
      '--border-2': '#1d4a37',
      '--ink': '#eefaf5',
      '--ink-2': '#bfe0d4',
      '--muted': '#6d9c8c',
      '--faint': '#4d7767',
      '--grid-line': '#122c22',
      '--baseline': '#1d4a37',
      '--chip': '#143728',
      '--shadow': 'none',
      '--shadow-md': '0 10px 26px rgba(0,0,0,0.42)',
      '--blue': '#2bc79b',
      '--c1': '#2bc79b',
      '--c2': '#3fc1db',
      '--c3': '#9be36d',
      '--c4': '#f0c04e',
      '--c5': '#ff8f6b',
      '--c6': '#7ad0ff',
      '--c7': '#c9a7ff',
      '--c8': '#59a687',
      '--success': '#2bc79b',
      '--success-bg': '#0f2a24',
      '--warning': '#e0a53c',
      '--warning-bg': '#2b2612',
      '--danger': '#ff6b66',
      '--danger-bg': '#321c1c',
    },
  },
  {
    id: 'midnight',
    name: 'Midnight',
    base: 'dark',
    card: 'elevated',
    vars: {
      '--bg': '#0a0d1c',
      '--panel': '#141a33',
      '--panel-2': '#10152a',
      '--panel-3': '#1e2647',
      '--border': '#232c4f',
      '--border-2': '#303a63',
      '--ink': '#eef1ff',
      '--ink-2': '#c0c7e8',
      '--muted': '#8089b5',
      '--faint': '#5a6294',
      '--grid-line': '#1c2444',
      '--baseline': '#303a63',
      '--chip': '#1e2647',
      '--shadow': 'none',
      '--shadow-md': '0 14px 34px rgba(0,0,0,0.5)',
      '--blue': '#6c8cff',
      '--c1': '#6c8cff',
      '--c2': '#4fd1c5',
      '--c3': '#b98cff',
      '--c4': '#ffa25c',
      '--c5': '#ff7ab0',
      '--c6': '#56c8f0',
      '--c7': '#ffd166',
      '--c8': '#8f9bff',
      '--success': '#3ddc97',
      '--success-bg': '#0f2b23',
      '--warning': '#ffc45c',
      '--warning-bg': '#2e2614',
      '--danger': '#ff6b7f',
      '--danger-bg': '#321a22',
    },
  },
  {
    id: 'sand',
    name: 'Sand',
    base: 'light',
    card: 'outlined',
    vars: {
      '--bg': '#faf6ef',
      '--panel': '#ffffff',
      '--panel-2': '#f5efe4',
      '--panel-3': '#ece4d4',
      '--border': '#ece4d4',
      '--border-2': '#ddd2bc',
      '--ink': '#2a2318',
      '--ink-2': '#574b38',
      '--muted': '#857757',
      '--faint': '#a99b7d',
      '--grid-line': '#f0e9dc',
      '--baseline': '#ddd2bc',
      '--chip': '#f5efe4',
      '--shadow': '0 1px 2px rgba(90,70,30,0.07)',
      '--shadow-md': '0 8px 22px rgba(90,70,30,0.10)',
      '--blue': '#b4813c',
      '--c1': '#b4813c',
      '--c2': '#6f8f4f',
      '--c3': '#a3564a',
      '--c4': '#4a7d8c',
      '--c5': '#8a6ba3',
      '--c6': '#c9a227',
      '--c7': '#77694f',
      '--c8': '#3f6b57',
      '--success': '#5a8a4a',
      '--success-bg': '#eaf1e2',
      '--warning': '#c9821b',
      '--warning-bg': '#faeed7',
      '--danger': '#b5453f',
      '--danger-bg': '#f8e5e3',
    },
  },
  {
    id: 'paper',
    name: 'Paper',
    base: 'light',
    card: 'flat',
    vars: {
      '--bg': '#ffffff',
      '--panel': '#ffffff',
      '--panel-2': '#f6f6f4',
      '--panel-3': '#ecece8',
      '--border': '#e2e2dd',
      '--border-2': '#cfcfc8',
      '--ink': '#14140f',
      '--ink-2': '#3c3c34',
      '--muted': '#6b6b60',
      '--faint': '#97978a',
      '--grid-line': '#eeeee9',
      '--baseline': '#cfcfc8',
      '--chip': '#f2f2ee',
      '--shadow': 'none',
      '--shadow-md': '0 2px 0 #ecece8',
      '--blue': '#b3382c',
      '--c1': '#1f2937',
      '--c2': '#b3382c',
      '--c3': '#6b7280',
      '--c4': '#b98900',
      '--c5': '#2f6f4f',
      '--c6': '#3b5b8c',
      '--c7': '#8c5a3b',
      '--c8': '#9aa1ab',
      '--success': '#2f6f4f',
      '--success-bg': '#e8f0eb',
      '--warning': '#b98900',
      '--warning-bg': '#f7efd9',
      '--danger': '#b3382c',
      '--danger-bg': '#f7e6e4',
    },
  },
]

export function findPreset(id) {
  return THEME_PRESETS.find((p) => p.id === id) || null
}

/** True when the theme leaves everything to the app defaults. */
export function isDefaultTheme(theme) {
  if (!theme) return true
  return !Object.keys(DEFAULT_THEME).some((k) => {
    const v = theme[k]
    return v !== null && v !== undefined && v !== ''
  })
}

const CARD_VARS = {
  flat: {
    '--panel-border-color': 'transparent',
    '--panel-shadow': 'none',
  },
  outlined: {
    '--panel-border-color': 'var(--border)',
    '--panel-shadow': 'none',
  },
  elevated: {
    '--panel-border-color': 'transparent',
    '--panel-shadow': 'var(--shadow-md)',
  },
  glass: {
    '--panel-border-color': 'color-mix(in srgb, var(--ink) 12%, transparent)',
    '--panel-shadow': 'var(--shadow-md)',
    '--panel-blur': 'saturate(170%) blur(14px)',
  },
}

const DENSITY_VARS = {
  compact: { '--panel-pad': '13px', '--grid-gap': '12px' },
  comfort: { '--panel-pad': '18px', '--grid-gap': '18px' },
}

/**
 * Resolve a saved theme into the CSS custom properties to paint on the
 * dashboard container. Anything the theme does not set is simply absent, so
 * the app's own tokens show through.
 */
export function themeVars(theme) {
  const t = { ...DEFAULT_THEME, ...(theme || {}) }
  const preset = findPreset(t.preset)
  const vars = { ...(preset?.vars || {}) }

  // a brand color leads the palette and every accent the app derives from it
  if (t.brand) {
    vars['--blue'] = t.brand
    vars['--blue-600'] = `color-mix(in srgb, ${t.brand} 84%, #000)`
    vars['--blue-deep'] = `color-mix(in srgb, ${t.brand} 68%, #000)`
    vars['--blue-300'] = `color-mix(in srgb, ${t.brand} 55%, #fff)`
    vars['--c1'] = t.brand
  }

  const card = t.card || preset?.card
  if (card && CARD_VARS[card]) Object.assign(vars, CARD_VARS[card])

  // glass only reads as glass over something: the panel goes translucent so
  // the page beneath shows through the blur
  if (card === 'glass') {
    const panel = vars['--panel'] || (preset?.base === 'dark' ? '#121826' : '#ffffff')
    vars['--panel'] = `color-mix(in srgb, ${panel} 62%, transparent)`
  }

  if (t.density && DENSITY_VARS[t.density]) Object.assign(vars, DENSITY_VARS[t.density])
  if (t.radius !== null && t.radius !== undefined && t.radius !== '') {
    vars['--panel-radius'] = `${Number(t.radius)}px`
  }

  const font = FONTS.find((f) => f.id === t.font)
  if (font && font.id) vars['--font'] = font.stack

  // the page behind the cards. Kept separate from --bg, which has to stay a
  // plain color because charts read it for tooltip text
  const bg = vars['--bg']
  if (t.surface === 'gradient' && bg) {
    const accent = vars['--blue'] || '#1463ff'
    vars['--canvas-bg'] = `linear-gradient(160deg, color-mix(in srgb, ${accent} 9%, ${bg}), ${bg} 55%)`
  } else if (t.surface === 'tint' && bg) {
    const accent = vars['--blue'] || '#1463ff'
    vars['--canvas-bg'] = `color-mix(in srgb, ${accent} 6%, ${bg})`
  }

  return vars
}

/** The three-band strip shown on a preset card. */
export function presetSwatch(preset) {
  return [preset.vars['--bg'], preset.vars['--blue'], preset.vars['--panel']]
}
