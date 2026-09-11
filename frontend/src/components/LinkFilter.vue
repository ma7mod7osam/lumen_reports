<template>
  <div ref="root" class="field" style="cursor: text; position: relative" @click="open">
    <span class="cue">{{ filter.label }}</span>
    <input
      ref="input"
      :value="display"
      dir="auto"
      :placeholder="t('All')"
      style="border: none; background: transparent; outline: none; font-family: var(--font); font-size: 13.5px; font-weight: 600; color: var(--ink); width: 110px; min-width: 0"
      @input="onType"
      @focus="open"
    />
    <button v-if="value" class="lf-clear" @click.stop="choose('')" :title="t('Clear')">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
    </button>
    <span v-else class="chev">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="m6 9 6 6 6-6" /></svg>
    </span>

    <div v-if="isOpen" class="lf-menu">
      <div v-if="loading" class="lf-empty">{{ t('Searching…') }}</div>
      <template v-else>
        <button
          v-for="opt in options"
          :key="opt.value"
          class="lf-opt"
          :class="{ on: opt.value === value }"
          @click.stop="choose(opt.value)"
        >
          {{ opt.label }}
        </button>
        <div v-if="!options.length" class="lf-empty">{{ t('No matches') }}</div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { call } from 'frappe-ui'
import { t } from '@/lib/i18n'

const props = defineProps({
  filter: { type: Object, required: true },
  value: { type: [String, Number], default: '' },
})
const emit = defineEmits(['update'])

const root = ref(null)
const input = ref(null)
const isOpen = ref(false)
const loading = ref(false)
const options = ref([])
const typed = ref('')
const labelCache = ref({})

const display = computed(() => {
  if (isOpen.value) return typed.value
  if (!props.value) return ''
  return labelCache.value[props.value] || props.value
})

let seq = 0
async function search(txt) {
  const mySeq = ++seq
  loading.value = true
  try {
    const rows = await call('lumen_reports.api.get_link_options', {
      link_doctype: props.filter.link_doctype,
      txt: txt || '',
    })
    if (mySeq === seq) {
      options.value = rows
      for (const r of rows) labelCache.value[r.value] = r.label
    }
  } catch {
    if (mySeq === seq) options.value = []
  } finally {
    if (mySeq === seq) loading.value = false
  }
}

let debounce
function onType(e) {
  typed.value = e.target.value
  isOpen.value = true
  clearTimeout(debounce)
  debounce = setTimeout(() => search(typed.value), 250)
}

function open() {
  if (isOpen.value) return
  isOpen.value = true
  typed.value = ''
  search('')
}

function choose(v) {
  emit('update', v)
  isOpen.value = false
  typed.value = ''
}

function onClickOutside(e) {
  if (root.value && !root.value.contains(e.target)) {
    isOpen.value = false
    typed.value = ''
  }
}

// resolve the label for a preset value so the chip shows a name, not an ID
watch(
  () => props.value,
  (v) => {
    if (v && !labelCache.value[v]) search('')
  },
  { immediate: true }
)

onMounted(() => document.addEventListener('click', onClickOutside))
onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
  clearTimeout(debounce)
})
</script>

<style scoped>
.lf-clear {
  border: none;
  background: transparent;
  color: var(--faint);
  cursor: pointer;
  display: flex;
  padding: 2px;
}
.lf-clear:hover {
  color: var(--danger);
}
.lf-menu {
  position: absolute;
  top: calc(100% + 6px);
  inset-inline-start: 0;
  min-width: 200px;
  max-height: 260px;
  overflow-y: auto;
  background: var(--panel);
  border: 1px solid var(--border-2);
  border-radius: 10px;
  box-shadow: var(--shadow-md);
  z-index: 40;
  padding: 5px;
}
.lf-opt {
  display: block;
  width: 100%;
  text-align: start;
  border: none;
  background: transparent;
  padding: 7px 10px;
  border-radius: 7px;
  font-family: var(--font);
  font-size: 13px;
  color: var(--ink-2);
  cursor: pointer;
}
.lf-opt:hover {
  background: var(--panel-2);
  color: var(--ink);
}
.lf-opt.on {
  background: color-mix(in srgb, var(--blue) 12%, transparent);
  color: var(--blue);
  font-weight: 600;
}
.lf-empty {
  padding: 10px;
  font-size: 12.5px;
  color: var(--faint);
  text-align: center;
}
</style>
