<template>
  <Modal
    :title="editWidget ? 'Modify widget with AI' : 'Add widgets with AI'"
    :subtitle="editWidget ? `Editing “${editWidget.title}”` : 'Describe what you want — widgets are generated and validated against your data'"
    width="860px"
    @close="$emit('close')"
  >
    <div class="flex flex-col gap-4" style="padding: 18px">
      <!-- no key -->
      <div v-if="status && !status.configured" class="note">
        Ask AI needs a Gemini API key.
        <router-link to="/ask" style="color: var(--blue); font-weight: 700">Set one up on the Ask AI page</router-link>
        — there's a free-tier guide there.
      </div>

      <template v-else>
        <div class="flex items-center gap-2">
          <input
            type="text"
            v-model="prompt"
            :placeholder="editWidget ? 'e.g. \'make it a donut\' or \'only paid invoices\'' : 'e.g. \'average order value\' or \'monthly revenue + top customers\''"
            style="flex: 1; height: 40px; padding: 0 13px; border-radius: 10px; border: 1px solid var(--border-2); background: var(--panel); color: var(--ink); font-family: var(--font); font-size: 14px; outline: none; min-width: 0"
            @keydown.enter="generate"
          />
          <button class="lbtn primary" :disabled="loading || !prompt.trim()" @click="generate">
            {{ loading ? 'Thinking…' : 'Generate' }}
          </button>
        </div>

        <div v-if="loading" class="skel" style="height: 200px"></div>

        <div v-else-if="clarify" class="note">{{ clarify }}</div>

        <div v-else-if="error" class="panel err" style="padding: 14px">
          <div style="font-weight: 700">Couldn't do that</div>
          <p style="font-size: 12.5px; color: var(--muted); margin-top: 3px">{{ error }}</p>
        </div>

        <template v-else-if="entries.length">
          <p v-if="explanation" style="font-size: 12.5px; color: var(--muted)">{{ explanation }}</p>
          <p v-if="dropped.length" style="font-size: 12.5px; color: var(--muted)">
            Skipped (no data): {{ dropped.join(', ') }}
          </p>
          <div class="preview-grid">
            <div
              v-for="(entry, i) in entries"
              :key="i"
              :class="entry.widget.widget_type === 'Number Card' ? 'pv-kpi' : entry.widget.widget_type === 'Table' ? 'pv-table' : 'pv-chart'"
            >
              <div v-if="entry.widget.widget_type === 'Number Card'" class="panel kpi" style="height: 100%">
                <NumberBody :result="entry.result" :label="entry.widget.title" :tint="entry.widget.style?.tint || 'blue'" />
              </div>
              <div v-else class="panel flex h-full flex-col">
                <div class="panel-h" style="padding: 11px 15px">
                  <div class="t" style="font-size: 13.5px">{{ entry.widget.title }}</div>
                </div>
                <div class="min-h-0 flex-1" style="padding: 12px 15px 14px">
                  <TableBody v-if="entry.widget.widget_type === 'Table'" :result="entry.result" />
                  <ChartBody v-else :widget-type="entry.widget.widget_type" :result="entry.result" />
                </div>
              </div>
            </div>
          </div>
        </template>
      </template>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <button class="lbtn" @click="$emit('close')">Cancel</button>
        <button
          v-if="entries.length"
          class="lbtn primary"
          @click="confirm"
        >
          {{ editWidget ? 'Apply change' : `Add ${entries.length} widget${entries.length > 1 ? 's' : ''}` }}
        </button>
      </div>
    </template>
  </Modal>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { call } from 'frappe-ui'
import Modal from '@/components/builder/Modal.vue'
import ChartBody from '@/components/widgets/ChartBody.vue'
import TableBody from '@/components/widgets/TableBody.vue'
import NumberBody from '@/components/widgets/NumberBody.vue'

const props = defineProps({
  // when set, the modal modifies this widget config instead of adding new ones
  editWidget: { type: Object, default: null },
})
const emit = defineEmits(['close', 'add', 'apply'])

const status = ref(null)
const prompt = ref('')
const loading = ref(false)
const error = ref(null)
const clarify = ref(null)
const entries = ref([]) // [{widget, result}]
const explanation = ref('')
const dropped = ref([])

onMounted(async () => {
  status.value = await call('lumen_reports.ai.get_ai_status')
})

async function generate() {
  if (!prompt.value.trim() || loading.value) return
  loading.value = true
  error.value = null
  clarify.value = null
  entries.value = []
  try {
    if (props.editWidget) {
      const entry = await call('lumen_reports.ai.modify_ai_widget', {
        prompt: prompt.value,
        widget: {
          title: props.editWidget.title,
          widget_type: props.editWidget.widget_type,
          query: props.editWidget.query,
          style: props.editWidget.style || {},
        },
      })
      entries.value = [entry]
      explanation.value = entry.explanation || ''
      dropped.value = []
    } else {
      const answer = await call('lumen_reports.ai.ask_ai', { prompt: prompt.value })
      if (answer.clarify) {
        clarify.value = answer.clarify
        return
      }
      entries.value = answer.widgets || []
      explanation.value = answer.explanation || ''
      dropped.value = answer.dropped || []
    }
  } catch (e) {
    error.value = e.messages?.[0] || e.message || String(e)
  } finally {
    loading.value = false
  }
}

function confirm() {
  if (props.editWidget) emit('apply', entries.value[0].widget)
  else emit('add', entries.value.map((entry) => entry.widget))
}
</script>

<style scoped>
.preview-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 12px;
  max-height: 420px;
  overflow-y: auto;
  padding-bottom: 2px;
}
.pv-kpi {
  grid-column: span 4;
  min-height: 116px;
}
.pv-chart {
  grid-column: span 6;
  height: 250px;
}
.pv-table {
  grid-column: span 12;
  min-height: 220px;
  max-height: 300px;
}
@media (max-width: 700px) {
  .pv-kpi {
    grid-column: span 6;
  }
  .pv-chart,
  .pv-table {
    grid-column: span 12;
  }
}
.note {
  padding: 13px 15px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--blue) 7%, var(--panel));
  border: 1px solid color-mix(in srgb, var(--blue) 20%, var(--border));
  font-size: 13.5px;
  color: var(--ink-2);
}
</style>
