<template>
  <!-- stays one row: only the forms that suit this data, plus a colour swatch
       that expands in place (a popover would clip inside scrolling grids) -->
  <div class="vbar" @click.stop>
    <template v-if="mode === 'color'">
      <button class="vt" title="Back" @click="mode = 'type'">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m14 6-6 6 6 6" /></svg>
      </button>
      <button
        v-for="(c, i) in swatches"
        :key="i"
        class="vc"
        :class="{ on: activeSwatch === i }"
        :style="{ background: c }"
        :title="swatchTitle(i)"
        @click="pickSwatch(i)"
      ></button>
    </template>

    <template v-else>
      <button
        v-for="t in choices"
        :key="t.value"
        class="vt"
        :class="{ on: widget.widget_type === t.value }"
        :title="t.label"
        @click="widget.widget_type = t.value"
      >
        <ChartIcon :type="t.value" />
      </button>
      <button v-if="swatches.length" class="vsw" title="Change colour" @click="mode = 'color'">
        <span class="sw" :style="{ background: swatches[activeSwatch] || swatches[0] }"></span>
        <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6" /></svg>
      </button>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch, watchEffect } from 'vue'
import { chartPalette, themeVersion } from '@/lib/theme'
import ChartIcon from '@/components/widgets/ChartIcon.vue'

const props = defineProps({
  widget: { type: Object, required: true }, // mutated in place: widget_type / style
  result: { type: Object, default: null }, // used to judge shape + category count
  defaultTint: { type: String, default: 'blue' },
})

const mode = ref('type')
watch(() => props.widget.widget_type, () => (mode.value = 'type'))

const TYPES = [
  { value: 'Bar Chart', label: 'Bar' },
  { value: 'Horizontal Bar', label: 'Ranked bars' },
  { value: 'Line Chart', label: 'Line' },
  { value: 'Area Chart', label: 'Area' },
  { value: 'Sparkline', label: 'Sparkline' },
  { value: 'Waterfall', label: 'Waterfall' },
  { value: 'Donut Chart', label: 'Donut' },
  { value: 'Pie Chart', label: 'Pie' },
  { value: 'Rings', label: 'Radial rings' },
  { value: 'Radar', label: 'Radar' },
  { value: 'Funnel', label: 'Funnel' },
]
const MATRIX_TYPES = [
  { value: 'Bar Chart', label: 'Grouped bars' },
  { value: 'Stacked Bar', label: 'Stacked bars' },
  { value: 'Line Chart', label: 'One line per series' },
  { value: 'Area Chart', label: 'Stacked area' },
  { value: 'Heatmap', label: 'Heatmap' },
  { value: 'Radar', label: 'Radar — one web per column' },
]
const TINTS = [
  { name: 'blue', color: '#1463FF' },
  { name: 'green', color: '#0F9D7A' },
  { name: 'amber', color: '#C9821B' },
  { name: 'violet', color: '#6D4AFF' },
]
// charts drawn in one colour let the user pick it; categorical charts use the
// whole palette in order, so there is nothing to choose
const ACCENT_TYPES = [
  'Bar Chart',
  'Horizontal Bar',
  'Line Chart',
  'Area Chart',
  'Sparkline',
  'Waterfall',
  'Radar',
  'Scatter',
  'Gauge',
  'Heatmap',
]

const SERIES_TYPES = new Set(TYPES.map((t) => t.value))
const shape = computed(() => props.result?.result_type || 'series')
const isSeriesShape = computed(() => shape.value === 'series')
const isMatrix = computed(() => shape.value === 'matrix')
const seriesType = computed(() => SERIES_TYPES.has(props.widget.widget_type))
const isTint = computed(() => props.widget.widget_type === 'Number Card')
const palette = computed(() => (themeVersion.value, chartPalette()))

// ---- form follows the data: which chart types actually suit this series ----
const rules = computed(() => {
  const grain = props.widget.query?.group_by?.time_grain
  const n = props.result?.labels?.length ?? 0
  if (grain === 'hour' || grain === 'weekday') {
    // 7 weekdays make a readable web; 24 hours do not
    const allowed = ['Bar Chart', 'Line Chart', 'Area Chart']
    if (grain === 'weekday') allowed.push('Radar')
    return { allowed, preferred: 'Bar Chart' }
  }
  if (grain) {
    return {
      allowed: ['Line Chart', 'Area Chart', 'Bar Chart', 'Sparkline', 'Waterfall'],
      preferred: 'Line Chart',
    }
  }
  if (n > 8) return { allowed: ['Bar Chart', 'Horizontal Bar'], preferred: 'Horizontal Bar' }
  return {
    allowed: [
      'Bar Chart',
      'Horizontal Bar',
      'Donut Chart',
      'Pie Chart',
      'Funnel',
      'Rings',
      'Radar',
      'Waterfall',
    ],
    preferred: 'Bar Chart',
  }
})

const matrixRules = computed(() => {
  // rows are the x axis / radar spokes, columns are the series / radar webs
  const rows = props.result?.rows?.length ?? 0
  const series = props.result?.cols?.length ?? 0
  const allowed = ['Heatmap']
  // a legend stops being readable past a handful of series
  if (series <= 6) allowed.unshift('Bar Chart', 'Stacked Bar', 'Line Chart', 'Area Chart')
  if (series <= 4 && rows >= 3 && rows <= 10) allowed.push('Radar')
  return { allowed }
})

// only offer real choices — a row of greyed-out icons is noise, and the wizard
// still lists every type for deliberate building
const choices = computed(() => {
  if (isSeriesShape.value && seriesType.value) {
    const list = TYPES.filter((t) => rules.value.allowed.includes(t.value))
    return list.length > 1 ? list : []
  }
  if (isMatrix.value) {
    const list = MATRIX_TYPES.filter((t) => matrixRules.value.allowed.includes(t.value))
    return list.length > 1 ? list : []
  }
  return []
})

const swatches = computed(() => {
  if (isTint.value) return TINTS.map((t) => t.color)
  return ACCENT_TYPES.includes(props.widget.widget_type) ? palette.value : []
})
const activeSwatch = computed(() =>
  isTint.value
    ? Math.max(
        0,
        TINTS.findIndex((t) => t.name === (props.widget.style?.tint || props.defaultTint))
      )
    : props.widget.style?.accent || 0
)

function swatchTitle(i) {
  return isTint.value ? TINTS[i].name : `Colour ${i + 1}`
}
function pickSwatch(i) {
  const style = { ...(props.widget.style || {}) }
  if (isTint.value) style.tint = TINTS[i].name
  else style.accent = i
  props.widget.style = style
  mode.value = 'type'
}

// snap to the best-practice type when the current one doesn't suit the data
// (also silently corrects an AI that picked a donut for a time series)
watchEffect(() => {
  if (
    isSeriesShape.value &&
    seriesType.value &&
    !rules.value.allowed.includes(props.widget.widget_type)
  ) {
    props.widget.widget_type = rules.value.preferred
  }
  if (isMatrix.value && !matrixRules.value.allowed.includes(props.widget.widget_type)) {
    props.widget.widget_type = 'Heatmap'
  }
})
</script>

<style scoped>
.vbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 2px 0;
  min-height: 28px;
  flex-wrap: wrap; /* safety valve on very narrow cards; normally one row */
}
.vt {
  width: 24px;
  height: 22px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--faint);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.vt:hover {
  color: var(--ink);
  border-color: var(--blue-300);
}
.vt.on {
  color: var(--blue);
  border-color: var(--blue);
  background: color-mix(in srgb, var(--blue) 8%, var(--panel));
}
.vsw {
  height: 22px;
  padding: 0 5px 0 4px;
  margin-left: auto;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--faint);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 3px;
  flex: none;
}
.vsw:hover {
  border-color: var(--blue-300);
  color: var(--ink);
}
.sw {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: block;
}
.vc {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0;
  flex: none;
}
.vc.on {
  border-color: var(--ink);
  box-shadow: 0 0 0 2px var(--panel);
}
</style>
