<template>
  <div class="cp">
    <div class="cp-head">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 3v2M12 19v2M5.6 5.6 7 7M17 17l1.4 1.4M3 12h2M19 12h2M5.6 18.4 7 17M17 7l1.4-1.4" />
        <circle cx="12" cy="12" r="4" />
      </svg>
      <span class="cp-title">{{ t('Copilot') }}</span>
      <span class="grow"></span>
      <button class="x" :title="t('Close')" @click="$emit('close')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
      </button>
    </div>

    <!-- what "this" means right now -->
    <div class="scope">
      <template v-if="selected">
        <span class="scope-chip on" :title="selected.title">
          <span class="lbl">{{ t('Working on') }}</span>
          <b dir="auto">{{ selected.title || t(selected.widget_type) }}</b>
          <button :title="t('Work on the whole dashboard')" @click="$emit('clear-scope')">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
          </button>
        </span>
        <button class="linkish" @click="$emit('open-inspector')">{{ t('Settings') }}</button>
      </template>
      <span v-else class="scope-chip">
        <span class="lbl">{{ t('Working on') }}</span>
        <b>{{ t('the whole dashboard') }}</b>
      </span>
    </div>

    <div ref="threadEl" class="thread">
      <!-- no key yet -->
      <div v-if="status && !status.configured" class="setup">
        <div class="setup-t">{{ t('Connect an AI key first') }}</div>
        <p>{{ t('The copilot runs on Google Gemini with your own key. Add it once in AI settings and it works here and in Ask AI.') }}</p>
        <router-link to="/ask" class="lbtn primary sm" style="text-decoration: none">{{ t('Open AI settings') }}</router-link>
      </div>

      <!-- first open -->
      <div v-else-if="!messages.length" class="intro">
        <div class="intro-t">{{ t('Ask for any change to this dashboard') }}</div>
        <p>
          {{ t('Layout, colors, titles, new charts, a written summary. You see the list of changes first, and one click on Undo takes the whole thing back.') }}
        </p>
        <div class="chips">
          <button v-for="s in STARTERS" :key="s" class="chip-s" @click="send(t(s))">{{ t(s) }}</button>
        </div>
      </div>

      <template v-for="(m, i) in messages" :key="i">
        <div v-if="m.role === 'user'" class="bubble user" dir="auto">{{ m.text }}</div>

        <div v-else class="bubble bot" :class="{ failed: m.error }">
          <div v-if="m.error" class="err-t" dir="auto">{{ m.error }}</div>

          <template v-else-if="m.clarify">
            <div class="reply" dir="auto">{{ m.clarify }}</div>
            <div v-if="m.state === 'open'" class="chips">
              <button v-for="o in m.options" :key="o" class="chip-s" dir="auto" @click="answer(m, o)">{{ o }}</button>
            </div>
          </template>

          <template v-else>
            <div v-if="m.reply" class="reply" dir="auto">{{ m.reply }}</div>

            <ul v-if="m.changes?.length" class="changes" dir="auto">
              <li v-for="(c, ci) in m.changes" :key="ci">{{ c }}</li>
            </ul>

            <ul v-if="m.notes?.length" class="notes" dir="auto">
              <li v-for="(n, ni) in m.notes" :key="ni">{{ n }}</li>
            </ul>

            <div v-if="m.analysis" class="ana" dir="auto">
              <div class="ana-h">{{ m.analysis.headline }}</div>
              <ul>
                <li v-for="(f, fi) in m.analysis.findings" :key="fi">{{ f }}</li>
              </ul>
              <ul v-if="m.analysis.watch?.length" class="watch">
                <li v-for="(w, wi) in m.analysis.watch" :key="wi">{{ w }}</li>
              </ul>
            </div>

            <div v-if="m.proposal && m.state === 'proposed'" class="acts">
              <button class="lbtn primary sm" @click="apply(m)">{{ t('Apply ({0})', m.changes?.length || 0) }}</button>
              <button class="lbtn sm" @click="m.state = 'discarded'">{{ t('Discard') }}</button>
            </div>
            <div v-else-if="m.state === 'applied'" class="done">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2.6" stroke-linecap="round"><path d="m4.5 12.5 5 5 10-11" /></svg>
              {{ t('Applied ({0})', m.changes?.length || 0) }}
              <button v-if="m.pointer === historyPointer" class="linkish" @click="undoApply(m)">{{ t('Undo') }}</button>
            </div>
            <div v-else-if="m.state === 'discarded'" class="done muted">{{ t('Discarded, nothing changed') }}</div>
            <div v-else-if="m.state === 'undone'" class="done muted">{{ t('Undone, the board is back as it was') }}</div>
          </template>
        </div>
      </template>

      <div v-if="busy" class="bubble bot typing">
        <i></i><i></i><i></i>
        <span>{{ busyText }}</span>
      </div>

      <div v-if="suggestions.length && !busy" class="chips follow">
        <button v-for="s in suggestions" :key="s" class="chip-s" dir="auto" @click="send(s)">{{ s }}</button>
      </div>
    </div>

    <form class="composer" @submit.prevent="send()">
      <textarea
        ref="inputEl"
        v-model="draft"
        dir="auto"
        rows="2"
        :placeholder="selected ? t('What should change on this widget?') : t('Ask for any change to the dashboard…')"
        :disabled="busy || (status && !status.configured)"
        @keydown.enter.exact.prevent="send()"
      ></textarea>
      <button class="send" type="submit" :disabled="busy || !draft.trim()" :title="t('Send (Enter)')">
        <svg class="flip-rtl" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></svg>
      </button>
    </form>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { call } from 'frappe-ui'
import { t } from '@/lib/i18n'
import '@/components/builder/controls.css'

const props = defineProps({
  // returns the board exactly as the studio holds it, unsaved edits included
  getBoard: { type: Function, required: true },
  selected: { type: Object, default: null },
  // the studio's undo position, so an Undo link only shows while it would
  // take back exactly that batch and nothing the person did after it
  historyPointer: { type: Number, default: -1 },
})
const emit = defineEmits(['apply', 'undo', 'close', 'clear-scope', 'open-inspector'])

const STARTERS = [
  'Arrange this dashboard',
  'Add an executive summary at the top',
  'Switch to a dark theme',
  'What stands out in these numbers?',
]

const messages = ref([])
const draft = ref('')
const busy = ref(false)
const status = ref(null)
const threadEl = ref(null)
const inputEl = ref(null)
const busyText = ref('')

onMounted(async () => {
  try {
    status.value = await call('lumen_reports.ai.get_ai_status')
  } catch {
    status.value = { configured: true } // let the first request surface the real error
  }
  inputEl.value?.focus()
})

const suggestions = computed(() => {
  const last = [...messages.value].reverse().find((m) => m.role === 'assistant')
  return last?.suggestions || []
})

// what the model needs to resolve "that", "same again", "undo the colors"
function history() {
  return messages.value.slice(-10).map((m) => {
    if (m.role === 'user') return { role: 'user', text: m.text }
    const parts = [m.reply || m.clarify || m.error || '']
    if (m.changes?.length) parts.push('Changes: ' + m.changes.join('; '))
    if (m.state) parts.push('(' + m.state + ')')
    return { role: 'assistant', text: parts.filter(Boolean).join(' ') }
  })
}

// the slow part of a turn is building widgets or reading numbers; say so
function guessWork(text) {
  const lower = text.toLowerCase()
  if (/summary|summari|ملخص/.test(lower)) return t('Reading the numbers…')
  if (/add|chart|widget|compare|اضف|أضف|رسم|قارن/.test(lower)) return t('Building from your data…')
  return t('Working on it…')
}

async function send(text = null, { answered = false } = {}) {
  const prompt = (typeof text === 'string' ? text : draft.value).trim()
  if (!prompt || busy.value) return
  const past = history()
  messages.value.push({ role: 'user', text: prompt })
  if (typeof text !== 'string') draft.value = ''
  busy.value = true
  busyText.value = guessWork(prompt)
  scrollDown()
  try {
    const r = await call('lumen_reports.copilot.copilot', {
      prompt,
      board: props.getBoard(),
      history: past,
      selected: props.selected?.widget_id || null,
      answered,
    })
    if (r.clarify) {
      messages.value.push({ role: 'assistant', clarify: r.clarify, options: r.options || [], state: 'open' })
    } else {
      messages.value.push({
        role: 'assistant',
        reply: r.reply,
        changes: r.changes || [],
        notes: r.notes || [],
        analysis: r.analysis || null,
        suggestions: r.suggestions || [],
        proposal: r.proposal || null,
        state: r.proposal ? 'proposed' : null,
      })
    }
  } catch (e) {
    messages.value.push({ role: 'assistant', error: e.messages?.[0] || e.message || String(e) })
  } finally {
    busy.value = false
    scrollDown()
    nextTick(() => inputEl.value?.focus())
  }
}

function answer(m, option) {
  m.state = 'answered'
  send(option, { answered: true })
}

function apply(m) {
  // the studio applies the whole proposal as one history step and tells us
  // where that step landed, so the Undo link knows whether it is still safe
  emit('apply', m.proposal, (pointer) => {
    m.pointer = pointer
    m.state = 'applied'
  })
}

function undoApply(m) {
  emit('undo')
  m.state = 'undone'
}

function scrollDown() {
  nextTick(() => {
    const el = threadEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

watch(() => messages.value.length, scrollDown)
</script>

<style scoped>
.cp {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--panel);
}
.cp-head {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 13px 14px;
  border-bottom: 1px solid var(--border);
}
.cp-title {
  font-weight: 800;
  font-size: 14px;
  color: var(--ink);
}
.grow {
  flex: 1;
}
.x {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.x:hover {
  background: var(--panel-2);
  color: var(--ink);
}

.scope {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border-bottom: 1px solid var(--border);
  min-height: 42px;
}
.scope-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  min-width: 0;
  padding-block: 4px;
  padding-inline: 10px 6px;
  border-radius: 99px;
  background: var(--panel-2);
  font-size: 11.5px;
  color: var(--ink-2);
}
.scope-chip .lbl {
  color: var(--faint);
  white-space: nowrap;
}
.scope-chip b {
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-inline-end: 4px;
}
.scope-chip.on {
  background: color-mix(in srgb, var(--blue) 11%, var(--panel));
  color: var(--blue);
}
.scope-chip button {
  width: 18px;
  height: 18px;
  flex: none;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: currentColor;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.scope-chip button:hover {
  background: color-mix(in srgb, var(--blue) 18%, transparent);
}
.linkish {
  border: none;
  background: none;
  color: var(--blue);
  font-family: var(--font);
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
  white-space: nowrap;
}

.thread {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.intro,
.setup {
  padding: 6px 2px;
}
.intro-t,
.setup-t {
  font-size: 13.5px;
  font-weight: 800;
  color: var(--ink);
}
.intro p,
.setup p {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.55;
  margin: 5px 0 12px;
}

/* the app's tight letter-spacing would pull joined Arabic letters apart, and
   this panel is where Arabic is most likely to appear */
.thread,
.composer textarea {
  letter-spacing: 0;
}
.bubble {
  font-size: 12.5px;
  line-height: 1.6;
  border-radius: 13px;
  padding: 9px 12px;
  max-width: 94%;
  white-space: pre-wrap;
  word-break: break-word;
}
.bubble.user {
  align-self: flex-end;
  background: var(--blue);
  color: #fff;
  border-end-end-radius: 4px;
}
.bubble.bot {
  align-self: flex-start;
  width: 94%;
  background: var(--panel-2);
  border: 1px solid var(--border);
  color: var(--ink-2);
  border-end-start-radius: 4px;
}
.bubble.failed {
  border-color: color-mix(in srgb, var(--danger) 40%, var(--border));
}
.err-t {
  color: var(--danger);
  font-weight: 600;
}
.reply {
  color: var(--ink);
  font-weight: 600;
}
.changes,
.notes,
.ana ul {
  margin: 7px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.changes li,
.notes li,
.ana li {
  position: relative;
  padding-inline-start: 13px;
}
.changes li::before,
.ana li::before {
  content: '';
  position: absolute;
  inset-inline-start: 0;
  top: 8px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--blue);
}
.notes li {
  color: var(--warning);
  font-size: 11.5px;
}
.notes li::before {
  content: '!';
  position: absolute;
  inset-inline-start: 1px;
  font-weight: 800;
}
.ana {
  margin-top: 8px;
  padding: 9px 11px;
  border-inline-start: 3px solid var(--blue);
  background: var(--panel);
  border-radius: 8px;
}
.ana-h {
  font-weight: 700;
  color: var(--ink);
}
.ana .watch li::before {
  background: var(--warning);
}
.acts {
  display: flex;
  gap: 7px;
  margin-top: 10px;
}
.done {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 9px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--ink-2);
}
.done.muted {
  color: var(--faint);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chips.follow {
  margin-top: 2px;
}
.chip-s {
  padding: 6px 11px;
  border-radius: 99px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--ink-2);
  font-family: var(--font);
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  text-align: start;
}
.chip-s:hover {
  border-color: var(--blue-300);
  color: var(--blue);
}

.typing {
  display: flex;
  align-items: center;
  gap: 4px;
  width: auto;
  color: var(--muted);
}
.typing i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--faint);
  display: block;
  animation: blink 1.2s infinite ease-in-out;
}
.typing i:nth-child(2) {
  animation-delay: 0.15s;
}
.typing i:nth-child(3) {
  animation-delay: 0.3s;
}
.typing span {
  margin-inline-start: 6px;
  font-size: 11.5px;
}
@keyframes blink {
  0%,
  80%,
  100% {
    opacity: 0.25;
  }
  40% {
    opacity: 1;
  }
}

.composer {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 11px 12px;
  border-top: 1px solid var(--border);
}
.composer textarea {
  flex: 1;
  min-width: 0;
  resize: none;
  border: 1px solid var(--border-2);
  border-radius: 12px;
  padding: 9px 11px;
  font-family: var(--font);
  font-size: 13px;
  line-height: 1.45;
  color: var(--ink);
  background: var(--panel);
  outline: none;
  max-height: 140px;
}
.composer textarea:focus {
  border-color: var(--blue-300);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--blue) 14%, transparent);
}
.send {
  width: 36px;
  height: 36px;
  flex: none;
  border-radius: 10px;
  border: none;
  background: var(--blue);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.send:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
