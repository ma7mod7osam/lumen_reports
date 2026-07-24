// Number formatting helpers. Chart colors live in theme.js (read from CSS
// variables at draw time so they follow the light/dark theme).

const compactFormatter = new Intl.NumberFormat('en', {
  notation: 'compact',
  maximumFractionDigits: 1,
})
const fullFormatter = new Intl.NumberFormat('en', { maximumFractionDigits: 2 })

export function formatNumber(value, { compact = false } = {}) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return (compact ? compactFormatter : fullFormatter).format(Number(value))
}

/** Render a computed-metric value per its server-declared format
 * (clock = time of day, hours/minutes/days = durations, percent = ratio). */
export function formatValue(value, format, opts = {}) {
  const n = Number(value)
  if (value === null || value === undefined || Number.isNaN(n)) return '—'
  switch (format) {
    case 'clock': {
      const h = Math.floor(((n % 24) + 24) % 24)
      const m = Math.round((n - Math.floor(n)) * 60)
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
    }
    case 'hours': {
      const h = Math.floor(n)
      const m = Math.round((n - h) * 60)
      return m ? `${h}h ${m}m` : `${h}h`
    }
    case 'minutes':
      return `${Math.round(n)} min`
    case 'days':
      return `${fullFormatter.format(Math.round(n * 10) / 10)} days`
    case 'percent':
      return `${fullFormatter.format(Math.round(n * 1000) / 10)}%`
    default:
      return formatNumber(value, opts)
  }
}
