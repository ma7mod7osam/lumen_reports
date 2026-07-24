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
          <div v-if="suggestions.length && !editWidget" class="flex flex-wrap items-center gap-2">
            <span class="mono" style="font-size: 10px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--faint)">Ideas</span>
            <button v-for="s in suggestions" :key="s" class="chip" @click="useSuggestion(s)">+ {{ s }}</button>
          </div>
          <p v-if="entries.some((e) => e.empty)" style="font-size: 12.5px; color: var(--muted)">
            Some widgets have <b>no data on this site yet</b> (no returns, nothing today, …). They're
            excluded by default — tick them to add anyway; they'll fill in when the data exists.
          </p>
          <div class="preview-grid">
            <div
              v-for="(entry, i) in entries"
              :key="i"
              class="pv-card"
              :class="[
                entry.widget.widget_type === 'Number Card' ? 'pv-kpi' : entry.widget.widget_type === 'Table' ? 'pv-table' : 'pv-chart',
                { 'pv-off': !entry.included },
              ]"
            >
              <button class="pv-toggle" :class="{ on: entry.included }" :title="entry.included ? 'Included — click to exclude' : 'Excluded — click to include'" @click="entry.included = !entry.included">
                <svg v-if="entry.included" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="m4.5 12.5 5 5 10-11" /></svg>
                <svg v-else width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
              </button>
              <span v-if="entry.empty" class="badge b-amber pv-empty"><span class="dot"></span>No data yet</span>
              <div v-if="entry.widget.widget_type === 'Number Card'" class="panel kpi" style="height: 100%">
                <NumberBody :result="entry.result" :label="entry.widget.title" :tint="entry.widget.style?.tint || 'blue'" />
              </div>
              <div v-else class="panel flex h-full flex-col">
                <div class="panel-h" style="padding: 11px 15px">
                  <div class="t" style="font-size: 13.5px">{{ entry.widget.title }}</div>
                </div>
                <div class="min-h-0 flex-1" style="padding: 12px 15px 14px">
                  <TableBody v-if="entry.widget.widget_type === 'Table'" :result="entry.result" />
                  <ChartBody v-else :widget-type="entry.widget.widget_type" :result="entry.result" :query="entry.widget.query" :accent="entry.widget.style?.accent || 0" />
                </div>
              </div>
              <ChartVariants v-if="entry.widget.widget_type !== 'Table'" :widget="entry.widget" :result="entry.result" default-tint="blue" />
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
          :disabled="!editWidget && includedCount === 0"
          @click="confirm"
        >
          {{ editWidget ? 'Apply change' : `Add ${includedCount} widget${includedCount === 1 ? '' : 's'}` }}
        </button>
      </div>
    </template>
  </Modal>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { call } from 'frappe-ui'
import Modal from '@/components/builder/Modal.vue'
import ChartBody from '@/components/widgets/ChartBody.vue'
import ChartVariants from '@/components/widgets/ChartVariants.vue'
import TableBody from '@/components/widgets/TableBody.vue'
import NumberBody from '@/components/widgets/NumberBody.vue'

const props = defineProps({
  // when set, the modal modifies this widget config instead of adding new ones
  editWidget: { type: Object, default: null },
  // titles already on the dashboard draft, so the AI extends instead of repeating
  existingTitles: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'add', 'apply'])

const status = ref(null)
const prompt = ref('')
const loading = ref(false)
const error = ref(null)
const clarify = ref(null)
const entries = ref([]) // [{widget, result, empty, included}]
const explanation = ref('')
const suggestions = ref([])

const includedCount = computed(() => entries.value.filter((e) => e.included).length)

function useSuggestion(s) {
  prompt.value = s
  generate()
}

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
      const answer = await call('lumen_reports.ai.ask_ai', {
        prompt: prompt.value,
        existing_titles: props.existingTitles,
      })
      if (answer.clarify) {
        clarify.value = answer.clarify
        return
      }
      // empty widgets stay visible but excluded by default — the user decides
      entries.value = (answer.widgets || []).map((e) => ({ ...e, included: !e.empty }))
      explanation.value = answer.explanation || ''
      suggestions.value = answer.suggestions || []
    }
  } catch (e) {
    error.value = e.messages?.[0] || e.message || String(e)
  } finally {
    loading.value = false
  }
}

function confirm() {
  if (props.editWidget) emit('apply', entries.value[0].widget)
  else emit('add', entries.value.filter((e) => e.included).map((entry) => entry.widget))
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
  height: 286px;
}
.pv-table {
  grid-column: span 12;
  min-height: 220px;
  max-height: 300px;
}
.pv-card {
  position: relative;
  display: flex;
  flex-direction: column;
}
.pv-card > .panel {
  flex: 1;
  min-height: 0;
}
.pv-card.pv-off > .panel {
  opacity: 0.45;
  filter: grayscale(0.4);
}
.pv-toggle {
  position: absolute;
  top: -7px;
  left: -7px;
  z-index: 5;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--faint);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow);
}
.pv-toggle.on {
  background: var(--blue);
  border-color: var(--blue);
  color: #fff;
}
.pv-empty {
  position: absolute;
  top: -8px;
  right: 8px;
  z-index: 5;
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
