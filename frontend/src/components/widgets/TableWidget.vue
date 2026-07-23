<template>
  <WidgetCard
    :title="widget.title"
    :subtitle="widget.style?.subtitle"
    :loading="loading"
    :has-data="!!data"
    :error="error"
  >
    <template #actions>
      <button class="xbtn" title="Download CSV" @click="exportCsv">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M12 3v12m0 0 4-4m-4 4-4-4" />
          <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
        </svg>
      </button>
    </template>
    <TableBody :result="data" />
  </WidgetCard>
</template>

<script setup>
import WidgetCard from '@/components/WidgetCard.vue'
import TableBody from '@/components/widgets/TableBody.vue'
import { useWidgetData } from '@/lib/useWidgetData'
import { resultToCsv, downloadFile } from '@/lib/csv'

const props = defineProps({
  slug: { type: String, required: true },
  widget: { type: Object, required: true },
  filterValues: { type: Object, default: () => ({}) },
  refreshKey: { type: Number, default: 0 },
  crossFilters: { type: Array, default: () => [] },
  index: { type: Number, default: 0 },
})

const { data, error, loading } = useWidgetData(props)

function exportCsv() {
  const csv = resultToCsv(data.value)
  if (csv) {
    const base = (props.widget.title || 'table').toLowerCase().replace(/[^a-z0-9]+/g, '-')
    downloadFile(`${base}.csv`, csv)
  }
}
</script>

<style scoped>
.xbtn {
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
}
.xbtn:hover {
  background: var(--panel-2);
  color: var(--ink);
}
</style>
