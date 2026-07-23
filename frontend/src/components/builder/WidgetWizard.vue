<template>
  <Modal
    :title="editing ? 'Edit widget' : 'Add widget'"
    subtitle="Build a report: pick a source, a measure, and a breakdown — preview is live"
    width="980px"
    @close="$emit('close')"
  >
    <div class="grid grid-cols-1 gap-0 lg:grid-cols-[380px_1fr]" style="min-height: 480px">
      <!-- form -->
      <div class="flex flex-col gap-4" style="padding: 18px; border-right: 1px solid var(--border)">
        <div class="lfield">
          <label>Title</label>
          <input type="text" v-model="form.title" placeholder="e.g. Revenue by Brand" />
        </div>

        <div class="lfield">
          <label>Data source</label>
          <select v-model="form.doctype" @change="onDoctypeChange">
            <option value="" disabled>Select a doctype…</option>
            <option v-for="d in doctypes.data || []" :key="d.name" :value="d.name">{{ d.name }}</option>
          </select>
        </div>

        <!-- grain: document vs line item -->
        <div v-if="lineTables.length" class="lfield">
          <label>Analyze by</label>
          <div class="seg" style="width: fit-content">
            <button :class="{ on: form.grain === 'document' }" @click="setGrain('document')">
              By document
            </button>
            <button :class="{ on: form.grain === 'line' }" @click="setGrain('line')">
              By {{ lineTables[0].label.toLowerCase().replace(/s$/, '') }}
            </button>
          </div>
          <p v-if="form.grain === 'line'" style="font-size: 11.5px; color: var(--muted); margin-top: 4px">
            One row per line item — group or measure by fields from the item, joined live.
          </p>
        </div>

        <div class="lfield">
          <label>Widget type</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="t in WIDGET_TYPES"
              :key="t.value"
              class="chip"
              :class="{ on: form.widget_type === t.value }"
              @click="form.widget_type = t.value"
            >
              {{ t.label }}
            </button>
          </div>
        </div>

        <template v-if="form.widget_type !== 'Table'">
          <div class="grid grid-cols-2 gap-3">
            <div class="lfield">
              <label>Measure</label>
              <select v-model="form.aggregate_function">
                <option value="count">Count</option>
                <option value="sum">Sum</option>
                <option value="avg">Average</option>
                <option value="min">Min</option>
                <option value="max">Max</option>
              </select>
            </div>
            <div v-if="form.aggregate_function !== 'count'" class="lfield">
              <label>Of field</label>
              <select v-model="form.aggregate_field">
                <option value="" disabled>Select…</option>
                <option v-for="f in numericFields" :key="f.fieldname" :value="f.fieldname">
                  {{ f.label }}
                </option>
              </select>
            </div>
          </div>

          <template v-if="form.widget_type !== 'Number Card'">
            <div class="grid grid-cols-2 gap-3">
              <div class="lfield">
                <label>Break down by</label>
                <select v-model="form.group_key">
                  <option value="" disabled>Select field…</option>
                  <optgroup label="Fields">
                    <option v-for="o in groupOwn" :key="o.key" :value="o.key">{{ o.label }}</option>
                  </optgroup>
                  <optgroup v-if="groupRelated.length" label="Related (joined)">
                    <option v-for="o in groupRelated" :key="o.key" :value="o.key">{{ o.label }}</option>
                  </optgroup>
                </select>
              </div>
              <div v-if="groupByIsDate" class="lfield">
                <label>Time grain</label>
                <select v-model="form.time_grain">
                  <option value="day">Day</option>
                  <option value="week">Week</option>
                  <option value="month">Month</option>
                  <option value="year">Year</option>
                </select>
              </div>
            </div>
          </template>

          <div v-if="form.widget_type === 'Number Card'" class="lfield">
            <label>Tint</label>
            <div class="flex gap-2">
              <button
                v-for="t in ['blue', 'green', 'amber', 'violet']"
                :key="t"
                class="chip"
                :class="{ on: form.tint === t }"
                @click="form.tint = t"
              >
                {{ t }}
              </button>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="lfield">
            <label>Columns</label>
            <div class="flex max-h-40 flex-col gap-1 overflow-auto rounded-[10px] p-2" style="border: 1px solid var(--border-2)">
              <label
                v-for="f in columnFields"
                :key="f.key"
                class="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-[13px] hover:bg-[var(--panel-2)]"
              >
                <input type="checkbox" :value="f.key" v-model="form.columns" />
                <span style="color: var(--ink-2)">{{ f.label }}</span>
                <span class="mono" style="font-size: 10px; color: var(--faint)">{{ f.fieldtype }}</span>
              </label>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div class="lfield" style="grid-column: span 2">
              <label>Sort by</label>
              <select v-model="form.sort_field">
                <option value="modified">Last Modified</option>
                <option v-for="f in columnFields" :key="f.key" :value="f.key">{{ f.label }}</option>
              </select>
            </div>
            <div class="lfield">
              <label>Order</label>
              <select v-model="form.sort_order">
                <option value="desc">Desc</option>
                <option value="asc">Asc</option>
              </select>
            </div>
          </div>
          <div class="lfield" style="max-width: 120px">
            <label>Rows</label>
            <input type="number" v-model.number="form.limit" min="1" max="100" />
          </div>
        </template>

        <!-- static widget filters (base fields) -->
        <div class="lfield">
          <label>Widget filters</label>
          <div class="flex flex-col gap-2">
            <div v-for="(f, i) in form.filters" :key="i" class="flex items-center gap-2">
              <select v-model="f[0]" style="flex: 2" class="wizard-mini">
                <option v-for="fd in ownFields" :key="fd.fieldname" :value="fd.fieldname">
                  {{ fd.label }}
                </option>
              </select>
              <select v-model="f[1]" style="flex: 1" class="wizard-mini">
                <option v-for="op in ['=', '!=', '>', '<', '>=', '<=', 'like']" :key="op" :value="op">{{ op }}</option>
              </select>
              <input type="text" v-model="f[2]" placeholder="value" style="flex: 2" class="wizard-mini" />
              <button class="icon-x" @click="form.filters.splice(i, 1)">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
              </button>
            </div>
            <button class="chip" style="align-self: flex-start; border-style: dashed" @click="form.filters.push(['', '=', ''])">
              + Add filter
            </button>
          </div>
        </div>
      </div>

      <!-- live preview -->
      <div class="flex flex-col" style="padding: 18px; background: var(--bg); min-width: 0">
        <div class="mono mb-3" style="font-size: 10.5px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--faint)">
          Live preview
        </div>
        <div class="flex min-h-0 flex-1 items-stretch justify-center">
          <div style="width: 100%; max-width: 560px">
            <div v-if="!canPreview" class="empty panel" style="height: 100%">
              <div class="ic">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M3 3v18h18" />
                  <path d="m7 15 4-6 4 3 5-8" />
                </svg>
              </div>
              <div style="font-weight: 700; color: var(--ink)">Configure the widget</div>
              <div style="font-size: 12.5px">Pick a source{{ needsGroup ? ' and a breakdown' : '' }} to see it live</div>
            </div>

            <div v-else-if="form.widget_type === 'Number Card'" class="panel kpi" style="max-width: 280px; min-height: 140px">
              <NumberBody :result="preview" :label="form.title || 'Untitled'" :tint="form.tint" />
            </div>

            <div v-else class="panel flex flex-col" style="height: 100%; min-height: 360px">
              <div class="panel-h" style="padding: 13px 18px">
                <div class="t">{{ form.title || 'Untitled' }}</div>
                <span v-if="previewLoading" class="badge b-gray">loading…</span>
                <span v-else-if="previewError" class="badge b-red" :title="String(previewError)">error</span>
              </div>
              <div class="min-h-0 flex-1" style="padding: 14px 18px 16px">
                <TableBody v-if="form.widget_type === 'Table'" :result="preview" />
                <ChartBody v-else :widget-type="form.widget_type" :result="preview" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between">
        <span v-if="previewError" style="font-size: 12.5px; color: var(--danger)">
          {{ String(previewError).slice(0, 90) }}
        </span>
        <span v-else></span>
        <div class="flex gap-2">
          <button class="lbtn" @click="$emit('close')">Cancel</button>
          <button class="lbtn primary" :disabled="!canSave" @click="save">
            {{ editing ? 'Update widget' : 'Add to dashboard' }}
          </button>
        </div>
      </div>
    </template>
  </Modal>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { call, createResource } from 'frappe-ui'
import Modal from '@/components/builder/Modal.vue'
import ChartBody from '@/components/widgets/ChartBody.vue'
import TableBody from '@/components/widgets/TableBody.vue'
import NumberBody from '@/components/widgets/NumberBody.vue'

const props = defineProps({
  widget: { type: Object, default: null },
})
const emit = defineEmits(['close', 'save'])

const editing = computed(() => !!props.widget)

const WIDGET_TYPES = [
  { label: 'Number', value: 'Number Card' },
  { label: 'Bar', value: 'Bar Chart' },
  { label: 'Line', value: 'Line Chart' },
  { label: 'Area', value: 'Area Chart' },
  { label: 'Donut', value: 'Donut Chart' },
  { label: 'Pie', value: 'Pie Chart' },
  { label: 'Table', value: 'Table' },
]

// ---- reconstruct initial state (supports editing a saved widget) ----
const q = props.widget?.query || {}
const isLine = !!q.parent_doctype

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
  title: props.widget?.title || '',
  doctype: isLine ? q.parent_doctype : q.doctype || '',
  grain: isLine ? 'line' : 'document',
  line_table: isLine ? q.doctype : '',
  widget_type: props.widget?.widget_type || 'Bar Chart',
  aggregate_function: q.aggregate?.function || 'count',
  aggregate_field: q.aggregate?.field || '',
  group_key: groupKeyFromQuery(q),
  time_grain: q.group_by?.time_grain || 'month',
  tint: props.widget?.style?.tint || 'blue',
  columns: columnKeysFromQuery(q),
  sort_field: q.sort ? groupKeyFromQuery({ group_by: q.sort }) : 'modified',
  sort_order: q.sort?.order || 'desc',
  limit: q.limit || 10,
  filters: (q.filters || []).filter((f) => typeof f[0] === 'string').map((f) => [...f]),
})

// filters the wizard doesn't render (base scoping like company/docstatus via a
// related ref) — preserved verbatim so editing a widget never drops them
const preservedFilters = ref((q.filters || []).filter((f) => typeof f?.[0] !== 'string'))

const doctypes = createResource({ url: 'lumen_reports.api.get_doctypes', auto: true })
const docFields = createResource({ url: 'lumen_reports.api.get_doctype_fields' })
const lineFields = createResource({ url: 'lumen_reports.api.get_doctype_fields' })

// fetch document-grain fields when the source changes
watch(
  () => form.doctype,
  (dt) => {
    if (dt) docFields.fetch({ doctype: dt })
  },
  { immediate: true }
)

const lineTables = computed(() => docFields.data?.line_item_tables || [])

// auto-pick a line table, and (re)fetch line-grain fields
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

const effectiveFields = computed(() =>
  form.grain === 'line' ? lineFields.data : docFields.data
)
const effectiveBase = computed(() => (form.grain === 'line' ? form.line_table : form.doctype))

// ---- field option lists ----
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

// columns: own fields + related (both selectable as table columns)
const columnFields = computed(() => {
  const own = ownFields.value.map((f) => ({
    key: `own:${f.fieldname}`,
    label: f.label,
    fieldtype: f.fieldtype,
  }))
  const related = (effectiveFields.value?.related_fields || []).map((r) => ({
    key: r.key,
    label: r.label,
    fieldtype: r.fieldtype,
  }))
  return [...own, ...related]
})

// ---- grain / source change handlers ----
function onDoctypeChange() {
  form.grain = 'document'
  form.line_table = ''
  form.group_key = ''
  form.aggregate_field = ''
  form.columns = ['own:name']
  preservedFilters.value = [] // base changed → old scoping no longer valid
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

// ---- query construction ----
function keyToRef(key) {
  // "own:fieldname" -> "fieldname"; "link>Doctype.field" -> {field, via}
  if (key.startsWith('own:')) return key.slice(4)
  const [linkPart, rest] = key.split('>')
  const dot = rest.lastIndexOf('.')
  const doctype = rest.slice(0, dot)
  const field = rest.slice(dot + 1)
  return { field, via: { link_field: linkPart, doctype } }
}

const needsGroup = computed(
  () => form.widget_type !== 'Number Card' && form.widget_type !== 'Table'
)

const canPreview = computed(() => {
  if (!effectiveBase.value) return false
  if (!effectiveFields.value) return false
  if (needsGroup.value) return !!selectedGroup.value
  return true
})
const canSave = computed(() => canPreview.value && !!form.title)

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

  if (needsGroup.value && selectedGroup.value) {
    const ref = selectedGroup.value.ref
    query.group_by = typeof ref === 'string' ? { field: ref } : { field: ref.field, via: ref.via }
    if (groupByIsDate.value) query.group_by.time_grain = form.time_grain
  }
  return query
}

// ---- live preview (debounced) ----
const preview = ref(null)
const previewError = ref(null)
const previewLoading = ref(false)
let previewTimer = null
let previewSeq = 0

watch(
  [form, effectiveFields],
  () => {
    if (!canPreview.value) {
      preview.value = null
      return
    }
    clearTimeout(previewTimer)
    previewTimer = setTimeout(runPreview, 450)
  },
  { deep: true, immediate: true }
)

async function runPreview() {
  const seq = ++previewSeq
  previewLoading.value = true
  previewError.value = null
  try {
    const result = await call('lumen_reports.api.preview_query', { query: buildQuery() })
    if (seq === previewSeq) preview.value = result
  } catch (e) {
    if (seq === previewSeq) previewError.value = e.messages?.[0] || e.message || e
  } finally {
    if (seq === previewSeq) previewLoading.value = false
  }
}

function save() {
  emit('save', {
    widget_id: props.widget?.widget_id,
    title: form.title,
    widget_type: form.widget_type,
    query: buildQuery(),
    style: form.widget_type === 'Number Card' ? { tint: form.tint } : {},
  })
}
</script>

<style scoped>
.wizard-mini {
  height: 32px;
  padding: 0 8px;
  border-radius: 8px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--ink);
  font-family: var(--font);
  font-size: 12.5px;
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
</style>
