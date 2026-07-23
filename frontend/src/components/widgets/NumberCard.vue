<template>
  <div class="panel kpi" :class="{ err: !!error }">
    <template v-if="loading && !data">
      <div class="skel" style="height: 38px; width: 38px; border-radius: 11px"></div>
      <div>
        <div class="skel" style="height: 30px; width: 90px"></div>
        <div class="skel" style="height: 13px; width: 120px; margin-top: 8px"></div>
      </div>
    </template>
    <NumberBody v-else :result="data" :label="widget.title" :tint="tint" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import NumberBody from '@/components/widgets/NumberBody.vue'
import { useWidgetData } from '@/lib/useWidgetData'

const props = defineProps({
  slug: { type: String, required: true },
  widget: { type: Object, required: true },
  filterValues: { type: Object, default: () => ({}) },
  refreshKey: { type: Number, default: 0 },
  crossFilters: { type: Array, default: () => [] },
  index: { type: Number, default: 0 },
})

const { data, error, loading } = useWidgetData(props)

const TINTS = ['blue', 'green', 'amber', 'violet']
const tint = computed(() => props.widget.style?.tint || TINTS[props.index % TINTS.length])
</script>
