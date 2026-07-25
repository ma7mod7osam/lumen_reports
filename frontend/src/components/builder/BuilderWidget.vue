<template>
  <!-- renders a widget from its query via preview_query (works for unsaved widgets) -->
  <div v-if="widget.widget_type === 'Number Card'" class="panel kpi" :class="{ err: !!error }">
    <template v-if="loading && !result">
      <div class="skel" style="height: 38px; width: 38px; border-radius: 11px"></div>
      <div>
        <div class="skel" style="height: 30px; width: 90px"></div>
        <div class="skel" style="height: 13px; width: 120px; margin-top: 8px"></div>
      </div>
    </template>
    <NumberBody v-else :result="result" :label="widget.title" :tint="widget.style?.tint || 'blue'" />
  </div>

  <WidgetCard
    v-else
    :title="widget.title"
    :loading="loading"
    :has-data="!!result"
    :error="error"
  >
    <TableBody v-if="widget.widget_type === 'Table'" :result="result" />
    <ChartBody v-else :widget-type="widget.widget_type" :result="result" :query="widget.query" :accent="widget.style?.accent || 0" :target="widget.style?.target ?? null" />
  </WidgetCard>
</template>

<script setup>
import { ref, watch } from 'vue'
import { call } from 'frappe-ui'
import WidgetCard from '@/components/WidgetCard.vue'
import ChartBody from '@/components/widgets/ChartBody.vue'
import TableBody from '@/components/widgets/TableBody.vue'
import NumberBody from '@/components/widgets/NumberBody.vue'

const props = defineProps({
  widget: { type: Object, required: true },
})

const result = ref(null)
const error = ref(null)
const loading = ref(true)
let seq = 0

watch(
  () => props.widget.query,
  async () => {
    const mySeq = ++seq
    loading.value = true
    error.value = null
    try {
      const r = await call('lumen_reports.api.preview_query', { query: props.widget.query })
      if (mySeq === seq) result.value = r
    } catch (e) {
      if (mySeq === seq) error.value = e
    } finally {
      if (mySeq === seq) loading.value = false
    }
  },
  { deep: true, immediate: true }
)
</script>
