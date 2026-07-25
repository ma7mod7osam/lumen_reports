<template>
  <div class="mx-auto max-w-7xl px-6 py-8">
    <!-- builder top bar -->
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div>
        <span class="mono" style="font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--blue)">
          {{ isNew ? 'New dashboard' : 'Editing' }}
        </span>
        <h1 style="font-size: 26px; font-weight: 800; letter-spacing: -0.03em">
          {{ settings.title || 'Untitled dashboard' }}
        </h1>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button class="lbtn" @click="showSettings = true">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
          </svg>
          Settings
        </button>
        <button class="lbtn" @click="openWizard()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Add widget
        </button>
        <button class="lbtn" style="color: var(--blue); border-color: color-mix(in srgb, var(--blue) 35%, var(--border-2))" @click="openAi()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" />
            <path d="M19 15l.9 2.6L22.5 18.5l-2.6.9L19 22l-.9-2.6-2.6-.9 2.6-.9L19 15Z" />
          </svg>
          Ask AI
        </button>
        <span style="width: 1px; height: 24px; background: var(--border-2)"></span>
        <button class="lbtn" @click="cancel">Cancel</button>
        <button class="lbtn primary" :disabled="saving || !settings.title || !widgets.length" @click="save">
          {{ saving ? 'Saving…' : 'Save dashboard' }}
        </button>
      </div>
    </div>

    <div v-if="loadError" class="empty panel err">
      <div style="font-weight: 700; color: var(--ink)">Couldn't load dashboard</div>
      <div style="font-size: 12.5px">{{ loadError }}</div>
    </div>

    <!-- empty state -->
    <div v-else-if="!widgets.length" class="empty panel" style="padding: 80px 20px; border-style: dashed">
      <div class="ic">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="3" y="3" width="7.5" height="7.5" rx="2" />
          <rect x="13.5" y="3" width="7.5" height="7.5" rx="2" />
          <rect x="3" y="13.5" width="7.5" height="7.5" rx="2" />
          <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2" />
        </svg>
      </div>
      <div style="font-weight: 700; color: var(--ink)">No widgets yet</div>
      <div style="font-size: 12.5px; margin-bottom: 10px">Add your first widget to start composing</div>
      <button class="lbtn primary" @click="openWizard()">+ Add widget</button>
    </div>

    <!-- edit grid -->
    <div v-else ref="gridEl" class="builder-grid" :style="gridBgStyle">
      <div
        v-for="widget in widgets"
        :key="widget.widget_id"
        class="builder-item"
        :class="{ dragging: active?.id === widget.widget_id }"
        :style="itemStyle(widget.widget_id)"
      >
        <BuilderWidget :widget="widget" />
        <!-- edit overlay -->
        <div class="overlay" @pointerdown="startDrag($event, widget.widget_id)">
          <div class="tools" @pointerdown.stop>
            <button class="tool" title="Edit" @click="openWizard(widget)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" /></svg>
            </button>
            <button class="tool" title="Modify with AI" style="color: var(--blue)" @click="openAi(widget)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /></svg>
            </button>
            <button class="tool" title="Duplicate" @click="duplicateWidget(widget)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="12" height="12" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" /></svg>
            </button>
            <button class="tool danger" title="Remove" @click="removeWidget(widget.widget_id)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /></svg>
            </button>
          </div>
        </div>
        <!-- resize handle -->
        <div class="rz" @pointerdown.stop.prevent="startResize($event, widget.widget_id)">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><path d="M9 1v8H1z" opacity=".5" /></svg>
        </div>
      </div>
    </div>
  </div>

  <WidgetWizard
    v-if="wizardOpen"
    :widget="wizardWidget"
    @close="wizardOpen = false"
    @save="onWizardSave"
  />
  <AiAssist
    v-if="aiOpen"
    :edit-widget="aiWidget"
    :existing-titles="widgets.map((w) => w.title)"
    @close="aiOpen = false"
    @add="onAiAdd"
    @apply="onAiApply"
  />
  <SettingsModal
    v-if="showSettings"
    :settings="settings"
    :is-new="isNew"
    :filter-fields="filterFields"
    @close="showSettings = false"
    @apply="onSettingsApply"
  />
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { call } from 'frappe-ui'
import BuilderWidget from '@/components/builder/BuilderWidget.vue'
import WidgetWizard from '@/components/builder/WidgetWizard.vue'
import SettingsModal from '@/components/builder/SettingsModal.vue'
import AiAssist from '@/components/builder/AiAssist.vue'

const props = defineProps({ slug: { type: String, default: '' } })
const router = useRouter()
const isNew = computed(() => !props.slug)

const GAP = 18
const ROW_H = 64
const COLS = 12

const settings = reactive({
  name: null,
  title: '',
  slug: '',
  description: '',
  auto_refresh: true,
  is_published: false,
  filters: [],
})
const widgets = ref([])
const layout = reactive({}) // widget_id -> {x,y,w,h}
const fieldsByDoctype = reactive({}) // doctype -> fields payload
const loadError = ref(null)
const saving = ref(false)

const wizardOpen = ref(false)
const wizardWidget = ref(null)
const showSettings = ref(false)
const aiOpen = ref(false)
const aiWidget = ref(null)

onMounted(async () => {
  if (isNew.value) {
    showSettings.value = true
    return
  }
  try {
    const d = await call('lumen_reports.api.get_dashboard', { slug: props.slug })
    if (!d.can_edit) throw new Error('You do not have permission to edit this dashboard')
    settings.name = d.name
    settings.title = d.title
    settings.slug = d.slug
    settings.description = d.description || ''
    settings.auto_refresh = !!d.auto_refresh
    settings.is_published = !!d.is_published
    settings.filters = d.filters || []
    widgets.value = d.widgets
    for (const item of d.layout || []) {
      layout[item.widget_id] = { x: item.x, y: item.y, w: item.w, h: item.h }
    }
    widgets.value.forEach((w) => loadFields(w.query?.doctype))
  } catch (e) {
    loadError.value = e.messages?.[0] || e.message || String(e)
  }
})

async function loadFields(doctype) {
  if (!doctype || fieldsByDoctype[doctype]) return
  try {
    fieldsByDoctype[doctype] = await call('lumen_reports.api.get_doctype_fields', { doctype })
  } catch {
    /* non-fatal: filters editor just won't offer this doctype's fields */
  }
}

// union of filterable field descriptors across all widget doctypes
const filterFields = computed(() => {
  const seen = {}
  for (const w of widgets.value) {
    const meta = fieldsByDoctype[w.query?.doctype]
    if (!meta?.filter_fields) continue
    for (const f of meta.filter_fields) {
      if (!seen[f.key]) seen[f.key] = f
    }
  }
  return Object.values(seen)
})

// ---------- widget CRUD ----------

function openWizard(widget = null) {
  wizardWidget.value = widget
  wizardOpen.value = true
}

const DEFAULT_SIZES = {
  'Number Card': { w: 3, h: 2 },
  Table: { w: 12, h: 5 },
  Sparkline: { w: 3, h: 3 },
  Gauge: { w: 3, h: 3 },
  Rings: { w: 4, h: 4 },
  Radar: { w: 4, h: 5 },
  'Progress Bars': { w: 4, h: 4 },
  Heatmap: { w: 12, h: 5 },
  'Tree Report': { w: 12, h: 7 },
  default: { w: 6, h: 5 },
}

function onWizardSave(config) {
  wizardOpen.value = false
  loadFields(config.query.doctype)
  if (config.widget_id) {
    const i = widgets.value.findIndex((w) => w.widget_id === config.widget_id)
    if (i >= 0) widgets.value[i] = { ...widgets.value[i], ...config }
    return
  }
  const id = 'w' + Math.random().toString(36).slice(2, 8)
  const size = DEFAULT_SIZES[config.widget_type] || DEFAULT_SIZES.default
  widgets.value.push({ ...config, widget_id: id, linked_filters: {} })
  layout[id] = { x: 0, y: nextRow(), ...size }
}

function openAi(widget = null) {
  aiWidget.value = widget
  aiOpen.value = true
}

function onAiAdd(configs) {
  aiOpen.value = false
  for (const config of configs) {
    const id = 'ai' + Math.random().toString(36).slice(2, 8)
    const size = DEFAULT_SIZES[config.widget_type] || DEFAULT_SIZES.default
    widgets.value.push({ ...config, widget_id: id, linked_filters: {} })
    layout[id] = { x: 0, y: nextRow(), ...size }
    loadFields(config.query?.parent_doctype || config.query?.doctype)
  }
}

function onAiApply(config) {
  aiOpen.value = false
  const i = widgets.value.findIndex((w) => w.widget_id === aiWidget.value.widget_id)
  if (i >= 0) {
    // keep id, layout and linked filters; the AI only reshapes the data spec
    widgets.value[i] = { ...widgets.value[i], ...config }
    loadFields(config.query?.parent_doctype || config.query?.doctype)
  }
  aiWidget.value = null
}

function duplicateWidget(widget) {
  const id = 'w' + Math.random().toString(36).slice(2, 8)
  const source = layout[widget.widget_id] || { w: 6, h: 5 }
  widgets.value.push({ ...JSON.parse(JSON.stringify(widget)), widget_id: id })
  layout[id] = { x: source.x, y: nextRow(), w: source.w, h: source.h }
}

function removeWidget(widgetId) {
  widgets.value = widgets.value.filter((w) => w.widget_id !== widgetId)
  delete layout[widgetId]
}

function nextRow() {
  let max = 0
  for (const item of Object.values(layout)) max = Math.max(max, item.y + item.h)
  return max
}

// ---------- grid drag & resize ----------

const gridEl = ref(null)
const active = ref(null) // {id, mode, startX, startY, orig}

function cellWidth() {
  const width = gridEl.value?.clientWidth || 1180
  return (width - (COLS - 1) * GAP) / COLS
}

function itemStyle(widgetId) {
  const item = layout[widgetId]
  if (!item) return {}
  return {
    gridColumn: `${item.x + 1} / span ${item.w}`,
    gridRow: `${item.y + 1} / span ${item.h}`,
  }
}

function startDrag(event, widgetId) {
  beginPointer(event, widgetId, 'move')
}
function startResize(event, widgetId) {
  beginPointer(event, widgetId, 'resize')
}

function beginPointer(event, widgetId, mode) {
  const item = layout[widgetId]
  if (!item) return
  active.value = {
    id: widgetId,
    mode,
    startX: event.clientX,
    startY: event.clientY,
    orig: { ...item },
  }
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp, { once: true })
}

function onPointerMove(event) {
  const a = active.value
  if (!a) return
  const dCols = Math.round((event.clientX - a.startX) / (cellWidth() + GAP))
  const dRows = Math.round((event.clientY - a.startY) / (ROW_H + GAP))
  const item = layout[a.id]
  if (a.mode === 'move') {
    item.x = clamp(a.orig.x + dCols, 0, COLS - item.w)
    item.y = Math.max(0, a.orig.y + dRows)
  } else {
    item.w = clamp(a.orig.w + dCols, 2, COLS - item.x)
    item.h = Math.max(2, a.orig.h + dRows)
  }
}

function onPointerUp() {
  window.removeEventListener('pointermove', onPointerMove)
  active.value = null
}

function clamp(v, lo, hi) {
  return Math.min(Math.max(v, lo), hi)
}

const gridBgStyle = computed(() => ({
  backgroundImage:
    'radial-gradient(circle, var(--border-2) 1px, transparent 1px)',
  backgroundSize: `${cellWidth() + GAP}px ${ROW_H + GAP}px`,
  backgroundPosition: `-${GAP / 2}px -${GAP / 2}px`,
}))

// ---------- settings + save ----------

function onSettingsApply(next) {
  Object.assign(settings, next)
  showSettings.value = false
}

async function save() {
  saving.value = true
  try {
    const payload = {
      name: settings.name,
      title: settings.title,
      slug: settings.slug,
      description: settings.description,
      auto_refresh: settings.auto_refresh,
      is_published: settings.is_published,
      filters: settings.filters.filter((f) => f.name),
      widgets: widgets.value.map((w) => ({
        widget_id: w.widget_id,
        title: w.title,
        widget_type: w.widget_type,
        query: w.query,
        style: w.style || {},
        linked_filters: buildLinkedFilters(w),
      })),
      layout: widgets.value.map((w) => ({ widget_id: w.widget_id, ...layout[w.widget_id] })),
    }
    const result = await call('lumen_reports.api.save_dashboard', { payload })
    router.push({ name: 'DashboardView', params: { slug: result.slug } })
  } catch (e) {
    alert(e.messages?.[0] || e.message || e)
  } finally {
    saving.value = false
  }
}

function buildLinkedFilters(widget) {
  // a widget responds to a dashboard filter when the filter can be applied to
  // the widget's grain: same document, its parent document, or its line items
  const linked = {}
  const wbase = widget.query?.doctype
  const wparent = widget.query?.parent_doctype
  const meta = fieldsByDoctype[wbase]
  const fieldnames = new Set((meta?.fields || []).map((f) => f.fieldname))
  for (const f of settings.filters) {
    if (!f.name) continue
    let applies
    if (f.source === 'child') {
      // a line-item filter fits a line-grain widget (same child) or its parent
      applies = wbase === f.child_doctype || wbase === f.parent_doctype
    } else if (f.base_doctype) {
      // a document field fits that document, or a line widget built on it
      applies = wbase === f.base_doctype || wparent === f.base_doctype
    } else {
      applies = fieldnames.has(f.fieldname || f.name) // legacy dashboards
    }
    if (applies) linked[f.name] = f.fieldname || f.name
  }
  return linked
}

function cancel() {
  if (isNew.value) router.push('/')
  else router.push({ name: 'DashboardView', params: { slug: props.slug } })
}
</script>

<style scoped>
.builder-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 64px;
  gap: 18px;
  border-radius: 16px;
  padding-bottom: 120px;
}
.builder-item {
  position: relative;
  min-width: 0;
}

/* on phones the drag-grid can't lay out 12 columns; stack widgets so the page
   stays usable (add / edit / remove still work; precise drag-resize is desktop) */
@media (max-width: 768px) {
  .builder-grid {
    grid-template-columns: 1fr;
    grid-auto-rows: auto;
    gap: 14px;
  }
  .builder-item {
    grid-column: 1 / -1 !important;
    grid-row: auto !important;
    min-height: 200px;
  }
  .rz {
    display: none;
  }
}
.builder-item.dragging {
  z-index: 30;
  opacity: 0.85;
}
.overlay {
  position: absolute;
  inset: 0;
  border-radius: 16px;
  cursor: grab;
  border: 1.5px dashed transparent;
  transition: border-color 0.15s, background 0.15s;
}
.overlay:hover {
  border-color: var(--blue-300);
  background: color-mix(in srgb, var(--blue) 4%, transparent);
}
.builder-item.dragging .overlay {
  cursor: grabbing;
  border-color: var(--blue);
}
.tools {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}
.overlay:hover .tools {
  opacity: 1;
}
.tool {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow);
}
.tool:hover {
  color: var(--ink);
  border-color: var(--blue-300);
}
.tool.danger:hover {
  color: var(--danger);
  border-color: var(--danger);
}
.rz {
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--faint);
  cursor: nwse-resize;
  z-index: 5;
}
.rz:hover {
  color: var(--blue);
}
</style>
