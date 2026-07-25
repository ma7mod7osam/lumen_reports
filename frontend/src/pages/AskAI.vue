<template>
  <div class="mx-auto max-w-4xl px-6 py-10">
    <div class="mb-6">
      <div class="mono" style="font-size: 12.5px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--blue); display: inline-flex; align-items: center; gap: 9px">
        <span style="width: 20px; height: 2px; background: var(--blue); display: inline-block"></span>
        Ask AI
      </div>
      <div class="flex flex-wrap items-end justify-between gap-3">
        <h1 style="font-size: 30px; font-weight: 800; letter-spacing: -0.03em; margin-top: 8px">
          Ask your data anything
        </h1>
        <button v-if="status?.configured" class="lbtn sm" @click="showSettings = !showSettings">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1" /></svg>
          AI settings
        </button>
      </div>
      <p style="color: var(--muted); margin-top: 4px; font-size: 14.5px">
        Describe the report you want — the AI builds it with Lumen's report engine, using only data
        you're permitted to see. Keep it as a one-off answer or pin it to a dashboard.
      </p>
      <span v-if="status?.configured" class="badge b-blue mt-2" style="margin-top: 8px">
        <span class="dot"></span>
        {{ status.source === 'user' ? 'Using your personal key' : 'Using the site-wide shared key' }}
        · {{ status.model }}
      </span>
    </div>

    <!-- key setup -->
    <div v-if="status && (!status.configured || showSettings)" class="panel mb-6" style="padding: 18px">
      <div class="flex items-start gap-3">
        <div class="kpi-ic tint-blue" style="width: 38px; height: 38px; border-radius: 11px; display: flex; align-items: center; justify-content: center; flex: none">
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M21 2l-2 2m-7.6 7.6a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78Zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4" /></svg>
        </div>
        <div style="flex: 1; min-width: 0">
          <div style="font-weight: 700; font-size: 15px">
            {{ status.configured ? 'AI settings' : 'Connect a Gemini API key' }}
          </div>
          <p style="font-size: 13px; color: var(--muted); margin-top: 2px">
            The AI runs on a Google Gemini key — either your personal one (billed to your Google
            account, free tier is plenty) or a site-wide key shared by everyone. Keys are stored
            encrypted and never leave the server. A personal key always takes priority.
          </p>

          <!-- personal key -->
          <div class="mono mt-3" style="font-size: 10.5px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--faint)">
            Your personal key
            <span v-if="status.personal_configured" class="badge b-green" style="margin-left: 6px"><span class="dot"></span>set</span>
          </div>
          <div class="mt-2 flex flex-wrap items-end gap-2">
            <div class="lfield" style="flex: 1; min-width: 220px">
              <label>Gemini API key</label>
              <input
                type="password"
                v-model="keyInput"
                :placeholder="status.personal_configured ? '•••••••• (saved — paste to replace)' : 'AIza…'"
                autocomplete="off"
              />
            </div>
            <div class="lfield" style="width: 200px">
              <label>Model</label>
              <select v-model="modelInput">
                <option v-for="m in modelOptions" :key="m" :value="m">{{ m }}</option>
              </select>
            </div>
            <button class="lbtn primary" :disabled="savingKey || (!keyInput && !status.personal_configured)" @click="saveKey">
              {{ savingKey ? 'Saving…' : 'Save' }}
            </button>
            <button v-if="status.personal_configured" class="lbtn danger" @click="removeKey">Remove</button>
          </div>
          <p v-if="!status.personal_configured && status.site_configured" style="font-size: 12.5px; color: var(--muted); margin-top: 6px">
            You're covered by the site-wide key — add a personal key only if you want your own quota.
          </p>

          <!-- site-wide key (admins) -->
          <template v-if="status.is_admin">
            <div class="mono mt-4" style="font-size: 10.5px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--faint); border-top: 1px solid var(--border); padding-top: 14px">
              Site-wide key · shared by all users
              <span v-if="status.site_configured" class="badge b-green" style="margin-left: 6px"><span class="dot"></span>set</span>
            </div>
            <div class="mt-2 flex flex-wrap items-end gap-2">
              <div class="lfield" style="flex: 1; min-width: 220px">
                <label>Site Gemini API key</label>
                <input
                  type="password"
                  v-model="siteKeyInput"
                  :placeholder="status.site_configured ? '•••••••• (saved — paste to replace)' : 'AIza…'"
                  autocomplete="off"
                />
              </div>
              <div class="lfield" style="width: 200px">
                <label>Model</label>
                <select v-model="siteModelInput">
                  <option v-for="m in modelOptions" :key="m" :value="m">{{ m }}</option>
                </select>
              </div>
              <button class="lbtn primary" :disabled="savingSiteKey || (!siteKeyInput && !status.site_configured)" @click="saveSiteKey">
                {{ savingSiteKey ? 'Saving…' : 'Save' }}
              </button>
              <button v-if="status.site_configured" class="lbtn danger" @click="removeSiteKey">Remove</button>
            </div>
          </template>

          <!-- free tier guide -->
          <details class="mt-3" :open="!status.configured">
            <summary class="mono" style="font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--blue); cursor: pointer">
              How to get a free Gemini API key
            </summary>
            <ol style="font-size: 13px; color: var(--ink-2); margin: 8px 0 0; padding-left: 18px; line-height: 1.9">
              <li>Go to <b>aistudio.google.com/apikey</b> and sign in with any Google account.</li>
              <li>Click <b>Create API key</b> (pick "Create in new project" if asked).</li>
              <li>Copy the key that starts with <span class="mono">AIza…</span> and paste it above.</li>
              <li>Done — the free tier includes generous daily usage of Gemini Flash, no credit card needed.</li>
            </ol>
          </details>
        </div>
      </div>
    </div>

    <!-- ask box -->
    <div v-if="status?.configured" class="panel" style="padding: 14px">
      <div class="flex items-center gap-2">
        <input
          type="text"
          v-model="question"
          placeholder='e.g. "revenue by brand this year" or "top 10 unpaid invoices"'
          style="flex: 1; border: none; background: transparent; outline: none; font-family: var(--font); font-size: 15px; color: var(--ink); min-width: 0"
          @keydown.enter="ask"
        />
        <button class="lbtn primary" :disabled="asking || !question.trim()" @click="ask">
          <svg v-if="!asking" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="m5 12 14-7-5 14-2.5-6.5L5 12Z" /></svg>
          {{ asking ? 'Thinking…' : 'Ask' }}
        </button>
      </div>
    </div>

    <div v-if="status?.configured && !answer && !asking && !askError && !clarify" class="mt-3 flex flex-wrap gap-2">
      <button v-for="ex in EXAMPLES" :key="ex" class="chip" @click="question = ex; ask()">{{ ex }}</button>
    </div>

    <!-- states -->
    <div v-if="asking" class="panel mt-5" style="padding: 18px">
      <div class="flex items-center gap-3">
        <div class="skel" style="width: 34px; height: 34px; border-radius: 10px"></div>
        <div style="flex: 1">
          <div class="skel" style="height: 14px; width: 40%"></div>
          <div class="skel mt-2" style="height: 11px; width: 65%"></div>
        </div>
      </div>
      <div class="skel mt-4" style="height: 220px"></div>
      <p class="mono mt-3" style="font-size: 10.5px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--faint)">
        picking data → building the report → validating with your permissions
      </p>
    </div>

    <div v-else-if="clarify" class="panel mt-5" style="padding: 18px">
      <div class="flex items-start gap-3">
        <div class="ic tint-blue" style="width: 34px; height: 34px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex: none">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01" /><circle cx="12" cy="12" r="9.2" /></svg>
        </div>
        <div style="flex: 1; min-width: 0">
          <div style="font-weight: 700">{{ clarify.question }}</div>
          <div v-if="clarify.options?.length" class="mt-2 flex flex-wrap gap-2">
            <button v-for="opt in clarify.options" :key="opt" class="chip" @click="answerClarify(opt)">
              {{ opt }}
            </button>
          </div>
          <div class="mt-3 flex items-center gap-2">
            <input
              type="text"
              v-model="clarifyReply"
              placeholder="Type your answer…"
              style="flex: 1; height: 36px; padding: 0 12px; border-radius: 10px; border: 1px solid var(--border-2); background: var(--panel); color: var(--ink); font-family: var(--font); font-size: 13.5px; outline: none; min-width: 0"
              @keydown.enter="answerClarify(clarifyReply)"
            />
            <button class="lbtn sm primary" :disabled="!clarifyReply.trim()" @click="answerClarify(clarifyReply)">
              Answer
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="askError" class="panel err mt-5" style="padding: 18px">
      <div style="font-weight: 700; color: var(--ink)">Couldn't build that report</div>
      <p style="font-size: 13px; color: var(--muted); margin-top: 4px">{{ askError }}</p>
    </div>

    <!-- result -->
    <template v-else-if="answer">
      <div class="mt-5 mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 style="font-size: 19px; font-weight: 800; letter-spacing: -0.02em">{{ answer.title }}</h2>
          <p v-if="answer.explanation" style="font-size: 13px; color: var(--muted)">{{ answer.explanation }}</p>
        </div>
        <span class="badge b-amber"><span class="dot"></span>AI-generated · not saved yet</span>
      </div>
      <p v-if="answer.widgets.some((e) => e.empty)" style="font-size: 12.5px; color: var(--muted); margin-bottom: 8px">
        Widgets marked <b>No data yet</b> have nothing to show on this site right now — they're
        excluded from saving by default; click the circle to include them anyway.
      </p>

      <div class="ai-grid">
        <div
          v-for="(entry, i) in answer.widgets"
          :key="i"
          class="ai-card"
          :class="[
            entry.widget.widget_type === 'Number Card' ? 'ai-kpi' : entry.widget.widget_type === 'Table' ? 'ai-table' : 'ai-chart',
            { 'ai-off': !entry.included },
          ]"
        >
          <button class="ai-toggle" :class="{ on: entry.included }" :title="entry.included ? 'Included — click to exclude' : 'Excluded — click to include'" @click="entry.included = !entry.included">
            <svg v-if="entry.included" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="m4.5 12.5 5 5 10-11" /></svg>
            <svg v-else width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
          </button>
          <span v-if="entry.empty" class="badge b-amber ai-empty"><span class="dot"></span>No data yet</span>
          <div v-if="entry.widget.widget_type === 'Number Card'" class="panel kpi" style="height: 100%">
            <NumberBody :result="entry.result" :label="entry.widget.title" :tint="entry.widget.style?.tint || KPI_TINTS[kpiIndex(i) % 4]" />
          </div>
          <div v-else class="panel flex h-full flex-col">
            <div class="panel-h" style="padding: 13px 18px">
              <div class="t">{{ entry.widget.title }}</div>
            </div>
            <div class="min-h-0 flex-1" style="padding: 14px 18px 16px">
              <TableBody v-if="entry.widget.widget_type === 'Table'" :result="entry.result" />
              <ChartBody v-else :widget-type="entry.widget.widget_type" :result="entry.result" :query="entry.widget.query" :accent="entry.widget.style?.accent || 0" :target="entry.widget.style?.target ?? null" />
            </div>
          </div>
          <ChartVariants v-if="entry.widget.widget_type !== 'Table'" :widget="entry.widget" :result="entry.result" :default-tint="KPI_TINTS[kpiIndex(i) % 4]" />
        </div>
      </div>

      <!-- refine: follow-up input + AI suggestions -->
      <div class="panel mt-4" style="padding: 13px 16px">
        <div class="flex items-center gap-2">
          <input
            type="text"
            v-model="followUpText"
            placeholder="Refine or add more… e.g. 'also show returns' or 'split it by territory'"
            style="flex: 1; border: none; background: transparent; outline: none; font-family: var(--font); font-size: 14px; color: var(--ink); min-width: 0"
            @keydown.enter="followUp(followUpText)"
          />
          <button class="lbtn sm primary" :disabled="followingUp || !followUpText.trim()" @click="followUp(followUpText)">
            {{ followingUp ? 'Thinking…' : 'Add' }}
          </button>
        </div>
        <!-- assumptions the AI made: each is a complete instruction, so tapping sends it -->
        <div v-if="answer.questions?.length" class="mt-2 flex flex-wrap items-center gap-2">
          <span class="mono chip-label">Refine</span>
          <button
            v-for="q in answer.questions"
            :key="q"
            class="chip chip-q"
            :disabled="followingUp"
            :title="'Send: ' + q"
            @click="followUp(q)"
          >
            {{ q }}
          </button>
        </div>
        <div v-if="answer.suggestions?.length" class="mt-2 flex flex-wrap items-center gap-2">
          <span class="mono chip-label">Ideas</span>
          <button
            v-for="s in answer.suggestions"
            :key="s"
            class="chip"
            :disabled="followingUp"
            @click="followUp(s)"
          >
            + {{ s }}
          </button>
        </div>
        <p v-if="followUpError" style="font-size: 12.5px; color: var(--danger); margin-top: 6px">{{ followUpError }}</p>
      </div>

      <!-- actions -->
      <div class="panel mt-4" style="padding: 13px 16px">
        <div class="flex flex-wrap items-center gap-2">
          <span class="mono" style="font-size: 10.5px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--faint)">
            Keep it?
          </span>
          <input
            type="text"
            v-model="newDashTitle"
            placeholder="New dashboard name"
            class="lfield-mini"
            style="min-width: 190px"
          />
          <button class="lbtn sm primary" :disabled="!newDashTitle.trim() || !!pinning || includedCount === 0" @click="saveAsNew">
            {{ pinning === 'new' ? 'Creating…' : `Save as new dashboard (${includedCount})` }}
          </button>
          <span class="mono" style="font-size: 10px; color: var(--faint)">or</span>
          <select v-model="targetDashboard" class="lfield-mini">
            <option value="" disabled>Add all to existing…</option>
            <option v-for="d in dashboards" :key="d.route_slug" :value="d.route_slug">
              {{ d.dashboard_title }}
            </option>
          </select>
          <button class="lbtn sm" :disabled="!targetDashboard || !!pinning || includedCount === 0" @click="appendToExisting">
            {{ pinning === 'append' ? 'Adding…' : 'Add' }}
          </button>
          <router-link
            v-if="pinnedSlug"
            :to="{ name: 'DashboardView', params: { slug: pinnedSlug } }"
            class="badge b-green"
            style="text-decoration: none"
          >
            <span class="dot"></span> Saved — open dashboard
          </router-link>
          <span style="flex: 1"></span>
          <button class="lbtn sm" @click="reset">New question</button>
        </div>
        <p v-if="pinError" style="font-size: 12.5px; color: var(--danger); margin-top: 6px">{{ pinError }}</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { call } from 'frappe-ui'
import ChartBody from '@/components/widgets/ChartBody.vue'
import ChartVariants from '@/components/widgets/ChartVariants.vue'
import TableBody from '@/components/widgets/TableBody.vue'
import NumberBody from '@/components/widgets/NumberBody.vue'

const EXAMPLES = [
  'Revenue by brand',
  'Monthly sales this year',
  'Top customers by revenue',
  'Unpaid invoices',
]

const status = ref(null)
const showSettings = ref(false)
const keyInput = ref('')
const modelInput = ref('gemini-2.5-flash')
const savingKey = ref(false)
const siteKeyInput = ref('')
const siteModelInput = ref('gemini-flash-latest')
const savingSiteKey = ref(false)
// floating aliases never rot; the real list loads from the API once a key exists
const modelOptions = ref(['gemini-flash-latest', 'gemini-pro-latest'])

// keep defaults sane if a stored model is stale/deprecated
const FALLBACK_MODEL = 'gemini-flash-latest'

const question = ref('')
const asking = ref(false)
const answer = ref(null)
const askError = ref(null)
const clarify = ref(null) // {question, options[]}
const clarifyReply = ref('')
const history = ref([]) // running conversation: [{role, text}]
const followUpText = ref('')
const followingUp = ref(false)
const followUpError = ref('')

const dashboards = ref([])
const targetDashboard = ref('')
const newDashTitle = ref('')
const pinning = ref('') // '' | 'new' | 'append'
const pinnedSlug = ref('')
const pinError = ref('')

const KPI_TINTS = ['blue', 'green', 'amber', 'violet']
const includedCount = computed(() => (answer.value?.widgets || []).filter((w) => w.included).length)
// tint counts only KPI cards so the rotation matches the saved dashboard
function kpiIndex(i) {
  let n = 0
  for (let j = 0; j < i; j++) {
    if (answer.value.widgets[j].widget.widget_type === 'Number Card') n++
  }
  return n
}

onMounted(async () => {
  applyStatus(await call('lumen_reports.ai.get_ai_status'))
  const list = await call('lumen_reports.api.get_dashboards')
  dashboards.value = list.dashboards || []
})

function applyStatus(next) {
  status.value = next
  modelInput.value = next.personal_model || FALLBACK_MODEL
  siteModelInput.value = next.site_model || FALLBACK_MODEL
  if (next.configured) loadModels()
}

let modelsLoaded = false
async function loadModels() {
  if (modelsLoaded) return
  modelsLoaded = true
  try {
    const models = await call('lumen_reports.ai.list_models')
    if (models?.length) {
      modelOptions.value = models
      // stored model may be deprecated / missing from the live list — keep it
      // selectable so the user sees what's set, but the list guides them
      for (const current of [modelInput.value, siteModelInput.value]) {
        if (current && !models.includes(current)) modelOptions.value.push(current)
      }
    }
  } catch {
    /* keep the alias fallbacks */
  }
}

async function saveKey() {
  savingKey.value = true
  try {
    applyStatus(
      await call('lumen_reports.ai.save_ai_settings', {
        api_key: keyInput.value || null,
        model: modelInput.value,
      })
    )
    keyInput.value = ''
    showSettings.value = false
  } catch (e) {
    alert(e.messages?.[0] || e.message || e)
  } finally {
    savingKey.value = false
  }
}

async function removeKey() {
  applyStatus(await call('lumen_reports.ai.clear_ai_key'))
}

async function saveSiteKey() {
  savingSiteKey.value = true
  try {
    applyStatus(
      await call('lumen_reports.ai.save_site_ai_settings', {
        api_key: siteKeyInput.value || null,
        model: siteModelInput.value,
      })
    )
    siteKeyInput.value = ''
    showSettings.value = false
  } catch (e) {
    alert(e.messages?.[0] || e.message || e)
  } finally {
    savingSiteKey.value = false
  }
}

async function removeSiteKey() {
  applyStatus(await call('lumen_reports.ai.clear_site_ai_key'))
}

async function ask(promptText = null, isAnswer = false) {
  // guard: template @click passes the event object, not a string
  const text = (typeof promptText === 'string' ? promptText : question.value).trim()
  if (!text || asking.value) return
  asking.value = true
  answer.value = null
  askError.value = null
  clarify.value = null
  clarifyReply.value = ''
  pinnedSlug.value = ''
  pinError.value = ''
  try {
    const response = await call('lumen_reports.ai.ask_ai', {
      prompt: text,
      history: history.value,
      answered: isAnswer, // a reply must produce a report, not another question
    })
    history.value.push({ role: 'user', text })
    if (response.clarify) {
      clarify.value = { question: response.clarify, options: response.options || [] }
      history.value.push({ role: 'assistant', text: response.clarify })
    } else {
      response.widgets = (response.widgets || []).map((e) => ({ ...e, included: !e.empty }))
      answer.value = response
      newDashTitle.value = response.title || ''
      history.value.push({ role: 'assistant', text: `Built: ${response.title}` })
    }
  } catch (e) {
    askError.value = e.messages?.[0] || e.message || String(e)
  } finally {
    asking.value = false
  }
}

function answerClarify(reply) {
  const text = (reply || '').trim()
  if (!text) return
  ask(text, true) // history already carries the question; the reply becomes the next turn
}

// follow-ups APPEND widgets to the current board instead of replacing it
async function followUp(text) {
  text = (text || '').trim()
  if (!text || followingUp.value) return
  followingUp.value = true
  followUpError.value = ''
  try {
    const response = await call('lumen_reports.ai.ask_ai', {
      prompt: text,
      history: history.value,
      existing_titles: answer.value.widgets.map((w) => w.widget.title),
    })
    history.value.push({ role: 'user', text })
    if (response.clarify) {
      followUpError.value = response.clarify
      history.value.push({ role: 'assistant', text: response.clarify })
      return
    }
    history.value.push({ role: 'assistant', text: `Added: ${response.title}` })
    // append, skipping widgets we already have (by title + query identity)
    const seen = new Set(answer.value.widgets.map((w) => w.widget.title + JSON.stringify(w.widget.query)))
    for (const entry of response.widgets || []) {
      const key = entry.widget.title + JSON.stringify(entry.widget.query)
      if (!seen.has(key)) {
        answer.value.widgets.push({ ...entry, included: !entry.empty })
        seen.add(key)
      }
    }
    answer.value.suggestions = response.suggestions || []
    answer.value.questions = response.questions || []
    followUpText.value = ''
    pinnedSlug.value = '' // board changed since last save
  } catch (e) {
    followUpError.value = e.messages?.[0] || e.message || String(e)
  } finally {
    followingUp.value = false
  }
}

async function saveResult(payload, mode) {
  pinning.value = mode
  pinError.value = ''
  try {
    const saved = await call('lumen_reports.ai.save_ai_result', payload)
    pinnedSlug.value = saved.slug
  } catch (e) {
    pinError.value = e.messages?.[0] || e.message || String(e)
  } finally {
    pinning.value = ''
  }
}

function includedWidgets() {
  return answer.value.widgets.filter((w) => w.included).map((w) => w.widget)
}

function saveAsNew() {
  saveResult({ widgets: includedWidgets(), title: newDashTitle.value }, 'new')
}

function appendToExisting() {
  saveResult({ widgets: includedWidgets(), slug: targetDashboard.value }, 'append')
}

function reset() {
  answer.value = null
  askError.value = null
  clarify.value = null
  clarifyReply.value = ''
  question.value = ''
  pinnedSlug.value = ''
  targetDashboard.value = ''
  newDashTitle.value = ''
  history.value = []
  followUpText.value = ''
  followUpError.value = ''
}
</script>

<style scoped>
.ai-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 14px;
}
.ai-kpi {
  grid-column: span 3;
  min-height: 128px;
  align-self: start; /* don't stretch to match a tall chart beside it */
}
.chip-label {
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--faint);
}
.chip-q {
  border-color: color-mix(in srgb, var(--blue) 28%, var(--border));
  background: color-mix(in srgb, var(--blue) 6%, var(--panel));
}
.chip-q:hover {
  border-color: var(--blue);
  color: var(--ink);
}
.ai-chart {
  grid-column: span 6;
  height: 366px;
}
.ai-table {
  grid-column: span 12;
  min-height: 300px;
  max-height: 430px;
}
.ai-card {
  position: relative;
  display: flex;
  flex-direction: column;
}
.ai-card > .panel {
  flex: 1;
  min-height: 0;
}
.ai-card.ai-off > .panel {
  opacity: 0.45;
  filter: grayscale(0.4);
}
.ai-toggle {
  position: absolute;
  top: -8px;
  left: -8px;
  z-index: 5;
  width: 24px;
  height: 24px;
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
.ai-toggle.on {
  background: var(--blue);
  border-color: var(--blue);
  color: #fff;
}
.ai-empty {
  position: absolute;
  top: -9px;
  right: 10px;
  z-index: 5;
}
@media (max-width: 900px) {
  .ai-kpi {
    grid-column: span 6;
  }
  .ai-chart,
  .ai-table {
    grid-column: span 12;
  }
}

.lfield-mini {
  height: 32px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--ink);
  font-family: var(--font);
  font-size: 12.5px;
  font-weight: 600;
  outline: none;
}
details summary::-webkit-details-marker {
  color: var(--blue);
}
</style>
