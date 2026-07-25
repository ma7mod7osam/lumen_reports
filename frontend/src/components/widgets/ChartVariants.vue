<template>
  <div class="vbar" @click.stop>
    <template v-if="isSeries">
      <button
        v-for="t in TYPES"
        :key="t.value"
        class="vt"
        :class="{ on: widget.widget_type === t.value, off: !rules.allowed.includes(t.value) }"
        :disabled="!rules.allowed.includes(t.value)"
        :title="rules.allowed.includes(t.value) ? t.label : rules.reasons[t.value]"
        @click="widget.widget_type = t.value"
      >
        <!-- bar -->
        <svg v-if="t.value === 'Bar Chart'" width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="12" width="4.5" height="9" rx="1" /><rect x="10" y="5" width="4.5" height="16" rx="1" /><rect x="17" y="9" width="4.5" height="12" rx="1" /></svg>
        <!-- ranked / horizontal bars -->
        <svg v-else-if="t.value === 'Horizontal Bar'" width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="4" width="17" height="4" rx="1" /><rect x="3" y="10" width="12" height="4" rx="1" /><rect x="3" y="16" width="7" height="4" rx="1" /></svg>
        <!-- funnel -->
        <svg v-else-if="t.value === 'Funnel'" width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M4 4h16l-3 5H7L4 4Z" /><path d="M8 11h8l-2 4h-4l-2-4Z" opacity="0.75" /><path d="M10.6 17h2.8l-.9 3.5h-1L10.6 17Z" opacity="0.5" /></svg>
        <!-- line -->
        <svg v-else-if="t.value === 'Line Chart'" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m3 16 5.5-6 4.5 4L21 6" /></svg>
        <!-- area -->
        <svg v-else-if="t.value === 'Area Chart'" width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M3 20V16l5.5-6 4.5 4L21 6v14H3Z" opacity="0.45" /><path d="m3 16 5.5-6 4.5 4L21 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
        <!-- donut -->
        <svg v-else-if="t.value === 'Donut Chart'" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4.5"><circle cx="12" cy="12" r="7.5" /></svg>
        <!-- pie -->
        <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3a9 9 0 1 0 9 9h-9V3Z" /><path d="M14 2.2A9 9 0 0 1 21.8 10H14V2.2Z" opacity="0.55" /></svg>
      </button>
      <template v-if="isCartesian">
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

    <template v-else-if="widget.widget_type === 'Gauge' || widget.widget_type === 'Heatmap'">
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

const props = defineProps({
  widget: { type: Object, required: true }, // mutated in place: widget_type / style
  result: { type: Object, default: null }, // used to judge category count
  defaultTint: { type: String, default: 'blue' },
})

const TYPES = [
  { value: 'Bar Chart', label: 'Bar' },
  { value: 'Horizontal Bar', label: 'Ranked bars' },
  { value: 'Line Chart', label: 'Line' },
  { value: 'Area Chart', label: 'Area' },
  { value: 'Donut Chart', label: 'Donut' },
  { value: 'Pie Chart', label: 'Pie' },
  { value: 'Funnel', label: 'Funnel' },
]
const TINTS = [
  { name: 'blue', color: '#1463FF' },
  { name: 'green', color: '#0F9D7A' },
  { name: 'amber', color: '#C9821B' },
  { name: 'violet', color: '#6D4AFF' },
]

const SERIES_TYPES = new Set(TYPES.map((t) => t.value))
const isSeries = computed(() => SERIES_TYPES.has(props.widget.widget_type))
const isCartesian = computed(() =>
  ['Bar Chart', 'Line Chart', 'Area Chart'].includes(props.widget.widget_type)
)
const accent = computed(() => props.widget.style?.accent || 0)
const palette = computed(() => (themeVersion.value, chartPalette()))

// ---- form follows the data: which chart types actually suit this series ----
const TIME_REASON = 'A time sequence is a trend, not shares or ranks — use a line'
const DIST_REASON = 'A time distribution, not shares or ranks — bars show it best'
const CAT_REASON = 'Lines imply an order over time — categories need bars'

const rules = computed(() => {
  const grain = props.widget.query?.group_by?.time_grain
  if (grain === 'hour' || grain === 'weekday') {
    return {
      allowed: ['Bar Chart', 'Line Chart', 'Area Chart'],
      preferred: 'Bar Chart',
      reasons: {
        'Horizontal Bar': DIST_REASON,
        'Donut Chart': DIST_REASON,
        'Pie Chart': DIST_REASON,
        Funnel: DIST_REASON,
      },
    }
  }
  if (grain) {
    return {
      allowed: ['Line Chart', 'Area Chart', 'Bar Chart'],
      preferred: 'Line Chart',
      reasons: {
        'Horizontal Bar': TIME_REASON,
        'Donut Chart': TIME_REASON,
        'Pie Chart': TIME_REASON,
        Funnel: TIME_REASON,
      },
    }
  }
  const n = props.result?.labels?.length ?? 0
  if (n > 8) {
    return {
      allowed: ['Bar Chart', 'Horizontal Bar'],
      preferred: 'Horizontal Bar',
      reasons: {
        'Line Chart': CAT_REASON,
        'Area Chart': CAT_REASON,
        'Donut Chart': `Too many categories (${n}) for a readable pie — use ranked bars`,
        'Pie Chart': `Too many categories (${n}) for a readable pie — use ranked bars`,
        Funnel: `Too many categories (${n}) for a funnel`,
      },
    }
  }
  return {
    allowed: ['Bar Chart', 'Horizontal Bar', 'Donut Chart', 'Pie Chart', 'Funnel'],
    preferred: 'Bar Chart',
    reasons: {
      'Line Chart': CAT_REASON,
      'Area Chart': CAT_REASON,
    },
  }
})

// snap to the best-practice type when the current one doesn't suit the data
// (also silently corrects an AI that picked a donut for a time series)
watchEffect(() => {
  if (isSeries.value && !rules.value.allowed.includes(props.widget.widget_type)) {
    props.widget.widget_type = rules.value.preferred
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
