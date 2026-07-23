<template>
  <div class="kpi" style="padding: 0; height: 100%">
    <div class="top">
      <div class="ic" :class="tintClass">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
          <path d="m4 16 5-5 4 4 8-8" />
          <path d="M16 7h4v4" />
        </svg>
      </div>
    </div>
    <div>
      <div class="val tnum">{{ display }}</div>
      <div class="lbl">{{ label }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatNumber } from '@/lib/palette'

const props = defineProps({
  result: { type: Object, default: null },
  label: { type: String, default: '' },
  tint: { type: String, default: 'blue' },
})

const tintClass = computed(() => `tint-${props.tint || 'blue'}`)

const display = computed(() => {
  if (!props.result) return '—'
  const compact = Number(props.result.value) >= 100000
  return formatNumber(props.result.value, { compact })
})
</script>
