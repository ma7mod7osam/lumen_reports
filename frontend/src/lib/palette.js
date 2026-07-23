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
