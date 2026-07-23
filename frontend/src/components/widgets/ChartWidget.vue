<template>
  <WidgetCard
    :title="widget.title"
    :subtitle="widget.style?.subtitle"
    :loading="loading"
    :has-data="!!data"
    :error="error"
  >
    <template #actions>
      <div class="flex gap-1">
        <button class="xbtn" title="Download image" @click="exportImage">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <rect x="3" y="3" width="18" height="18" rx="3" />
            <circle cx="9" cy="9" r="2" />
            <path d="m21 15-4.6-4.6L5 22" />
          </svg>
        </button>
        <button class="xbtn" title="Download CSV" @click="exportCsv">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M12 3v12m0 0 4-4m-4 4-4-4" />
            <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
          </svg>
        </button>
      </div>
    </template>
    <ChartBody
      ref="body"
      :widget-type="widget.widget_type"
      :result="data"
      :selectable="selectable"
      @select="onSelect"
    />
  </WidgetCard>
</template>

<script setup>
import { computed, ref } from 'vue'
import WidgetCard from '@/components/WidgetCard.vue'
import ChartBody from '@/components/widgets/ChartBody.vue'
import { useWidgetData } from '@/lib/useWidgetData'
import { resultToCsv, downloadFile, downloadDataUrl } from '@/lib/csv'

const props = defineProps({
  slug: { type: String, required: true },
  widget: { type: Object, required: true },
  filterValues: { type: Object, default: () => ({}) },
  refreshKey: { type: Number, default: 0 },
  crossFilters: { type: Array, default: () => [] },
  index: { type: Number, default: 0 },
})
const emit = defineEmits(['select'])

const { data, error, loading } = useWidgetData(props)
const body = ref(null)

// cross-filter source: categorical group-by only (no time buckets)
const selectable = computed(() => {
  const groupBy = props.widget.query?.group_by
  return !!groupBy?.field && !groupBy?.time_grain
})

function onSelect({ label }) {
  const gb = props.widget.query.group_by
  emit('select', {
    field: gb.field,
    via: gb.via || null,
    value: label,
    source_doctype: props.widget.query.doctype,
    parent_doctype: props.widget.query.parent_doctype || null,
    sourceId: props.widget.widget_id,
  })
}

function fileBase() {
  return (props.widget.title || 'widget').toLowerCase().replace(/[^a-z0-9]+/g, '-')
}

function exportCsv() {
  const csv = resultToCsv(data.value, props.widget.query?.group_by?.field || 'label')
  if (csv) downloadFile(`${fileBase()}.csv`, csv)
}

function exportImage() {
  const url = body.value?.getDataURL()
  if (url) downloadDataUrl(`${fileBase()}.svg`, url)
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
