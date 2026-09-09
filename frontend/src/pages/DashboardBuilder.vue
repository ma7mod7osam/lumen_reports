<template>
  <div class="studio">
    <!-- ===== studio toolbar ===== -->
    <div class="stoolbar">
      <button class="tbtn" title="Back" @click="exit">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6" /></svg>
      </button>
      <button class="stitle" title="Dashboard settings" @click="showSettings = true">
        <span>{{ settings.title || 'Untitled dashboard' }}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
      </button>
      <span v-if="settings.is_published" class="badge b-green"><span class="dot"></span>Published</span>
      <span v-else class="badge b-amber"><span class="dot"></span>Draft</span>

      <span class="grow"></span>

      <button class="tbtn" title="Undo (Ctrl+Z)" :disabled="!canUndo" @click="undo">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 14 4 9l5-5" /><path d="M4 9h10a6 6 0 0 1 0 12h-3" /></svg>
      </button>
      <button class="tbtn" title="Redo (Ctrl+Shift+Z)" :disabled="!canRedo" @click="redo">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 14 5-5-5-5" /><path d="M20 9H10a6 6 0 0 0 0 12h3" /></svg>
      </button>

      <span class="savestate" :class="saveTone">
        <svg v-if="saveTone === 'saved'" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="m4.5 12.5 5 5 10-11" /></svg>
        <svg v-else-if="saveTone === 'saving'" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9" opacity="0.3" /><path d="M21 12a9 9 0 0 0-9-9" /></svg>
        <svg v-else-if="saveTone === 'error'" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16.5v.01" /></svg>
        <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4" fill="currentColor" stroke="none" /></svg>
        {{ saveStateLabel }}
      </span>

      <span class="vsep"></span>

      <button class="lbtn" :class="{ on: showTheme }" @click="toggleThemePanel">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="13.5" cy="6.5" r="1.4" /><circle cx="17.5" cy="10.5" r="1.4" /><circle cx="6.5" cy="12.5" r="1.4" /><circle cx="8.5" cy="7.5" r="1.4" />
          <path d="M12 2a10 10 0 1 0 0 20c.9 0 1.6-.7 1.6-1.6 0-.4-.2-.8-.5-1.1-.3-.3-.4-.7-.4-1 0-.9.7-1.6 1.6-1.6H16a6 6 0 0 0 6-6c0-4.9-4.5-8.7-10-8.7Z" />
        </svg>
        Theme
      </button>
      <button class="lbtn" @click="showSettings = true">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" /></svg>
        Settings
      </button>
      <button class="lbtn" style="color: var(--blue); border-color: color-mix(in srgb, var(--blue) 35%, var(--border-2))" @click="openAi()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /><path d="M19 15l.9 2.6L22.5 18.5l-2.6.9L19 22l-.9-2.6-2.6-.9 2.6-.9L19 15Z" /></svg>
        Ask AI
      </button>
      <button v-if="settings.name" class="lbtn" @click="preview">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></svg>
        Preview
      </button>
      <button class="lbtn primary" :disabled="primaryDisabled" @click="primaryAction">
        {{ primaryLabel }}
      </button>
    </div>

    <div v-if="loadError" class="mx-auto max-w-3xl px-6 py-10">
      <div class="empty panel err">
        <div style="font-weight: 700; color: var(--ink)">Couldn't load dashboard</div>
        <div style="font-size: 12.5px">{{ loadError }}</div>
      </div>
    </div>

    <div v-else class="sbody">
      <!-- ===== insert rail ===== -->
      <div class="srail">
        <div class="rail-eyebrow">Charts</div>
        <div class="rail-grid">
          <button
            v-for="t in CHART_PALETTE"
            :key="t.value"
            class="rail-tile"
            :title="'Add ' + t.label"
            @click="addFromPalette(t.value, t.label)"
          >
            <ChartIcon :type="t.value" :size="16" />
            <span>{{ t.label }}</span>
          </button>
        </div>

        <div class="rail-eyebrow">Elements</div>
        <div class="rail-grid">
          <button
            v-for="t in ELEMENT_PALETTE"
            :key="t.value"
            class="rail-tile"
            :title="'Add ' + t.label"
            @click="addFromPalette(t.value, t.label)"
          >
            <ElementIcon :type="t.value" :size="16" />
            <span>{{ t.label }}</span>
          </button>
        </div>

        <button class="rail-ai" @click="openAi()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /></svg>
          Describe it instead
        </button>
      </div>

      <!-- ===== canvas ===== -->
      <ThemeScope :theme="settings.theme" paint class="scanvas" @pointerdown.self="deselect">
        <!-- empty state -->
        <div v-if="!widgets.length" class="empty panel" style="padding: 80px 20px; border-style: dashed" @pointerdown.stop>
          <div class="ic">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7.5" height="7.5" rx="2" /><rect x="13.5" y="3" width="7.5" height="7.5" rx="2" /><rect x="3" y="13.5" width="7.5" height="7.5" rx="2" /><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2" /></svg>
          </div>
          <div style="font-weight: 700; color: var(--ink)">An empty canvas</div>
          <div style="font-size: 12.5px; margin-bottom: 10px">Pick an element from the left rail, or describe the dashboard to the AI</div>
          <button class="lbtn primary" @click="openAi()">Ask AI to draft it</button>
        </div>

        <!-- edit grid -->
        <div v-else ref="gridEl" class="builder-grid" :style="gridBgStyle" @pointerdown.self="deselect">
          <div
            v-for="widget in widgets"
            :key="widget.widget_id"
            class="builder-item"
            :class="{ dragging: active?.id === widget.widget_id, selected: selectedId === widget.widget_id }"
            :style="itemStyle(widget.widget_id)"
          >
            <BuilderWidget :widget="widget" />
            <!-- edit overlay: click selects, drag moves -->
            <div class="overlay" @pointerdown="onWidgetPointerDown($event, widget.widget_id)">
              <div class="tools" @pointerdown.stop>
                <button class="tool" title="Modify with AI" style="color: var(--blue)" @click="openAi(widget)">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /></svg>
                </button>
                <button class="tool" title="Duplicate (Ctrl+D)" @click="duplicateWidget(widget)">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="12" height="12" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" /></svg>
                </button>
                <button class="tool danger" title="Remove (Del)" @click="removeWidget(widget.widget_id)">
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
      </ThemeScope>

      <!-- ===== inspector ===== -->
      <div v-if="showTheme" class="sinspector">
        <ThemePanel :theme="settings.theme" @apply="applyTheme" @close="showTheme = false" />
      </div>
      <div v-else-if="selectedWidget" class="sinspector">
        <WidgetInspector
          :widget="selectedWidget"
          @apply="applyInspector"
          @close="deselect"
        />
      </div>
    </div>
  </div>

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
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { call } from 'frappe-ui'
import BuilderWidget from '@/components/builder/BuilderWidget.vue'
import WidgetInspector from '@/components/builder/WidgetInspector.vue'
import SettingsModal from '@/components/builder/SettingsModal.vue'
import ThemePanel from '@/components/builder/ThemePanel.vue'
import AiAssist from '@/components/builder/AiAssist.vue'
import ChartIcon from '@/components/widgets/ChartIcon.vue'
import ElementIcon from '@/components/widgets/ElementIcon.vue'
import ThemeScope from '@/components/ThemeScope.vue'
import { CHART_PALETTE, ELEMENT_PALETTE, defaultSize, defaultStyle, isStatic } from '@/lib/widgetTypes'
import { DEFAULT_THEME } from '@/lib/dashboardTheme'

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
  visible_to_roles: [],
  visible_to_users: [],
  filters: [],
  theme: { ...DEFAULT_THEME },
})
const widgets = ref([])
const layout = reactive({}) // widget_id -> {x,y,w,h}
const fieldsByDoctype = reactive({}) // doctype -> fields payload
const loadError = ref(null)

const showSettings = ref(false)
const showTheme = ref(false)
const aiOpen = ref(false)
const aiWidget = ref(null)
const selectedId = ref(null)

const selectedWidget = computed(
  () => widgets.value.find((w) => w.widget_id === selectedId.value) || null
)

function widgetById(id) {
  return widgets.value.find((w) => w.widget_id === id) || null
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  if (isNew.value) {
    showSettings.value = true
    resetHistory()
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
    settings.visible_to_roles = d.visible_to_roles || []
    settings.visible_to_users = d.visible_to_users || []
    settings.filters = d.filters || []
    settings.theme = { ...DEFAULT_THEME, ...(d.theme || {}) }
    widgets.value = d.widgets
    for (const item of d.layout || []) {
      layout[item.widget_id] = { x: item.x, y: item.y, w: item.w, h: item.h }
    }
    widgets.value.forEach((w) => loadFields(w.query?.doctype))
    resetHistory()
    lastSaved.value = serialize()
    saveState.value = 'saved'
  } catch (e) {
    loadError.value = e.messages?.[0] || e.message || String(e)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  clearTimeout(autosaveTimer)
  clearTimeout(historyTimer)
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

// the doctype most of this board is built on — a new widget starts there
const dominantDoctype = computed(() => {
  const counts = {}
  for (const w of widgets.value) {
    const dt = w.query?.parent_doctype || w.query?.doctype
    if (dt) counts[dt] = (counts[dt] || 0) + 1
  }
  return Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0] || ''
})

function addFromPalette(type, label) {
  const id = 'w' + Math.random().toString(36).slice(2, 8)
  const element = isStatic(type)
  // a layout element carries content, not a query; a data widget starts on the
  // doctype the rest of the board already uses so it renders something at once
  const query = element || !dominantDoctype.value
    ? {}
    : { doctype: dominantDoctype.value, aggregate: { function: 'count' } }
  widgets.value.push({
    widget_id: id,
    title: label,
    widget_type: type,
    query,
    style: defaultStyle(type),
    linked_filters: {},
  })
  layout[id] = { x: 0, y: nextRow(), ...defaultSize(type) }
  selectedId.value = id
  showTheme.value = false
}

function applyInspector(config) {
  const w = selectedWidget.value
  if (!w) return
  // mutate in place so the inspector doesn't re-sync off its own change
  w.title = config.title
  w.widget_type = config.widget_type
  w.query = config.query
  w.style = config.style
  loadFields(config.query?.doctype)
}

function toggleThemePanel() {
  showTheme.value = !showTheme.value
  // the theme panel and the widget inspector share the dock, so opening one
  // puts the other away rather than fighting over the space
  if (showTheme.value) selectedId.value = null
}

function applyTheme(next) {
  Object.assign(settings.theme, next)
}

function openAi(widget = null) {
  aiWidget.value = widget
  aiOpen.value = true
}

function onAiAdd(configs) {
  aiOpen.value = false
  for (const config of configs) {
    const id = 'ai' + Math.random().toString(36).slice(2, 8)
    widgets.value.push({ ...config, widget_id: id, linked_filters: {} })
    layout[id] = { x: 0, y: nextRow(), ...defaultSize(config.widget_type) }
    loadFields(config.query?.parent_doctype || config.query?.doctype)
  }
}

function onAiApply(config) {
  aiOpen.value = false
  const i = widgets.value.findIndex((w) => w.widget_id === aiWidget.value.widget_id)
  if (i >= 0) {
    // replaced object -> the inspector re-syncs from the new reference
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
  selectedId.value = id
  showTheme.value = false
}

function removeWidget(widgetId) {
  widgets.value = widgets.value.filter((w) => w.widget_id !== widgetId)
  delete layout[widgetId]
  if (selectedId.value === widgetId) selectedId.value = null
}

function nextRow() {
  let max = 0
  for (const item of Object.values(layout)) max = Math.max(max, item.y + item.h)
  return max
}

function deselect() {
  selectedId.value = null
}

// ---------- keyboard ----------

function isTyping(event) {
  const el = event.target
  return (
    el &&
    (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable)
  )
}

function onKeydown(event) {
  if (aiOpen.value || showSettings.value) return
  if (showTheme.value && event.key !== 'Escape') return
  const mod = event.ctrlKey || event.metaKey
  if (mod && !event.shiftKey && event.key.toLowerCase() === 'z') {
    if (isTyping(event)) return
    event.preventDefault()
    undo()
  } else if ((mod && event.shiftKey && event.key.toLowerCase() === 'z') || (mod && event.key.toLowerCase() === 'y')) {
    if (isTyping(event)) return
    event.preventDefault()
    redo()
  } else if (mod && event.key.toLowerCase() === 'd' && selectedWidget.value) {
    if (isTyping(event)) return
    event.preventDefault()
    duplicateWidget(selectedWidget.value)
  } else if ((event.key === 'Delete' || event.key === 'Backspace') && selectedId.value) {
    if (isTyping(event)) return
    event.preventDefault()
    removeWidget(selectedId.value)
  } else if (event.key === 'Escape') {
    if (showTheme.value) showTheme.value = false
    else deselect()
  }
}

// ---------- undo / redo ----------

const history = ref([])
const histPointer = ref(-1)
let historyTimer = null

const canUndo = computed(() => histPointer.value > 0)
const canRedo = computed(() => histPointer.value < history.value.length - 1)

function serialize() {
  return JSON.stringify({
    widgets: widgets.value,
    layout,
    settings: {
      title: settings.title,
      description: settings.description,
      auto_refresh: settings.auto_refresh,
      is_published: settings.is_published,
      visible_to_roles: settings.visible_to_roles,
      visible_to_users: settings.visible_to_users,
      filters: settings.filters,
      theme: settings.theme,
    },
  })
}

function resetHistory() {
  history.value = [serialize()]
  histPointer.value = 0
}

function recordHistory() {
  const snapshot = serialize()
  if (snapshot === history.value[histPointer.value]) return
  history.value.splice(histPointer.value + 1)
  history.value.push(snapshot)
  if (history.value.length > 60) history.value.shift()
  histPointer.value = history.value.length - 1
}

function restore(snapshot) {
  const data = JSON.parse(snapshot)
  widgets.value = data.widgets
  for (const key of Object.keys(layout)) delete layout[key]
  Object.assign(layout, data.layout)
  Object.assign(settings, data.settings)
  if (selectedId.value && !widgets.value.some((w) => w.widget_id === selectedId.value)) {
    selectedId.value = null
  }
}

function undo() {
  if (!canUndo.value) return
  histPointer.value -= 1
  restore(history.value[histPointer.value])
}

function redo() {
  if (!canRedo.value) return
  histPointer.value += 1
  restore(history.value[histPointer.value])
}

// one watcher drives both history and autosave; a restore serializes back to
// the snapshot it landed on, so recordHistory() sees no change and skips
watch(
  [widgets, layout, settings],
  () => {
    clearTimeout(historyTimer)
    historyTimer = setTimeout(recordHistory, 550)
    queueAutosave()
  },
  { deep: true }
)

// ---------- grid drag & resize ----------

const gridEl = ref(null)
const active = ref(null) // {id, mode, startX, startY, orig, moved}

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

function onWidgetPointerDown(event, widgetId) {
  selectedId.value = widgetId
  showTheme.value = false // picking a widget hands the dock back to the inspector
  beginPointer(event, widgetId, 'move')
}

function startResize(event, widgetId) {
  selectedId.value = widgetId
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
    // a heading or a rule is allowed to be one row tall; a chart is not
    const minRows = isStatic(widgetById(a.id)?.widget_type) ? 1 : 2
    item.w = clamp(a.orig.w + dCols, 2, COLS - item.x)
    item.h = Math.max(minRows, a.orig.h + dRows)
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
  backgroundImage: 'radial-gradient(circle, var(--border-2) 1px, transparent 1px)',
  backgroundSize: `${cellWidth() + GAP}px ${ROW_H + GAP}px`,
  backgroundPosition: `-${GAP / 2}px -${GAP / 2}px`,
}))

// ---------- settings, save, autosave ----------

function onSettingsApply(next) {
  Object.assign(settings, next)
  showSettings.value = false
}

const saveState = ref('dirty') // saved | saving | dirty | error
const lastSaved = ref('')
let autosaveTimer = null
let saveSeq = 0

const dirty = computed(() => serialize() !== lastSaved.value)

// what the indicator actually shows. Undoing back to the saved state leaves
// saveState on 'dirty' while nothing differs any more, so the live comparison
// wins over the last thing that happened
const saveTone = computed(() => {
  if (saveState.value === 'saving' || saveState.value === 'error') return saveState.value
  return dirty.value ? 'dirty' : 'saved'
})

const saveStateLabel = computed(() => {
  if (saveTone.value === 'saving') return 'Saving…'
  if (saveTone.value === 'error') return 'Save failed'
  if (saveTone.value === 'saved') return 'Saved'
  return 'Unsaved changes'
})

const primaryLabel = computed(() => {
  if (!settings.name) return 'Save draft'
  if (!settings.is_published) return 'Publish'
  return 'Save changes'
})

const primaryDisabled = computed(() => {
  if (!settings.title) return true
  if (settings.is_published && settings.name) return !dirty.value && saveState.value !== 'error'
  return false
})

async function primaryAction() {
  if (settings.name && !settings.is_published) {
    settings.is_published = true
  }
  await persist()
}

function queueAutosave() {
  saveState.value = dirty.value ? 'dirty' : saveState.value
  // drafts save themselves; published dashboards wait for an explicit
  // "Save changes" so viewers never see a half-finished edit
  if (!settings.name || settings.is_published) return
  clearTimeout(autosaveTimer)
  autosaveTimer = setTimeout(() => {
    if (dirty.value) persist({ quiet: true })
  }, 1600)
}

function buildPayload() {
  return {
    name: settings.name,
    title: settings.title,
    slug: settings.slug,
    description: settings.description,
    auto_refresh: settings.auto_refresh,
    is_published: settings.is_published,
    visible_to_roles: settings.visible_to_roles || [],
    visible_to_users: settings.visible_to_users || [],
    filters: settings.filters.filter((f) => f.name),
    theme: settings.theme || {},
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
}

async function persist({ quiet = false } = {}) {
  const seq = ++saveSeq
  const snapshotAtSave = serialize()
  saveState.value = 'saving'
  try {
    const result = await call('lumen_reports.api.save_dashboard', { payload: buildPayload() })
    if (seq !== saveSeq) return
    settings.name = settings.name || result.name
    settings.slug = result.slug
    lastSaved.value = snapshotAtSave
    saveState.value = 'saved'
  } catch (e) {
    if (seq !== saveSeq) return
    saveState.value = 'error'
    if (!quiet) alert(e.messages?.[0] || e.message || e)
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
      applies = wbase === f.child_doctype || wbase === f.parent_doctype
    } else if (f.base_doctype) {
      applies = wbase === f.base_doctype || wparent === f.base_doctype
    } else {
      applies = fieldnames.has(f.fieldname || f.name) // legacy dashboards
    }
    if (applies) linked[f.name] = f.fieldname || f.name
  }
  return linked
}

function preview() {
  if (settings.slug) router.push({ name: 'DashboardView', params: { slug: settings.slug } })
}

function exit() {
  if (settings.slug && settings.name) {
    router.push({ name: 'DashboardView', params: { slug: settings.slug } })
  } else {
    router.push('/')
  }
}
</script>

<style scoped>
.studio {
  min-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
}
.stoolbar {
  position: sticky;
  top: 64px;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 54px;
  padding: 0 14px;
  background: color-mix(in srgb, var(--bg) 86%, transparent);
  backdrop-filter: saturate(160%) blur(14px);
  border-bottom: 1px solid var(--border);
}
.grow {
  flex: 1;
}
.vsep {
  width: 1px;
  height: 22px;
  background: var(--border-2);
  margin: 0 2px;
}
.tbtn {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tbtn:hover:not(:disabled) {
  background: var(--panel-2);
  color: var(--ink);
}
.tbtn:disabled {
  opacity: 0.35;
  cursor: default;
}
.stitle {
  display: flex;
  align-items: center;
  gap: 7px;
  border: none;
  background: transparent;
  color: var(--ink);
  font-family: var(--font);
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.02em;
  cursor: pointer;
  padding: 5px 9px;
  border-radius: 9px;
  max-width: 340px;
}
.stitle span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stitle svg {
  color: var(--faint);
  flex: none;
}
.stitle:hover {
  background: var(--panel-2);
}
.savestate {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  white-space: nowrap;
}
.savestate.saved {
  color: var(--success);
}
.savestate.error {
  color: var(--danger);
}
.savestate.saving svg {
  animation: spin 0.9s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.sbody {
  flex: 1;
  display: flex;
  align-items: flex-start;
  min-height: 0;
}
.srail {
  position: sticky;
  top: 118px;
  align-self: flex-start;
  width: 208px;
  flex: none;
  max-height: calc(100vh - 118px);
  overflow-y: auto;
  padding: 14px 12px 20px;
  border-right: 1px solid var(--border);
  background: var(--panel);
  min-height: calc(100vh - 118px);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rail-eyebrow {
  font-family: var(--mono);
  font-size: 9.5px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
  font-weight: 500;
}
.rail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px;
}
.rail-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 58px;
  border: 1px solid var(--border);
  border-radius: 11px;
  background: var(--panel);
  color: var(--ink-2);
  font-family: var(--font);
  font-size: 10.5px;
  font-weight: 600;
  cursor: pointer;
}
.rail-tile svg {
  opacity: 0.8;
}
.rail-tile:hover {
  border-color: var(--blue-300);
  color: var(--blue);
  background: color-mix(in srgb, var(--blue) 4%, var(--panel));
}
.rail-ai {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  height: 36px;
  border-radius: 10px;
  border: 1px dashed color-mix(in srgb, var(--blue) 45%, var(--border-2));
  background: color-mix(in srgb, var(--blue) 5%, var(--panel));
  color: var(--blue);
  font-family: var(--font);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.scanvas {
  flex: 1;
  min-width: 0;
  padding: 18px 20px 120px;
}
.sinspector {
  position: sticky;
  top: 118px;
  align-self: flex-start;
  width: 312px;
  flex: none;
  height: calc(100vh - 118px);
  border-left: 1px solid var(--border);
  background: var(--panel);
}

.builder-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 64px;
  gap: var(--grid-gap, 18px);
  border-radius: 16px;
}
.builder-item {
  position: relative;
  min-width: 0;
}
.builder-item.selected {
  z-index: 20;
}
.builder-item.selected > :first-child {
  outline: 2px solid var(--blue);
  outline-offset: 1px;
  border-radius: var(--panel-radius, 16px);
}

@media (max-width: 900px) {
  .srail {
    display: none;
  }
  .sinspector {
    position: fixed;
    right: 0;
    top: 64px;
    bottom: 0;
    height: auto;
    width: min(340px, 92vw);
    z-index: 60;
    box-shadow: var(--shadow-md);
  }
}
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
.overlay:hover .tools,
.builder-item.selected .tools {
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
