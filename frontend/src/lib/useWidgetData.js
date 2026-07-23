import { ref, watch } from 'vue'
import { call } from 'frappe-ui'

/** Shared data-fetching for all widget components: runs the widget's saved
 * query, refetches when dashboard filters, cross-filters or the realtime
 * refresh key change. */
export function useWidgetData(props) {
  const data = ref(null)
  const error = ref(null)
  const loading = ref(true)

  let requestCounter = 0

  async function fetchData() {
    const requestId = ++requestCounter
    loading.value = data.value === null // keep stale data visible on refresh
    error.value = null
    try {
      const result = await call('lumen_reports.api.run_widget', {
        slug: props.slug,
        widget_id: props.widget.widget_id,
        filter_values: relevantFilters(),
        cross_filters: props.crossFilters || [],
      })
      if (requestId === requestCounter) data.value = result
    } catch (e) {
      if (requestId === requestCounter) error.value = e
    } finally {
      if (requestId === requestCounter) loading.value = false
    }
  }

  function relevantFilters() {
    const linked = props.widget.linked_filters || {}
    const values = {}
    for (const [name, value] of Object.entries(props.filterValues || {})) {
      if (name in linked) values[name] = value
    }
    return values
  }

  watch(
    () => [props.filterValues, props.refreshKey, props.crossFilters],
    () => fetchData(),
    { deep: true, immediate: true }
  )

  return { data, error, loading, refetch: fetchData }
}
