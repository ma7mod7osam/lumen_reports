<template>
  <div class="fbar">
    <template v-for="filter in filters" :key="filter.name">
      <!-- Link: searchable value picker -->
      <LinkFilter
        v-if="filter.fieldtype === 'Link'"
        :filter="filter"
        :value="modelValue[filter.name] ?? ''"
        @update="(v) => update(filter.name, v)"
      />
      <!-- Select / Check: native dropdown -->
      <label v-else class="field">
        <span class="cue">{{ filter.label }}</span>
        <select
          :value="modelValue[filter.name] ?? ''"
          @change="(e) => update(filter.name, e.target.value)"
        >
          <option value="">All</option>
          <option v-for="opt in optionsFor(filter)" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <span class="chev">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </span>
      </label>
    </template>

    <button v-if="hasActiveFilters" class="chip on" @click="$emit('update:modelValue', {})">
      Clear all
      <span class="x">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round">
          <path d="M6 6l12 12M18 6 6 18" />
        </svg>
      </span>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import LinkFilter from '@/components/LinkFilter.vue'

const props = defineProps({
  filters: { type: Array, required: true },
  modelValue: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue'])

const hasActiveFilters = computed(() =>
  Object.values(props.modelValue).some((v) => v !== null && v !== '')
)

function optionsFor(filter) {
  if (filter.fieldtype === 'Check') {
    return [
      { label: 'Yes', value: '1' },
      { label: 'No', value: '0' },
    ]
  }
  return (filter.options || []).map((o) => (typeof o === 'string' ? { label: o, value: o } : o))
}

function update(name, value) {
  const next = { ...props.modelValue }
  if (value === '' || value === null) delete next[name]
  else next[name] = value
  emit('update:modelValue', next)
}
</script>
