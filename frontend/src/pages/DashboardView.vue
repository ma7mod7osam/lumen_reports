<template>
  <!-- the dashboard's own theme paints the page it lives on, so a board can
       look nothing like the one next to it -->
  <ThemeScope :theme="dashboard.data?.theme" paint class="page">
    <div class="mx-auto max-w-7xl px-6 py-8">
    <div v-if="dashboard.loading" class="flex flex-col gap-[18px]">
      <div class="skel" style="height: 34px; width: 280px"></div>
      <div class="skel" style="height: 40px; width: 60%; border-radius: 10px"></div>
      <div class="skel" style="height: 380px; border-radius: 16px"></div>
    </div>

    <template v-else-if="dashboard.data">
      <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <router-link to="/" class="mono back-link">
            <svg class="flip-rtl" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6" /></svg>
            {{ t('Dashboards') }}
          </router-link>
          <h1 style="font-size: 28px; font-weight: 800; letter-spacing: -0.03em; margin-top: 4px" dir="auto">
            {{ dashboard.data.title }}
          </h1>
        </div>
        <div class="flex items-center gap-3" style="padding-bottom: 4px">
          <span
            v-if="dashboard.data.auto_refresh"
            class="badge"
            :class="liveConnected ? 'b-green' : 'b-gray'"
            :title="liveConnected ? t('Widgets refresh automatically when data changes') : socketTimedOut ? t('Live updates are unavailable because the realtime server could not be reached. Data still loads normally.') : t('Connecting to live updates…')"
          >
            <span class="dot" :class="{ 'animate-pulse': liveConnected }"></span>
            {{ liveConnected ? t('Live') : socketTimedOut ? t('Offline') : t('Connecting…') }}
          </span>
          <router-link
            :to="{ name: 'DashboardReport', params: { slug }, query: reportQuery }"
            class="lbtn sm"
            style="text-decoration: none"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M6 9V3h12v6" /><rect x="3" y="9" width="18" height="8" rx="2" /><path d="M6 14h12v7H6z" />
            </svg>
            {{ t('Report') }}
          </router-link>
          <router-link
            v-if="dashboard.data.can_edit"
            :to="{ name: 'DashboardEdit', params: { slug } }"
            class="lbtn sm"
            style="text-decoration: none"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
            </svg>
            {{ t('Edit') }}
          </router-link>
        </div>
      </div>

      <div class="mb-[18px] flex flex-wrap items-center gap-3">
        <FilterBar
          v-if="dashboard.data.filters?.length"
          :filters="dashboard.data.filters"
          v-model="filterValues"
        />
        <button
          v-for="cf in activeCrossFilters"
          :key="cf.key"
          class="chip on"
          @click="removeCrossFilter(cf.key)"
        >
          {{ cf.field }}: {{ cf.value }}
          <span class="x">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round">
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </span>
        </button>
      </div>

      <div class="lumen-grid">
        <div
          v-for="(widget, i) in dashboard.data.widgets"
          :key="widget.widget_id"
          :class="widgetClass(widget)"
          :style="gridStyle(widget.widget_id)"
        >
          <StaticBody
            v-if="isStatic(widget.widget_type)"
            :widget-type="widget.widget_type"
            :style="widget.style || {}"
          />
          <NumberCard
            v-else-if="widget.widget_type === 'Number Card'"
            :slug="slug"
            :widget="widget"
            :filter-values="filterValues"
            :refresh-key="refreshKey"
            :cross-filters="crossFiltersFor(widget)"
            :index="i"
          />
          <TableWidget
            v-else-if="widget.widget_type === 'Table'"
            :slug="slug"
            :widget="widget"
            :filter-values="filterValues"
            :refresh-key="refreshKey"
            :cross-filters="crossFiltersFor(widget)"
            :index="i"
          />
          <ChartWidget
            v-else
            :slug="slug"
            :widget="widget"
            :filter-values="filterValues"
            :refresh-key="refreshKey"
            :cross-filters="crossFiltersFor(widget)"
            :index="i"
            @select="onCrossFilter"
          />
        </div>
      </div>
    </template>
    </div>
  </ThemeScope>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createResource } from 'frappe-ui'
import FilterBar from '@/components/FilterBar.vue'
import ThemeScope from '@/components/ThemeScope.vue'
import NumberCard from '@/components/widgets/NumberCard.vue'
import ChartWidget from '@/components/widgets/ChartWidget.vue'
import TableWidget from '@/components/widgets/TableWidget.vue'
import StaticBody from '@/components/widgets/StaticBody.vue'
import { isStatic } from '@/lib/widgetTypes'
import { getSocket } from '@/lib/socket'
import { t } from '@/lib/i18n'

const props = defineProps({ slug: { type: String, required: true } })

const filterValues = ref({})

// the report opens on the same filters the person is looking at
const reportQuery = computed(() => {
  const active = Object.fromEntries(
    Object.entries(filterValues.value || {}).filter(([, v]) => v !== '' && v !== null && v !== undefined)
  )
  return Object.keys(active).length ? { filters: JSON.stringify(active) } : {}
})
const refreshKey = ref(0)
const liveConnected = ref(false)
const socketTimedOut = ref(false) // "Connecting…" shouldn't lie forever
let socketTimeoutTimer = null
// multiple cross-filters at once, keyed by dimension so a new value within the
// same dimension replaces (you can't be two territories), but different
// dimensions accumulate (Open AND North), combined with AND like the filter bar
const crossFilters = ref({}) // dimKey -> {field, via, value, source_doctype, parent_doctype, sourceId}

function dimKey(cf) {
  return `${cf.via?.link_field || ''}.${cf.field}`
}

const activeCrossFilters = computed(() =>
  Object.entries(crossFilters.value).map(([key, cf]) => ({ ...cf, key }))
)

function onCrossFilter(next) {
  const key = dimKey(next)
  const copy = { ...crossFilters.value }
  // clicking the same segment again clears just that dimension
  if (copy[key] && String(copy[key].value) === String(next.value)) delete copy[key]
  else copy[key] = next
  crossFilters.value = copy
}

function removeCrossFilter(key) {
  const copy = { ...crossFilters.value }
  delete copy[key]
  crossFilters.value = copy
}

function crossFiltersFor(widget) {
  // every active cross-filter except ones sourced from this widget (so a chart
  // never filters itself out of view)
  return Object.values(crossFilters.value)
    .filter((cf) => cf.sourceId !== widget.widget_id)
    .map(({ field, via, value, source_doctype, parent_doctype }) => ({
      field,
      via,
      value,
      source_doctype,
      parent_doctype,
    }))
}

const dashboard = createResource({
  url: 'lumen_reports.api.get_dashboard',
  params: { slug: props.slug },
  auto: true,
})

const layoutById = computed(() => {
  const map = {}
  for (const item of dashboard.data?.layout || []) map[item.widget_id] = item
  return map
})

function gridStyle(widgetId) {
  const item = layoutById.value[widgetId]
  if (!item) return {}
  return {
    gridColumn: `${item.x + 1} / span ${item.w}`,
    gridRow: `${item.y + 1} / span ${item.h}`,
  }
}

// widget-type class drives the mobile layout (KPIs 2-up, charts/tables full width)
function widgetClass(widget) {
  if (isStatic(widget.widget_type)) return 'w-el'
  if (widget.widget_type === 'Number Card') return 'w-number'
  if (widget.widget_type === 'Table') return 'w-table'
  return 'w-chart'
}

let socket
let debounceTimer

// invalidation events are published to Frappe's per-doctype rooms (scoped, not
// site-wide), so the viewer joins the rooms for the doctypes its widgets use.
// Rooms are cheap: joining is a name, and the server re-checks read permission
// on every widget load regardless.
const subscribedDoctypes = new Set()
function subscribeDoctypes() {
  if (!socket) return
  const wanted = new Set()
  for (const w of dashboard.data?.widgets || []) {
    const q = w.query || {}
    if (q.doctype) wanted.add(q.doctype)
    if (q.parent_doctype) wanted.add(q.parent_doctype)
  }
  for (const dt of wanted) {
    if (!subscribedDoctypes.has(dt)) {
      socket.emit('doctype_subscribe', dt)
      subscribedDoctypes.add(dt)
    }
  }
}

onMounted(() => {
  socket = getSocket()
  socket.on('connect', () => {
    liveConnected.value = true
    socketTimedOut.value = false
    clearTimeout(socketTimeoutTimer)
    subscribedDoctypes.clear() // rooms don't survive a reconnect
    subscribeDoctypes()
  })
  socket.on('disconnect', () => (liveConnected.value = false))
  if (socket.connected) liveConnected.value = true
  else socketTimeoutTimer = setTimeout(() => (socketTimedOut.value = !socket?.connected), 10000)
  socket.on('lumen_reports:invalidate', onInvalidate)
})

// the dashboard definition arrives async — subscribe once its widgets are known
watch(() => dashboard.data, () => subscribeDoctypes())

onBeforeUnmount(() => {
  socket?.off('lumen_reports:invalidate', onInvalidate)
  for (const dt of subscribedDoctypes) socket?.emit('doctype_unsubscribe', dt)
  clearTimeout(debounceTimer)
  clearTimeout(socketTimeoutTimer)
})

function onInvalidate(message) {
  if (!dashboard.data?.auto_refresh) return
  if (!message?.dashboards?.includes(props.slug)) return
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => (refreshKey.value += 1), 800)
}
</script>

<style scoped>
.page {
  min-height: calc(100vh - 64px);
}
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  text-decoration: none;
}
.lumen-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 64px;
  gap: var(--grid-gap, 18px);
}

@media (max-width: 768px) {
  /* stack by widget type: KPIs two-up, charts and tables full width, and
     ignore the desktop grid placement so everything reads top-to-bottom */
  .lumen-grid {
    grid-template-columns: repeat(2, 1fr);
    grid-auto-rows: auto;
    gap: 14px;
  }
  .lumen-grid > * {
    grid-column: span 2 !important;
    grid-row: auto !important;
  }
  .lumen-grid > .w-number {
    grid-column: span 1 !important;
    min-height: 124px;
  }
  .lumen-grid > .w-chart {
    min-height: 280px;
  }
  .lumen-grid > .w-table {
    min-height: 340px;
  }
}
</style>
