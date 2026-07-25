<template>
  <div class="vbar" @click.stop>
    <!-- one row of values: the interchangeable chart family -->
    <template v-if="isSeriesShape && seriesType">
      <button
        v-for="t in TYPES"
        :key="t.value"
        class="vt"
        :class="{ on: widget.widget_type === t.value, off: !rules.allowed.includes(t.value) }"
        :disabled="!rules.allowed.includes(t.value)"
        :title="rules.allowed.includes(t.value) ? t.label : rules.reasons[t.value]"
        @click="widget.widget_type = t.value"
      >
        <ChartIcon :type="t.value" />
      </button>
      <template v-if="hasAccent">
        <span class="vsep"></span>
        <button
          v-for="(c, i) in palette"
          :key="i"
          class="vc"
          :class="{ on: accent === i }"
          :style="{ background: c }"
          :title="'Color ' + (i + 1)"
          @click="setAccent(i)"
        ></button>
      </template>
    </template>

    <!-- two-dimensional results read as a grid or as overlaid webs -->
    <template v-else-if="isMatrix">
      <button
        v-for="t in MATRIX_TYPES"
        :key="t.value"
        class="vt"
        :class="{ on: widget.widget_type === t.value, off: !matrixRules.allowed.includes(t.value) }"
        :disabled="!matrixRules.allowed.includes(t.value)"
        :title="matrixRules.allowed.includes(t.value) ? t.label : matrixRules.reasons[t.value]"
        @click="widget.widget_type = t.value"
      >
        <ChartIcon :type="t.value" />
      </button>
      <span class="vsep"></span>
      <button
        v-for="(c, i) in palette"
        :key="i"
        class="vc"
        :class="{ on: accent === i }"
        :style="{ background: c }"
        :title="'Color ' + (i + 1)"
        @click="setAccent(i)"
      ></button>
    </template>

    <template v-else-if="isPoints || widget.widget_type === 'Gauge'">
      <span class="mono vlabel">Color</span>
      <button
        v-for="(c, i) in palette"
        :key="i"
        class="vc"
        :class="{ on: accent === i }"
        :style="{ background: c }"
        :title="'Color ' + (i + 1)"
        @click="setAccent(i)"
      ></button>
    </template>

    <template v-else-if="widget.widget_type === 'Number Card'">
      <span class="mono vlabel">Tint</span>
      <button
        v-for="t in TINTS"
        :key="t.name"
        class="vc"
        :class="{ on: (widget.style?.tint || defaultTint) === t.name }"
        :style="{ background: t.color }"
        :title="t.name"
        @click="setTint(t.name)"
      ></button>
    </template>
  </div>
</template>

<script setup>
import { computed, watchEffect } from 'vue'
import { chartPalette, themeVersion } from '@/lib/theme'
import ChartIcon from '@/components/widgets/ChartIcon.vue'

const props = defineProps({
  widget: { type: Object, required: true }, // mutated in place: widget_type / style
  result: { type: Object, default: null }, // used to judge shape + category count
  defaultTint: { type: String, default: 'blue' },
})

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
  { value: 'Heatmap', label: 'Heatmap' },
  { value: 'Radar', label: 'Radar — one web per row' },
]
const TINTS = [
  { name: 'blue', color: '#1463FF' },
  { name: 'green', color: '#0F9D7A' },
  { name: 'amber', color: '#C9821B' },
  { name: 'violet', color: '#6D4AFF' },
]
// single-colour charts wear the accent; categorical ones use the whole palette
const ACCENT_TYPES = [
  'Bar Chart',
  'Horizontal Bar',
  'Line Chart',
  'Area Chart',
  'Sparkline',
  'Waterfall',
  'Radar',
]

const SERIES_TYPES = new Set(TYPES.map((t) => t.value))
const shape = computed(() => props.result?.result_type || 'series')
const isSeriesShape = computed(() => shape.value === 'series')
const isMatrix = computed(() => shape.value === 'matrix')
const isPoints = computed(() => shape.value === 'points')
const seriesType = computed(() => SERIES_TYPES.has(props.widget.widget_type))
const hasAccent = computed(() => ACCENT_TYPES.includes(props.widget.widget_type))
const accent = computed(() => props.widget.style?.accent || 0)
const palette = computed(() => (themeVersion.value, chartPalette()))

// ---- form follows the data: which chart types actually suit this series ----
const TIME_REASON = 'A time sequence is a trend, not shares or ranks — use a line'
const DIST_REASON = 'A time distribution, not shares or ranks — bars show it best'
const CAT_REASON = 'Lines imply an order over time — categories need bars'
const SPARK_REASON = 'A sparkline traces a trend over time — categories have no sequence'

const rules = computed(() => {
  const grain = props.widget.query?.group_by?.time_grain
  const n = props.result?.labels?.length ?? 0

  if (grain === 'hour' || grain === 'weekday') {
    // 7 weekdays make a readable web; 24 hours do not
    const allowed = ['Bar Chart', 'Line Chart', 'Area Chart']
    if (grain === 'weekday') allowed.push('Radar')
    return {
      allowed,
      preferred: 'Bar Chart',
      reasons: {
        'Horizontal Bar': DIST_REASON,
        'Donut Chart': DIST_REASON,
        'Pie Chart': DIST_REASON,
        Funnel: DIST_REASON,
        Rings: DIST_REASON,
        Radar: 'Too many spokes for a readable web — use bars',
        Sparkline: 'A distribution has no running trend to trace',
        Waterfall: 'Nothing accumulates across a distribution — use bars',
      },
    }
  }
  if (grain) {
    return {
      allowed: ['Line Chart', 'Area Chart', 'Bar Chart', 'Sparkline', 'Waterfall'],
      preferred: 'Line Chart',
      reasons: {
        'Horizontal Bar': TIME_REASON,
        'Donut Chart': TIME_REASON,
        'Pie Chart': TIME_REASON,
        Funnel: TIME_REASON,
        Rings: TIME_REASON,
        Radar: TIME_REASON,
      },
    }
  }
  if (n > 8) {
    return {
      allowed: ['Bar Chart', 'Horizontal Bar'],
      preferred: 'Horizontal Bar',
      reasons: {
        'Line Chart': CAT_REASON,
        'Area Chart': CAT_REASON,
        Sparkline: SPARK_REASON,
        Waterfall: `Too many steps (${n}) to follow a running balance`,
        'Donut Chart': `Too many categories (${n}) for a readable pie — use ranked bars`,
        'Pie Chart': `Too many categories (${n}) for a readable pie — use ranked bars`,
        Funnel: `Too many categories (${n}) for a funnel`,
        Rings: `Too many categories (${n}) for rings — five at most`,
        Radar: `Too many axes (${n}) for a readable web`,
      },
    }
  }
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
    reasons: {
      'Line Chart': CAT_REASON,
      'Area Chart': CAT_REASON,
      Sparkline: SPARK_REASON,
    },
  }
})

const matrixRules = computed(() => {
  // rows become the spokes, columns become one web each
  const spokes = props.result?.rows?.length ?? 0
  const webs = props.result?.cols?.length ?? 0
  const allowed = ['Heatmap']
  if (webs <= 4 && spokes >= 3 && spokes <= 10) allowed.push('Radar')
  return {
    allowed,
    reasons: {
      Radar:
        webs > 4
          ? `${webs} overlaid webs would be unreadable — a heatmap scales`
          : `A radar needs 3-10 spokes, this has ${spokes}`,
    },
  }
})

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

function setAccent(i) {
  props.widget.style = { ...(props.widget.style || {}), accent: i }
}
function setTint(name) {
  props.widget.style = { ...(props.widget.style || {}), tint: name }
}
</script>

<style scoped>
.vbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 2px 0;
  flex-wrap: wrap;
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
}
.vt:hover:not(:disabled) {
  color: var(--ink);
  border-color: var(--blue-300);
}
.vt.on {
  color: var(--blue);
  border-color: var(--blue);
  background: color-mix(in srgb, var(--blue) 8%, var(--panel));
}
.vt.off {
  opacity: 0.32;
  cursor: not-allowed;
}
.vsep {
  width: 1px;
  height: 14px;
  background: var(--border-2);
  margin: 0 3px;
}
.vc {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0;
}
.vc.on {
  border-color: var(--ink);
  box-shadow: 0 0 0 2px var(--panel);
}
.vlabel {
  font-size: 9px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--faint);
  margin-right: 2px;
}
</style>
