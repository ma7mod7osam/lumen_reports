<!-- Copyright (c) 2026 Lumen Solutions. All rights reserved.
     SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
     Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions. -->
<template>
  <span class="drf">
    <label class="field">
      <span class="cue">{{ t(filter.label) }}</span>
      <select :value="preset" @change="(e) => pickPreset(e.target.value)">
        <option value="">{{ t('All dates') }}</option>
        <option v-for="p in DATE_PRESETS" :key="p.key" :value="p.key">{{ t(p.label) }}</option>
        <option value="custom">{{ t('Custom range') }}</option>
      </select>
      <span class="chev">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </span>
    </label>
    <span v-if="preset === 'custom'" class="custom">
      <input
        type="date"
        :value="draft[0]"
        :aria-label="t('From')"
        @change="(e) => pickDate(0, e.target.value)"
      />
      <span class="sep">{{ t('to') }}</span>
      <input
        type="date"
        :value="draft[1]"
        :aria-label="t('To')"
        @change="(e) => pickDate(1, e.target.value)"
      />
    </span>
  </span>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { DATE_PRESETS, matchPreset, presetRange } from '@/lib/dateRanges'
import { t } from '@/lib/i18n'

const props = defineProps({
  filter: { type: Object, required: true },
  value: { type: [Array, String], default: null },
})
const emit = defineEmits(['update'])

const isPair = (v) => Array.isArray(v) && v.length === 2
const customOpen = ref(false)
// dates typed so far; a range is only sent once both ends are set
const draft = ref(isPair(props.value) ? [...props.value] : ['', ''])
watch(
  () => props.value,
  (v) => {
    draft.value = isPair(v) ? [...v] : ['', '']
    if (!isPair(v) && !customOpen.value) draft.value = ['', '']
  }
)

const preset = computed(() => {
  if (customOpen.value) return 'custom'
  if (!isPair(props.value)) return ''
  return matchPreset(props.value) || 'custom'
})

function pickPreset(key) {
  if (key === 'custom') {
    customOpen.value = true
    return
  }
  customOpen.value = false
  emit('update', key ? presetRange(key) : '')
}

function pickDate(index, date) {
  const next = [...draft.value]
  next[index] = date
  draft.value = next
  if (next[0] && next[1]) {
    // a range typed backwards still means the days between the two dates
    emit('update', next[0] <= next[1] ? next : [next[1], next[0]])
  }
}
</script>

<style scoped>
.drf {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.custom {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.custom input {
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--panel);
  color: var(--ink);
  font: inherit;
  font-size: 13px;
}
.sep {
  font-size: 12px;
  color: var(--muted);
}
</style>
