<template>
  <div class="flex h-full flex-col">
    <div class="min-h-0 flex-1 overflow-auto">
      <table v-if="result" class="tbl">
        <thead>
          <tr>
            <th
              v-for="col in result.columns"
              :key="col.fieldname"
              :class="{ num: isNumeric(col) }"
              class="sticky top-0"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in result.rows" :key="row.name ?? i">
            <td
              v-for="col in result.columns"
              :key="col.fieldname"
              :class="{ num: isNumeric(col) }"
              class="max-w-64 truncate"
            >
              <span
                v-if="col.fieldtype === 'Select' && badgeFor(row[col.fieldname])"
                class="badge"
                :class="badgeFor(row[col.fieldname])"
              >
                <span class="dot"></span>{{ row[col.fieldname] }}
              </span>
              <template v-else>{{ formatCell(row[col.fieldname], col) }}</template>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="result && !result.rows.length" class="empty">
        <div class="ic">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M4 7h16M4 12h16M4 17h10" />
          </svg>
        </div>
        <div style="font-weight: 700; color: var(--ink)">No records</div>
        <div style="font-size: 12.5px">Nothing matches the current filters</div>
      </div>
    </div>
    <div
      v-if="result && result.rows.length"
      class="mono"
      style="border-top: 1px solid var(--border); padding-top: 9px; margin-top: 6px; text-align: right; font-size: 11px; color: var(--faint)"
    >
      {{ result.rows.length }} OF {{ formatNumber(result.total) }} ROWS
    </div>
  </div>
</template>

<script setup>
import { formatNumber } from '@/lib/palette'

defineProps({
  result: { type: Object, default: null },
})

const NUMERIC_TYPES = new Set(['Int', 'Float', 'Currency', 'Percent'])

const BADGE_MAP = {
  open: 'b-blue',
  closed: 'b-green',
  completed: 'b-green',
  paid: 'b-green',
  cancelled: 'b-gray',
  overdue: 'b-red',
  draft: 'b-gray',
  pending: 'b-amber',
  high: 'b-red',
  medium: 'b-amber',
  low: 'b-gray',
}

function badgeFor(value) {
  if (typeof value !== 'string') return null
  return BADGE_MAP[value.toLowerCase()] || null
}

function isNumeric(col) {
  return NUMERIC_TYPES.has(col.fieldtype)
}

function formatCell(value, col) {
  if (value === null || value === undefined || value === '') return '—'
  if (isNumeric(col)) return formatNumber(value)
  return String(value).replace(/<[^>]*>/g, '')
}
</script>
