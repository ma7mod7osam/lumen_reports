// Copyright (c) 2026 Lumen Solutions. All rights reserved.
// SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
// Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
/**
 * Date range filter values. A value is always a pair of local calendar dates,
 * ['YYYY-MM-DD', 'YYYY-MM-DD'], which the server turns into a `between` filter.
 * Presets are resolved to dates on this device at the moment they are picked,
 * so "Today" means the viewer's today, not the server's.
 */

const pad = (n) => String(n).padStart(2, '0')

export function ymd(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function addDays(date, days) {
  const copy = new Date(date)
  copy.setDate(copy.getDate() + days)
  return copy
}

// no "this week": where a week starts differs by country, and a filter that
// silently picks one would be wrong for half the people using it
export const DATE_PRESETS = [
  { key: 'today', label: 'Today' },
  { key: 'yesterday', label: 'Yesterday' },
  { key: 'last_7_days', label: 'Last 7 days' },
  { key: 'this_month', label: 'This month' },
  { key: 'last_month', label: 'Last month' },
  { key: 'last_30_days', label: 'Last 30 days' },
  { key: 'this_year', label: 'This year' },
]

export function presetRange(key, now = new Date()) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const y = today.getFullYear()
  const m = today.getMonth()
  switch (key) {
    case 'today':
      return [ymd(today), ymd(today)]
    case 'yesterday': {
      const day = addDays(today, -1)
      return [ymd(day), ymd(day)]
    }
    case 'last_7_days':
      return [ymd(addDays(today, -6)), ymd(today)]
    case 'last_30_days':
      return [ymd(addDays(today, -29)), ymd(today)]
    case 'this_month':
      return [ymd(new Date(y, m, 1)), ymd(today)]
    case 'last_month':
      return [ymd(new Date(y, m - 1, 1)), ymd(new Date(y, m, 0))]
    case 'this_year':
      return [ymd(new Date(y, 0, 1)), ymd(today)]
    default:
      return null
  }
}

/** The preset a stored pair corresponds to today, or '' for a custom range. */
export function matchPreset(range) {
  if (!Array.isArray(range) || range.length !== 2) return ''
  const hit = DATE_PRESETS.find((p) => {
    const r = presetRange(p.key)
    return r && r[0] === range[0] && r[1] === range[1]
  })
  return hit ? hit.key : ''
}

/** Starting values for a dashboard's filters, from each definition's default. */
export function defaultFilterValues(filters) {
  const values = {}
  for (const f of filters || []) {
    if (f.fieldtype === 'Date Range' && f.default) {
      const range = presetRange(f.default)
      if (range) values[f.name] = range
    }
  }
  return values
}
