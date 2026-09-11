<template>
  <div class="inspector">
    <!-- header: inline title + close -->
    <div class="ins-head">
      <input
        v-model="form.title"
        class="ins-title"
        type="text"
        dir="auto"
        :placeholder="isElement ? t('Block name (not shown)') : t('Widget title')"
      />
      <button class="ins-x" :title="t('Close (Esc)')" @click="$emit('close')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
      </button>
    </div>

    <div class="ins-body">
      <!-- type -->
      <div class="ins-sec">
        <div class="ins-eyebrow">{{ isElement ? t('Element') : t('Widget type') }}</div>
        <div v-if="isElement" class="flex flex-wrap gap-1.5">
          <button
            v-for="p in ELEMENT_PALETTE"
            :key="p.value"
            class="typechip"
            :class="{ on: form.widget_type === p.value }"
            :title="t(p.label)"
            @click="setElementType(p.value)"
          >
            <ElementIcon :type="p.value" :size="12" />
            {{ t(p.label) }}
          </button>
        </div>
        <div v-else class="flex flex-wrap gap-1.5">
          <button
            v-for="p in WIDGET_TYPES"
            :key="p.value"
            class="typechip"
            :class="{ on: form.widget_type === p.value }"
            :title="t(p.label)"
            @click="form.widget_type = p.value"
          >
            <ChartIcon :type="p.value" :size="12" />
            {{ t(p.label) }}
          </button>
        </div>
      </div>

      <!-- content: the layout elements carry text and pictures, not queries -->
      <div v-if="isElement" class="ins-sec">
        <div class="ins-eyebrow">{{ t('Content') }}</div>

        <template v-if="form.widget_type === 'Heading'">
          <div class="lfield">
            <label>{{ t('Heading') }}</label>
            <input type="text" v-model="form.text" dir="auto" :placeholder="t('Section heading')" />
          </div>
          <div class="lfield">
            <label>{{ t('Sub-heading (optional)') }}</label>
            <input type="text" v-model="form.subtext" dir="auto" :placeholder="t('A line of context')" />
          </div>
          <div class="lfield">
            <label>{{ t('Size') }}</label>
            <div class="seg" style="width: fit-content">
              <button :class="{ on: form.level === 1 }" @click="form.level = 1">{{ t('Large') }}</button>
              <button :class="{ on: form.level === 2 }" @click="form.level = 2">{{ t('Medium') }}</button>
              <button :class="{ on: form.level === 3 }" @click="form.level = 3">{{ t('Label') }}</button>
            </div>
          </div>
        </template>

        <template v-else-if="form.widget_type === 'Text'">
          <div class="lfield">
            <label>{{ t('Note') }}</label>
            <textarea v-model="form.text" rows="5" dir="auto" :placeholder="t('Explain what this section shows, who it is for, or how to read it.')"></textarea>
          </div>
          <div class="lfield">
            <label>{{ t('Size') }}</label>
            <div class="seg" style="width: fit-content">
              <button :class="{ on: form.size === 'sm' }" @click="form.size = 'sm'">{{ t('Small') }}</button>
              <button :class="{ on: form.size === 'md' }" @click="form.size = 'md'">{{ t('Normal') }}</button>
              <button :class="{ on: form.size === 'lg' }" @click="form.size = 'lg'">{{ t('Lead') }}</button>
            </div>
          </div>
        </template>

        <template v-else-if="form.widget_type === 'Divider'">
          <div class="lfield">
            <label>{{ t('Label (optional)') }}</label>
            <input type="text" v-model="form.text" dir="auto" :placeholder="t('e.g. Second half')" />
          </div>
        </template>

        <template v-else>
          <div class="lfield">
            <label>{{ t('Image URL') }}</label>
            <input type="text" v-model="form.url" dir="ltr" placeholder="/files/logo.png" spellcheck="false" />
          </div>
          <div class="lfield">
            <label>{{ t('Fit') }}</label>
            <div class="seg" style="width: fit-content">
              <button :class="{ on: form.fit === 'contain' }" @click="form.fit = 'contain'">{{ t('Fit inside') }}</button>
              <button :class="{ on: form.fit === 'cover' }" @click="form.fit = 'cover'">{{ t('Fill') }}</button>
            </div>
          </div>
        </template>

        <div v-if="form.widget_type !== 'Divider'" class="lfield">
          <label>{{ t('Alignment') }}</label>
          <div class="seg" style="width: fit-content">
            <button :class="{ on: form.align === 'left' }" @click="form.align = 'left'">{{ t('Left') }}</button>
            <button :class="{ on: form.align === 'center' }" @click="form.align = 'center'">{{ t('Center') }}</button>
            <button :class="{ on: form.align === 'right' }" @click="form.align = 'right'">{{ t('Right') }}</button>
          </div>
        </div>

        <label
          v-if="form.widget_type === 'Text' || form.widget_type === 'Image'"
          class="flex cursor-pointer items-center gap-2 text-[12.5px]"
          style="color: var(--ink-2)"
        >
          <input type="checkbox" v-model="form.framed" />
          {{ t('Put it on a card') }}
        </label>
      </div>

      <!-- data source -->
      <div v-if="!isElement" class="ins-sec">
        <div class="ins-eyebrow">{{ t('Data') }}</div>
        <div class="lfield">
          <label>{{ t('Source') }}</label>
          <select v-model="form.doctype" @change="onDoctypeChange">
            <option value="" disabled>{{ t('Select a doctype…') }}</option>
            <option v-for="d in doctypes.data || []" :key="d.name" :value="d.name">{{ d.name }}</option>
          </select>
        </div>

        <div v-if="lineTables.length" class="lfield">
          <label>{{ t('Analyze by') }}</label>
          <div class="seg" style="width: fit-content">
            <button :class="{ on: form.grain === 'document' }" @click="setGrain('document')">{{ t('By document') }}</button>
            <button :class="{ on: form.grain === 'line' }" @click="setGrain('line')">
              {{ t('By line item') }}
            </button>
          </div>
        </div>

        <template v-if="form.widget_type !== 'Table'">
          <div class="grid grid-cols-2 gap-2.5">
            <div class="lfield">
              <label>{{ isScatter ? t('X measure') : t('Measure') }}</label>
              <select v-model="form.aggregate_function">
                <option v-for="a in AGGREGATES" :key="a" :value="a">{{ t(AGG_LABELS[a]) }}</option>
              </select>
            </div>
            <div v-if="form.aggregate_function !== 'count'" class="lfield">
              <label>{{ t('Of field') }}</label>
              <select v-model="form.aggregate_field">
                <option value="" disabled>{{ t('Select…') }}</option>
                <option v-for="f in numericFields" :key="f.fieldname" :value="f.fieldname">{{ f.label }}</option>
              </select>
            </div>
          </div>

          <template v-if="isScatter">
            <div class="grid grid-cols-2 gap-2.5">
              <div class="lfield">
                <label>{{ t('Y measure') }}</label>
                <select v-model="form.y_function">
                  <option v-for="a in AGGREGATES" :key="a" :value="a">{{ t(AGG_LABELS[a]) }}</option>
                </select>
              </div>
              <div v-if="form.y_function !== 'count'" class="lfield">
                <label>{{ t('Of field') }}</label>
                <select v-model="form.y_field">
                  <option value="" disabled>{{ t('Select…') }}</option>
                  <option v-for="f in numericFields" :key="f.fieldname" :value="f.fieldname">{{ f.label }}</option>
                </select>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-2.5">
              <div class="lfield">
                <label>{{ t('Bubble size') }}</label>
                <select v-model="form.size_function">
                  <option value="">{{ t('Same for all') }}</option>
                  <option v-for="a in ['count', 'sum', 'avg']" :key="a" :value="a">{{ t(AGG_LABELS[a]) }}</option>
                </select>
              </div>
              <div v-if="form.size_function && form.size_function !== 'count'" class="lfield">
                <label>{{ t('Of field') }}</label>
                <select v-model="form.size_field">
                  <option value="" disabled>{{ t('Select…') }}</option>
                  <option v-for="f in numericFields" :key="f.fieldname" :value="f.fieldname">{{ f.label }}</option>
                </select>
              </div>
            </div>
          </template>

          <template v-if="needsGroup">
            <div class="grid grid-cols-2 gap-2.5">
              <div class="lfield">
                <label>{{ t(groupLabel) }}</label>
                <select v-model="form.group_key">
                  <option value="" disabled>{{ t('Select field…') }}</option>
                  <optgroup :label="t('Fields')">
                    <option v-for="o in groupOwn" :key="o.key" :value="o.key">{{ o.label }}</option>
                  </optgroup>
                  <optgroup v-if="groupRelated.length" :label="t('Related (joined)')">
                    <option v-for="o in groupRelated" :key="o.key" :value="o.key">{{ o.label }}</option>
                  </optgroup>
                </select>
              </div>
              <div v-if="groupByIsDate" class="lfield">
                <label>{{ t('Time grain') }}</label>
                <select v-model="form.time_grain">
                  <option v-for="g in ['hour', 'weekday', 'day', 'week', 'month', 'year']" :key="g" :value="g">{{ t(GRAIN_LABELS[g]) }}</option>
                </select>
              </div>
            </div>
            <div v-if="usesGroup2" class="grid grid-cols-2 gap-2.5">
              <div class="lfield">
                <label>{{ t(group2Label) }}</label>
                <select v-model="form.group2_key">
                  <option v-if="group2Optional" value="">{{ t('None') }}</option>
                  <option v-else value="" disabled>{{ t('Select field…') }}</option>
                  <optgroup :label="t('Fields')">
                    <option v-for="o in groupOwn" :key="o.key" :value="o.key">{{ o.label }}</option>
                  </optgroup>
                  <optgroup v-if="groupRelated.length" :label="t('Related (joined)')">
                    <option v-for="o in groupRelated" :key="o.key" :value="o.key">{{ o.label }}</option>
                  </optgroup>
                </select>
              </div>
              <div v-if="group2IsDate" class="lfield">
                <label>{{ t('Time grain') }}</label>
                <select v-model="form.time_grain2">
                  <option v-for="g in ['hour', 'weekday', 'day', 'month']" :key="g" :value="g">{{ t(GRAIN_LABELS[g]) }}</option>
                </select>
              </div>
            </div>
            <div v-if="isTree && form.group2_key" class="lfield">
              <label>{{ t('Then by (level 3, optional)') }}</label>
              <select v-model="form.group3_key">
                <option value="">{{ t('None') }}</option>
                <optgroup :label="t('Fields')">
                  <option v-for="o in groupOwn" :key="o.key" :value="o.key">{{ o.label }}</option>
                </optgroup>
                <optgroup v-if="groupRelated.length" :label="t('Related (joined)')">
                  <option v-for="o in groupRelated" :key="o.key" :value="o.key">{{ o.label }}</option>
                </optgroup>
              </select>
            </div>
          </template>

          <div v-if="usesTarget" class="lfield">
            <label>{{ isRings ? t('Target per ring (leave blank for share of total)') : t('Target') }}</label>
            <input type="number" v-model.number="form.target" :placeholder="t('e.g. {0}', '1000000')" />
          </div>
        </template>

        <template v-else>
          <div class="lfield">
            <label>{{ t('Columns') }}</label>
            <div class="flex max-h-44 flex-col gap-1 overflow-auto rounded-[10px] p-2" style="border: 1px solid var(--border-2)">
              <label
                v-for="f in columnFields"
                :key="f.key"
                class="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-[12.5px] hover:bg-[var(--panel-2)]"
              >
                <input type="checkbox" :value="f.key" v-model="form.columns" />
                <span style="color: var(--ink-2)">{{ f.label }}</span>
                <span class="mono" style="font-size: 10px; color: var(--faint)">{{ f.fieldtype }}</span>
              </label>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2.5">
            <div class="lfield" style="grid-column: span 2">
              <label>{{ t('Sort by') }}</label>
              <select v-model="form.sort_field">
                <option value="modified">{{ t('Last modified') }}</option>
                <option v-for="f in columnFields" :key="f.key" :value="f.key">{{ f.label }}</option>
              </select>
            </div>
            <div class="lfield">
              <label>{{ t('Order') }}</label>
              <select v-model="form.sort_order">
                <option value="desc">{{ t('Descending') }}</option>
                <option value="asc">{{ t('Ascending') }}</option>
              </select>
            </div>
          </div>
          <div class="lfield" style="max-width: 110px">
            <label>{{ t('Rows') }}</label>
            <input type="number" v-model.number="form.limit" min="1" max="100" />
          </div>
        </template>
      </div>

      <!-- appearance -->
      <div v-if="!isElement && (form.widget_type === 'Number Card' || hasAccent)" class="ins-sec">
        <div class="ins-eyebrow">{{ t('Appearance') }}</div>
        <div v-if="form.widget_type === 'Number Card'" class="lfield">
          <label>{{ t('Tint') }}</label>
          <div class="flex items-center gap-2">
            <button
              v-for="tint in TINTS"
              :key="tint.name"
              class="dot"
              :class="{ on: form.tint === tint.name }"
              :style="{ background: tint.color }"
              :title="t(tint.label)"
              @click="form.tint = tint.name"
            ></button>
          </div>
        </div>
        <div v-else class="lfield">
          <label>{{ t('Color') }}</label>
          <div class="flex items-center gap-2">
            <button
              v-for="(c, i) in paletteColors"
              :key="i"
              class="dot"
              :class="{ on: form.accent === i }"
              :style="{ background: c }"
              :title="t('Color {0}', i + 1)"
              @click="form.accent = i"
            ></button>
          </div>
        </div>
      </div>

      <!-- widget filters -->
      <div v-if="!isElement" class="ins-sec">
        <div class="ins-eyebrow">{{ t('Widget filters') }}</div>
        <div class="flex flex-col gap-2">
          <div v-for="(f, i) in form.filters" :key="i" class="flex items-center gap-1.5">
            <select v-model="f[0]" style="flex: 2" class="ins-mini">
              <option v-for="fd in ownFields" :key="fd.fieldname" :value="fd.fieldname">{{ fd.label }}</option>
            </select>
            <select v-model="f[1]" style="flex: 1" class="ins-mini">
              <option v-for="op in ['=', '!=', '>', '<', '>=', '<=', 'like']" :key="op" :value="op">{{ op }}</option>
            </select>
            <input type="text" v-model="f[2]" dir="auto" :placeholder="t('value')" style="flex: 2" class="ins-mini" />
            <button class="icon-x" :title="t('Remove')" @click="form.filters.splice(i, 1)">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>
          </div>
          <button class="chip" style="align-self: flex-start; border-style: dashed" @click="form.filters.push(['', '=', ''])">
            + {{ t('Add filter') }}
          </button>
        </div>
      </div>
    </div>

    <!-- status footer -->
    <div class="ins-foot">
      <template v-if="!canApply">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16.5v.01" /></svg>
        <span>{{ needsGroup ? t('Pick a source and a breakdown to apply') : t('Pick a source to apply') }}</span>
      </template>
      <template v-else-if="isElement">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2.4" stroke-linecap="round"><path d="m4.5 12.5 5 5 10-11" /></svg>
        <span>{{ t('This block carries no data, so it never loads') }}</span>
      </template>
      <template v-else>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2.4" stroke-linecap="round"><path d="m4.5 12.5 5 5 10-11" /></svg>
        <span>{{ t('Changes apply live on the canvas') }}</span>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { createResource } from 'frappe-ui'
import { chartPalette, themeVersion } from '@/lib/theme'
import { ELEMENT_PALETTE, defaultStyle, isStatic } from '@/lib/widgetTypes'
import { t } from '@/lib/i18n'
import ChartIcon from '@/components/widgets/ChartIcon.vue'
import ElementIcon from '@/components/widgets/ElementIcon.vue'

const AGGREGATES = ['count', 'sum', 'avg', 'min', 'max']
const AGG_LABELS = { count: 'Count', sum: 'Sum', avg: 'Average', min: 'Minimum', max: 'Maximum' }
const GRAIN_LABELS = {
  hour: 'Hour of day',
  weekday: 'Day of week',
  day: 'Day',
  week: 'Week',
  month: 'Month',
  year: 'Year',
}

const props = defineProps({
  widget: { type: Object, required: true },
})
const emit = defineEmits(['close', 'apply'])

const WIDGET_TYPES = [
  { label: 'Number', value: 'Number Card' },
  { label: 'Gauge', value: 'Gauge' },
  { label: 'Sparkline', value: 'Sparkline' },
  { label: 'Bar', value: 'Bar Chart' },
  { label: 'Stacked', value: 'Stacked Bar' },
  { label: 'Ranked', value: 'Horizontal Bar' },
  { label: 'Line', value: 'Line Chart' },
  { label: 'Area', value: 'Area Chart' },
  { label: 'Waterfall', value: 'Waterfall' },
  { label: 'Progress', value: 'Progress Bars' },
  { label: 'Donut', value: 'Donut Chart' },
  { label: 'Pie', value: 'Pie Chart' },
  { label: 'Rings', value: 'Rings' },
  { label: 'Radar', value: 'Radar' },
  { label: 'Funnel', value: 'Funnel' },
  { label: 'Scatter', value: 'Scatter' },
  { label: 'Heatmap', value: 'Heatmap' },
  { label: 'Tree', value: 'Tree Report' },
  { label: 'Table', value: 'Table' },
]
const TINTS = [
  { name: 'blue', label: 'Blue', color: '#1463FF' },
  { name: 'green', label: 'Green', color: '#0F9D7A' },
  { name: 'amber', label: 'Amber', color: '#C9821B' },
  { name: 'violet', label: 'Violet', color: '#6D4AFF' },
]
const NO_GROUP_TYPES = ['Number Card', 'Gauge', 'Table']
const GROUP2_TYPES = ['Heatmap', 'Radar', 'Bar Chart', 'Stacked Bar', 'Line Chart', 'Area Chart', 'Tree Report']
const GROUP2_LABELS = {
  Heatmap: 'Columns (split by)',
  Radar: 'One web per (optional)',
  'Tree Report': 'Then by (level 2)',
}
const GROUP_LABELS = {
  Heatmap: 'Rows',
  Radar: 'Axes (spokes)',
  Rings: 'One ring per',
  'Progress Bars': 'One bar per',
  Scatter: 'One point per',
  Waterfall: 'Steps',
  'Tree Report': 'Group by (level 1)',
}
const ACCENT_TYPES = [
  'Bar Chart',
  'Horizontal Bar',
  'Line Chart',
  'Area Chart',
  'Sparkline',
  'Waterfall',
  'Progress Bars',
  'Radar',
  'Scatter',
  'Heatmap',
]

function groupKeyFromQuery(query) {
  const g = query.group_by
  if (!g?.field) return ''
  if (g.via) return `${g.via.link_field}>${g.via.doctype}.${g.field}`
  return `own:${g.field}`
}
function columnKeysFromQuery(query) {
  return (query.fields || ['name']).map((ref) =>
    typeof ref === 'string' ? `own:${ref}` : `${ref.via.link_field}>${ref.via.doctype}.${ref.field}`
  )
}

const form = reactive({
  title: '',
  doctype: '',
  grain: 'document',
  line_table: '',
  widget_type: 'Bar Chart',
  aggregate_function: 'count',
  aggregate_field: '',
  y_function: 'sum',
  y_field: '',
  size_function: '',
  size_field: '',
  group_key: '',
  time_grain: 'month',
  group2_key: '',
  time_grain2: 'hour',
  group3_key: '',
  target: null,
  tint: 'blue',
  accent: 0,
  columns: ['own:name'],
  sort_field: 'modified',
  sort_order: 'desc',
  limit: 10,
  filters: [],
  // layout elements
  text: '',
  subtext: '',
  level: 1,
  align: 'left',
  size: 'md',
  url: '',
  fit: 'contain',
  framed: false,
})

// filters the panel doesn't render (base scoping via a related ref) —
// preserved verbatim so live editing never drops them
const preservedFilters = ref([])
// guards the form-watcher while we rebuild the form from a widget
let syncing = false
// what the widget currently is, so unchanged forms never re-apply
let lastApplied = ''

function syncFromWidget() {
  syncing = true
  const w = props.widget || {}
  const q = w.query || {}
  const isLine = !!q.parent_doctype
  form.title = w.title || ''
  form.doctype = isLine ? q.parent_doctype : q.doctype || ''
  form.grain = isLine ? 'line' : 'document'
  form.line_table = isLine ? q.doctype : ''
  form.widget_type = w.widget_type || 'Bar Chart'
  form.aggregate_function = q.aggregate?.function || 'count'
  form.aggregate_field = q.aggregate?.field || ''
  form.y_function = q.aggregate_y?.function || 'sum'
  form.y_field = q.aggregate_y?.field || ''
  form.size_function = q.aggregate_size?.function || ''
  form.size_field = q.aggregate_size?.field || ''
  form.group_key = groupKeyFromQuery(q)
  form.time_grain = q.group_by?.time_grain || 'month'
  form.group2_key = q.group_by2 ? groupKeyFromQuery({ group_by: q.group_by2 }) : ''
  form.time_grain2 = q.group_by2?.time_grain || 'hour'
  form.group3_key = q.group_by3 ? groupKeyFromQuery({ group_by: q.group_by3 }) : ''
  form.target = w.style?.target ?? null
  form.tint = w.style?.tint || 'blue'
  form.accent = w.style?.accent || 0
  form.columns = columnKeysFromQuery(q)
  form.sort_field = q.sort ? groupKeyFromQuery({ group_by: q.sort }) : 'modified'
  form.sort_order = q.sort?.order || 'desc'
  form.limit = q.limit || 10
  form.filters = (q.filters || []).filter((f) => typeof f[0] === 'string').map((f) => [...f])
  preservedFilters.value = (q.filters || []).filter((f) => typeof f?.[0] !== 'string')
  const s = w.style || {}
  form.text = s.text || ''
  form.subtext = s.subtext || ''
  form.level = Number(s.level) || 1
  form.align = s.align || 'left'
  form.size = s.size || 'md'
  form.url = s.url || ''
  form.fit = s.fit || 'contain'
  form.framed = !!s.framed
  lastApplied = ''
  // release the guard after the watchers triggered by this sync have run
  setTimeout(() => {
    syncing = false
    lastApplied = canApply.value ? JSON.stringify(buildConfig()) : ''
  }, 0)
}

// re-sync when a different widget is selected, or the object is replaced
// externally (e.g. the AI rewrote it) — our own applies mutate in place
watch(() => props.widget, syncFromWidget, { immediate: true })

const doctypes = createResource({ url: 'lumen_reports.api.get_doctypes', auto: true })
const docFields = createResource({ url: 'lumen_reports.api.get_doctype_fields' })
const lineFields = createResource({ url: 'lumen_reports.api.get_doctype_fields' })

watch(
  () => form.doctype,
  (dt) => {
    if (dt) docFields.fetch({ doctype: dt })
  },
  { immediate: true }
)

const lineTables = computed(() => docFields.data?.line_item_tables || [])

watch(
  [() => form.grain, () => form.line_table, () => form.doctype, lineTables],
  () => {
    if (form.grain !== 'line') return
    if (!form.line_table && lineTables.value[0]) form.line_table = lineTables.value[0].child_doctype
    if (form.line_table) {
      lineFields.fetch({ doctype: form.line_table, parent_doctype: form.doctype })
    }
  },
  { immediate: true }
)

const effectiveFields = computed(() => (form.grain === 'line' ? lineFields.data : docFields.data))
const effectiveBase = computed(() => (form.grain === 'line' ? form.line_table : form.doctype))

const ownFields = computed(() => effectiveFields.value?.fields || [])
const numericFields = computed(() => effectiveFields.value?.numeric || [])
const groupOwn = computed(() =>
  (effectiveFields.value?.groupable || []).map((f) => ({
    key: `own:${f.fieldname}`,
    label: f.label,
    ref: f.fieldname,
    isDate: (effectiveFields.value?.date || []).some((d) => d.fieldname === f.fieldname),
  }))
)
const groupRelated = computed(() =>
  (effectiveFields.value?.related_fields || []).map((r) => ({
    key: r.key,
    label: r.label,
    ref: { field: r.field, via: r.via },
    isDate: ['Date', 'Datetime'].includes(r.fieldtype),
  }))
)
const allGroupOptions = computed(() => [...groupOwn.value, ...groupRelated.value])
const selectedGroup = computed(() => allGroupOptions.value.find((o) => o.key === form.group_key))
const groupByIsDate = computed(() => !!selectedGroup.value?.isDate)
const selectedGroup2 = computed(() => allGroupOptions.value.find((o) => o.key === form.group2_key))
const group2IsDate = computed(() => !!selectedGroup2.value?.isDate)
const selectedGroup3 = computed(() => allGroupOptions.value.find((o) => o.key === form.group3_key))
const paletteColors = computed(() => (themeVersion.value, chartPalette()))

const columnFields = computed(() => {
  const own = ownFields.value.map((f) => ({ key: `own:${f.fieldname}`, label: f.label, fieldtype: f.fieldtype }))
  const related = (effectiveFields.value?.related_fields || []).map((r) => ({
    key: r.key,
    label: r.label,
    fieldtype: r.fieldtype,
  }))
  return [...own, ...related]
})

function onDoctypeChange() {
  form.grain = 'document'
  form.line_table = ''
  form.group_key = ''
  form.aggregate_field = ''
  form.columns = ['own:name']
  preservedFilters.value = []
}
function setGrain(grain) {
  if (form.grain === grain) return
  form.grain = grain
  if (grain === 'document') form.line_table = ''
  form.group_key = ''
  form.aggregate_field = ''
  form.columns = ['own:name']
  preservedFilters.value = []
}

function keyToRef(key) {
  if (key.startsWith('own:')) return key.slice(4)
  const [linkPart, rest] = key.split('>')
  const dot = rest.lastIndexOf('.')
  const doctype = rest.slice(0, dot)
  const field = rest.slice(dot + 1)
  return { field, via: { link_field: linkPart, doctype } }
}

const isElement = computed(() => isStatic(form.widget_type))
const needsGroup = computed(() => !isElement.value && !NO_GROUP_TYPES.includes(form.widget_type))
const isScatter = computed(() => form.widget_type === 'Scatter')
const isRings = computed(() => form.widget_type === 'Rings')
const isTree = computed(() => form.widget_type === 'Tree Report')
const usesGroup2 = computed(() => GROUP2_TYPES.includes(form.widget_type))
const usesTarget = computed(() => ['Gauge', 'Rings', 'Progress Bars'].includes(form.widget_type))
const hasAccent = computed(
  () => ACCENT_TYPES.includes(form.widget_type) || form.widget_type === 'Gauge'
)
const groupLabel = computed(() => GROUP_LABELS[form.widget_type] || 'Break down by')
const group2Label = computed(() => GROUP2_LABELS[form.widget_type] || 'Split by (optional)')
const group2Optional = computed(
  () => form.widget_type !== 'Heatmap' && form.widget_type !== 'Stacked Bar'
)

const canApply = computed(() => {
  if (isElement.value) return true // nothing to validate: no query to run
  if (['Heatmap', 'Stacked Bar'].includes(form.widget_type) && !selectedGroup2.value) return false
  if (isScatter.value && form.y_function !== 'count' && !form.y_field) return false
  if (isScatter.value && form.size_function && form.size_function !== 'count' && !form.size_field) return false
  if (!effectiveBase.value) return false
  if (!effectiveFields.value) return false
  if (needsGroup.value) return !!selectedGroup.value
  return true
})

function buildQuery() {
  const query = { doctype: effectiveBase.value }
  if (form.grain === 'line') query.parent_doctype = form.doctype

  const filters = [
    ...preservedFilters.value,
    ...form.filters.filter((f) => f[0] && f[2] !== '').map((f) => [...f]),
  ]
  if (filters.length) query.filters = filters

  if (form.widget_type === 'Table') {
    query.fields = form.columns.map(keyToRef)
    const sortRef = keyToRef(form.sort_field === 'modified' ? 'own:modified' : form.sort_field)
    query.sort = typeof sortRef === 'string' ? { field: sortRef } : { field: sortRef.field, via: sortRef.via }
    query.sort.order = form.sort_order
    query.limit = form.limit || 10
    return query
  }

  query.aggregate = { function: form.aggregate_function }
  if (form.aggregate_function !== 'count') query.aggregate.field = form.aggregate_field

  if (isScatter.value) {
    query.aggregate_y = { function: form.y_function }
    if (form.y_function !== 'count') query.aggregate_y.field = form.y_field
    if (form.size_function) {
      query.aggregate_size = { function: form.size_function }
      if (form.size_function !== 'count') query.aggregate_size.field = form.size_field
    }
  }

  if (needsGroup.value && selectedGroup.value) {
    const ref = selectedGroup.value.ref
    query.group_by = typeof ref === 'string' ? { field: ref } : { field: ref.field, via: ref.via }
    if (groupByIsDate.value) query.group_by.time_grain = form.time_grain
  }
  if (usesGroup2.value && selectedGroup2.value) {
    const ref2 = selectedGroup2.value.ref
    query.group_by2 = typeof ref2 === 'string' ? { field: ref2 } : { field: ref2.field, via: ref2.via }
    if (group2IsDate.value) query.group_by2.time_grain = form.time_grain2
  }
  if (isTree.value) {
    query.shape = 'tree'
    if (selectedGroup3.value && query.group_by2) {
      const ref3 = selectedGroup3.value.ref
      query.group_by3 = typeof ref3 === 'string' ? { field: ref3 } : { field: ref3.field, via: ref3.via }
    }
  }
  return query
}

function setElementType(type) {
  if (form.widget_type === type) return
  form.widget_type = type
  // carry the text across (a heading often becomes a note), but reset the
  // knobs that mean nothing on the new element
  Object.assign(form, { level: 1, size: 'md', fit: 'contain' }, defaultStyle(type), {
    text: form.text,
  })
}

function elementStyle() {
  const type = form.widget_type
  if (type === 'Heading') {
    const style = { text: form.text, level: form.level, align: form.align }
    if (form.subtext) style.subtext = form.subtext
    return style
  }
  if (type === 'Text') {
    return { text: form.text, align: form.align, size: form.size, framed: !!form.framed }
  }
  if (type === 'Divider') return { text: form.text }
  return { url: form.url, fit: form.fit, align: form.align, framed: !!form.framed }
}

function buildConfig() {
  if (isElement.value) {
    return {
      title: form.title || t(form.widget_type),
      widget_type: form.widget_type,
      query: {},
      style: elementStyle(),
    }
  }
  let style = {}
  if (form.widget_type === 'Number Card') style = { tint: form.tint }
  else if (usesTarget.value) {
    style = { accent: form.accent || 0 }
    if (form.target) style.target = form.target
  } else if (ACCENT_TYPES.includes(form.widget_type) && form.accent) style = { accent: form.accent }
  return {
    title: form.title || t('Untitled'),
    widget_type: form.widget_type,
    query: buildQuery(),
    style,
  }
}

// ---- live apply (debounced) ----
let applyTimer = null
watch(
  [form, effectiveFields],
  () => {
    if (syncing) return
    clearTimeout(applyTimer)
    applyTimer = setTimeout(() => {
      if (syncing || !canApply.value) return
      const config = buildConfig()
      const serialized = JSON.stringify(config)
      if (serialized === lastApplied) return
      lastApplied = serialized
      emit('apply', config)
    }, 450)
  },
  { deep: true }
)
</script>

<style scoped>
.inspector {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--panel);
}
.ins-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 13px 14px;
  border-bottom: 1px solid var(--border);
  flex: none;
}
.ins-title {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--ink);
  font-family: var(--font);
  font-size: 14.5px;
  font-weight: 800;
  letter-spacing: -0.01em;
  padding: 4px 6px;
  border-radius: 8px;
}
.ins-title:hover {
  background: var(--panel-2);
}
.ins-title:focus {
  background: var(--panel-2);
  box-shadow: 0 0 0 1.5px var(--blue-300);
}
.ins-x {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--faint);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.ins-x:hover {
  background: var(--panel-2);
  color: var(--ink);
}
.ins-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.ins-sec {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ins-eyebrow {
  font-family: var(--mono);
  font-size: 9.5px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
  font-weight: 500;
}
.typechip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 26px;
  padding: 0 9px;
  border-radius: 8px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--ink-2);
  font-family: var(--font);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}
.typechip svg {
  opacity: 0.75;
}
.typechip:hover {
  border-color: var(--blue-300);
}
.typechip.on {
  border-color: var(--blue);
  color: var(--blue);
  background: color-mix(in srgb, var(--blue) 7%, var(--panel));
}
.typechip.on svg {
  opacity: 1;
}
.dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0;
}
.dot.on {
  border-color: var(--ink);
  box-shadow: 0 0 0 2px var(--panel);
}
.ins-mini {
  height: 30px;
  padding: 0 7px;
  border-radius: 8px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--ink);
  font-family: var(--font);
  font-size: 12px;
  outline: none;
  min-width: 0;
}
.icon-x {
  border: none;
  background: transparent;
  color: var(--faint);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: flex;
}
.icon-x:hover {
  color: var(--danger);
  background: var(--panel-2);
}
.ins-foot {
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 16px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}
</style>
