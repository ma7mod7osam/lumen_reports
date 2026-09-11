<template>
  <div class="rp">
    <div class="rbar">
      <router-link :to="{ name: 'DashboardView', params: { slug } }" class="tbtn" :title="t('Back to the dashboard')">
        <svg class="flip-rtl" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6" /></svg>
      </router-link>
      <div class="rtitle" dir="auto">{{ title }}</div>
      <span class="badge b-blue">{{ t('Report') }}</span>
      <span class="grow"></span>
      <a class="lbtn" :href="pdfUrl(true)" target="_blank" rel="noopener">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V3h12v6" /><rect x="3" y="9" width="18" height="8" rx="2" /><path d="M6 14h12v7H6z" /></svg>
        {{ t('Open to print') }}
      </a>
      <a class="lbtn primary" :href="pdfUrl(false)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3v12m0 0 4-4m-4 4-4-4" /><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" /></svg>
        {{ t('Download PDF') }}
      </a>
    </div>

    <div class="rbody">
      <!-- the preview is the PDF itself, so what is shown is exactly what
           gets downloaded, printed or emailed -->
      <div class="rpreview">
        <iframe :key="previewSrc" :src="previewSrc" :title="t('Report preview')" @load="rendering = false"></iframe>
        <div v-if="rendering" class="rloading">
          <span class="spin"></span>
          {{ t('Rendering the PDF…') }}
        </div>
      </div>

      <aside class="rpanel">
        <div class="ptitle">{{ t('Print options') }}</div>

        <div class="grp">
          <div class="eyebrow">{{ t('Paper size') }}</div>
          <div class="segm">
            <button v-for="p in ['A4', 'Letter']" :key="p" :class="{ on: options.paper === p }" @click="options.paper = p">{{ t(p) }}</button>
          </div>
        </div>

        <div class="switches">
          <label class="sw-row">
            <span>{{ t('Company header') }}</span>
            <input v-model="options.header" type="checkbox" class="sw" />
          </label>
          <label class="sw-row">
            <span>{{ t('Page numbers') }}</span>
            <input v-model="options.page_numbers" type="checkbox" class="sw" />
          </label>
          <label class="sw-row" :class="{ off: !aiReady }" :title="aiReady ? '' : t('Needs an AI key in AI settings')">
            <span>
              {{ t('Executive summary') }}
              <small v-if="!aiReady">{{ t('Needs an AI key') }}</small>
            </span>
            <input v-model="options.summary" type="checkbox" class="sw" :disabled="!aiReady" />
          </label>
          <label class="sw-row">
            <span>{{ t('Arabic edition') }}</span>
            <input v-model="arabic" type="checkbox" class="sw" />
          </label>
        </div>

        <p v-if="filtersLabel" class="note">{{ t('Filtered as on the dashboard: {0}', filtersLabel) }}</p>

        <div class="ptitle sep">{{ t('Schedule') }}</div>

        <div v-if="!sched.loaded" class="skel" style="height: 60px; border-radius: 10px"></div>

        <template v-else>
          <div class="info">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>
            <span>{{ t('Each recipient gets their own copy, rendered with their own permissions.') }}</span>
          </div>

          <div v-if="!sched.email_ready" class="warn">
            {{ t('This site has no outgoing email account yet. Schedules can be saved, but nothing is sent until one is set up in the desk under Email Account.') }}
          </div>

          <div v-for="s in sched.schedules" :key="s.name" class="srow" :class="{ disabled: !s.enabled }">
            <div class="srow-main">
              <div class="srow-t">{{ describe(s) }}</div>
              <div class="srow-s">
                {{ t('Recipients: {0}', s.recipients.length) }} · {{ t(s.language) }} · {{ t(s.paper) }}
              </div>
              <div v-if="s.enabled && s.next_run" class="srow-s">{{ t('Next: {0}', when(s.next_run)) }}</div>
              <div v-if="s.last_status" class="srow-s muted" dir="auto">{{ t('Last run: {0}', s.last_status) }}</div>
            </div>
            <div v-if="s.can_edit" class="srow-acts">
              <input type="checkbox" class="sw" :checked="!!s.enabled" :title="t('Enabled')" @change="toggle(s, $event.target.checked)" />
              <button class="icon-btn" :title="t('Delete')" @click="remove(s)">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /></svg>
              </button>
            </div>
          </div>

          <template v-if="sched.can_schedule">
            <button v-if="!draft" class="lbtn sm add" @click="startDraft">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
              {{ t('New schedule') }}
            </button>

            <div v-else class="draft">
              <div class="segm">
                <button v-for="f in ['Daily', 'Weekly', 'Monthly']" :key="f" :class="{ on: draft.frequency === f }" @click="draft.frequency = f">{{ t(f) }}</button>
              </div>
              <div class="drow">
                <select v-if="draft.frequency === 'Weekly'" v-model="draft.day_of_week" class="ctl">
                  <option v-for="d in WEEKDAYS" :key="d" :value="d">{{ t(d) }}</option>
                </select>
                <select v-else-if="draft.frequency === 'Monthly'" v-model.number="draft.day_of_month" class="ctl">
                  <option v-for="d in 28" :key="d" :value="d">{{ t('Day {0}', d) }}</option>
                </select>
                <input v-model="draft.send_time" type="time" class="ctl time" />
              </div>
              <div class="eyebrow">{{ t('Recipients') }}</div>
              <div class="chips">
                <span v-for="u in draft.recipients" :key="u" class="pchip">
                  {{ userName(u) }}
                  <button :title="t('Remove')" @click="draft.recipients = draft.recipients.filter((x) => x !== u)">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
                  </button>
                </span>
              </div>
              <select class="ctl" :value="''" @change="addRecipient">
                <option value="" disabled>{{ t('Add person…') }}</option>
                <option v-for="u in availableUsers" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
              </select>
              <p class="note">
                {{
                  options.summary
                    ? t('Sent with the options above: {0}, {1}, with the executive summary.', t(options.paper), arabic ? t('Arabic') : t('English'))
                    : t('Sent with the options above: {0}, {1}.', t(options.paper), arabic ? t('Arabic') : t('English'))
                }}
              </p>
              <div class="dacts">
                <button class="lbtn sm primary" :disabled="!draft.recipients.length || saving" @click="saveDraft">{{ t('Save schedule') }}</button>
                <button class="lbtn sm" @click="draft = null">{{ t('Cancel') }}</button>
              </div>
            </div>
          </template>

          <button class="lbtn sm test" :disabled="testing" @click="sendTest">
            {{ testing ? t('Sending…') : t('Send me a test now') }}
          </button>
          <p v-if="message" class="note" :class="{ bad: messageBad }" dir="auto">{{ message }}</p>
        </template>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { call } from 'frappe-ui'
import { lang, t } from '@/lib/i18n'
import '@/components/builder/controls.css'

const props = defineProps({ slug: { type: String, required: true } })
const route = useRoute()

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const title = ref('')
const filterDefs = ref([])
const aiReady = ref(false)
const filterValues = (() => {
  try {
    return JSON.parse(route.query.filters || '{}') || {}
  } catch {
    return {}
  }
})()

const options = reactive({
  paper: 'A4',
  header: true,
  page_numbers: true,
  summary: false,
})
// the report follows the app's language unless the person switches it here
const arabic = ref(lang.value === 'ar')

// ---- preview ----------------------------------------------------------

const rendering = ref(true)
const previewSrc = ref('')
let previewTimer = null

function payload() {
  return { ...options, lang: arabic.value ? 'ar' : 'en', filter_values: filterValues }
}

function pdfUrl(inline) {
  const params = new URLSearchParams({ slug: props.slug, options: JSON.stringify(payload()) })
  if (inline) params.set('inline', '1')
  return `/api/method/lumen_reports.report.download?${params.toString()}`
}

function refreshPreview() {
  clearTimeout(previewTimer)
  previewTimer = setTimeout(() => {
    rendering.value = true
    previewSrc.value = pdfUrl(true) + `&t=${Date.now()}`
  }, 450)
}

watch([options, arabic], refreshPreview, { deep: true })

const filtersLabel = computed(() => {
  const byName = Object.fromEntries(filterDefs.value.map((f) => [f.name, f.label || f.name]))
  return Object.entries(filterValues)
    .filter(([, v]) => v !== '' && v !== null && v !== undefined)
    .map(([k, v]) => `${byName[k] || k}: ${v}`)
    .join(' · ')
})

// ---- schedules --------------------------------------------------------

const sched = reactive({ loaded: false, schedules: [], can_schedule: false, email_ready: true })
const users = ref([])
const draft = ref(null)
const saving = ref(false)
const testing = ref(false)
const message = ref('')
const messageBad = ref(false)

const availableUsers = computed(() => users.value.filter((u) => !draft.value?.recipients.includes(u.name)))

function userName(id) {
  const u = users.value.find((x) => x.name === id)
  return u?.full_name || id
}

async function loadSchedules() {
  try {
    Object.assign(sched, await call('lumen_reports.schedules.get_schedules', { slug: props.slug }), { loaded: true })
  } catch {
    sched.loaded = true
  }
  if (sched.can_schedule && !users.value.length) {
    try {
      users.value = await call('lumen_reports.api.get_assignable_users')
    } catch {
      users.value = []
    }
  }
}

function startDraft() {
  draft.value = {
    frequency: 'Weekly',
    day_of_week: 'Monday',
    day_of_month: 1,
    send_time: '08:00',
    recipients: [],
  }
}

function addRecipient(event) {
  const id = event.target.value
  if (id && !draft.value.recipients.includes(id)) draft.value.recipients.push(id)
  event.target.value = ''
}

async function saveDraft() {
  saving.value = true
  message.value = ''
  try {
    await call('lumen_reports.schedules.save_schedule', {
      payload: {
        slug: props.slug,
        ...draft.value,
        send_time: `${draft.value.send_time}:00`.slice(0, 8),
        language: arabic.value ? 'Arabic' : 'English',
        paper: options.paper,
        include_summary: options.summary ? 1 : 0,
      },
    })
    draft.value = null
    await loadSchedules()
  } catch (e) {
    showError(e)
  } finally {
    saving.value = false
  }
}

async function toggle(s, enabled) {
  try {
    await call('lumen_reports.schedules.save_schedule', { payload: { name: s.name, enabled: enabled ? 1 : 0 } })
    await loadSchedules()
  } catch (e) {
    showError(e)
  }
}

async function remove(s) {
  if (!window.confirm(t('Delete this schedule? Nobody on it will receive the report any more.'))) return
  try {
    await call('lumen_reports.schedules.delete_schedule', { name: s.name })
    await loadSchedules()
  } catch (e) {
    showError(e)
  }
}

async function sendTest() {
  testing.value = true
  message.value = ''
  try {
    const r = await call('lumen_reports.schedules.send_test', { slug: props.slug, options: payload() })
    messageBad.value = false
    message.value = t('Sent to {0}. It may take a minute to arrive.', r.sent_to)
  } catch (e) {
    showError(e)
  } finally {
    testing.value = false
  }
}

function showError(e) {
  messageBad.value = true
  message.value = e?.messages?.[0] || e?.message || String(e)
}

function describe(s) {
  const time = s.send_time || '08:00'
  if (s.frequency === 'Daily') return t('Every day at {0}', time)
  if (s.frequency === 'Monthly') return t('On day {0} of every month at {1}', s.day_of_month, time)
  return t('Every {0} at {1}', t(s.day_of_week), time)
}

function when(value) {
  const d = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return value
  const day = t(WEEKDAYS[(d.getDay() + 6) % 7])
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${day} ${d.getDate()}/${d.getMonth() + 1} ${hh}:${mm}`
}

onMounted(async () => {
  refreshPreview()
  try {
    const d = await call('lumen_reports.api.get_dashboard', { slug: props.slug })
    title.value = d.title
    filterDefs.value = d.filters || []
  } catch {
    /* the preview itself shows the permission error */
  }
  try {
    aiReady.value = !!(await call('lumen_reports.ai.get_ai_status'))?.configured
  } catch {
    aiReady.value = false
  }
  loadSchedules()
})
</script>

<style scoped>
.rp {
  min-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
}
.rbar {
  position: sticky;
  top: 64px;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 16px;
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: saturate(160%) blur(12px);
  border-bottom: 1px solid var(--border);
}
.tbtn {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}
.tbtn:hover {
  background: var(--panel-2);
  color: var(--ink);
}
.rtitle {
  font-size: 15px;
  font-weight: 800;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 40vw;
}
.grow {
  flex: 1;
}
.lbtn {
  text-decoration: none;
}

.rbody {
  flex: 1;
  display: flex;
  min-height: 0;
}
.rpreview {
  flex: 1;
  min-width: 0;
  position: relative;
  background: var(--panel-3);
}
.rpreview iframe {
  width: 100%;
  height: calc(100vh - 120px);
  border: 0;
  display: block;
}
.rloading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: color-mix(in srgb, var(--panel-3) 70%, transparent);
  color: var(--ink-2);
  font-size: 13px;
  font-weight: 600;
}
.spin {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--border-2);
  border-top-color: var(--blue);
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.rpanel {
  width: 320px;
  flex: none;
  height: calc(100vh - 120px);
  overflow-y: auto;
  padding: 16px;
  background: var(--panel);
  border-inline-start: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ptitle {
  font-size: 14px;
  font-weight: 800;
  color: var(--ink);
}
.ptitle.sep {
  border-top: 1px solid var(--border);
  padding-top: 14px;
  margin-top: 4px;
}
.grp {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.eyebrow {
  font-family: var(--mono);
  font-size: 9.5px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
  font-weight: 600;
}
.segm {
  display: flex;
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 3px;
  gap: 2px;
}
.segm button {
  flex: 1;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 7px;
  font-family: var(--font);
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  cursor: pointer;
}
.segm button.on {
  background: var(--panel);
  color: var(--ink);
  box-shadow: var(--shadow);
}
.switches {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--border);
  padding-top: 4px;
}
.sw-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink-2);
  cursor: pointer;
}
.sw-row small {
  display: block;
  font-size: 10.5px;
  font-weight: 500;
  color: var(--faint);
}
.sw-row.off {
  cursor: default;
}
/* a switch drawn from a plain checkbox, so it stays keyboard-accessible */
.sw {
  appearance: none;
  width: 32px;
  height: 18px;
  flex: none;
  border-radius: 99px;
  background: var(--border-2);
  position: relative;
  cursor: pointer;
  transition: background 0.15s;
}
.sw::after {
  content: '';
  position: absolute;
  top: 2px;
  inset-inline-start: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  transition: inset-inline-start 0.15s;
}
.sw:checked {
  background: var(--blue);
}
.sw:checked::after {
  inset-inline-start: 16px;
}
.sw:disabled {
  opacity: 0.45;
  cursor: default;
}
.note {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--muted);
}
.note.bad {
  color: var(--danger);
}
.info,
.warn {
  display: flex;
  gap: 8px;
  padding: 9px 11px;
  border-radius: 10px;
  font-size: 11.5px;
  line-height: 1.5;
  font-weight: 600;
}
.info {
  background: var(--success-bg);
  color: var(--success);
}
.info svg {
  flex: none;
  margin-top: 2px;
}
.warn {
  background: var(--warning-bg);
  color: var(--warning);
}
.srow {
  display: flex;
  gap: 8px;
  padding: 10px 11px;
  border: 1px solid var(--border);
  border-radius: 11px;
}
.srow.disabled {
  opacity: 0.6;
}
.srow-main {
  flex: 1;
  min-width: 0;
}
.srow-t {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--ink);
}
.srow-s {
  font-size: 11px;
  color: var(--muted);
  margin-top: 2px;
}
.srow-s.muted {
  color: var(--faint);
}
.srow-acts {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.icon-btn {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-btn:hover {
  color: var(--danger);
  border-color: var(--danger);
}
.add,
.test {
  justify-content: center;
}
.draft {
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding: 11px;
  border: 1px dashed var(--border-2);
  border-radius: 11px;
}
.drow {
  display: flex;
  gap: 7px;
}
.ctl {
  height: 34px;
  padding: 0 10px;
  border-radius: 9px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--ink);
  font-family: var(--font);
  font-size: 12.5px;
  flex: 1;
  min-width: 0;
}
.ctl.time {
  flex: none;
  width: 104px;
  font-family: var(--mono);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.pchip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding-block: 4px;
  padding-inline: 10px 6px;
  border-radius: 99px;
  background: var(--panel-2);
  font-size: 11.5px;
  font-weight: 600;
  color: var(--ink-2);
}
.pchip button {
  width: 16px;
  height: 16px;
  border: none;
  background: none;
  color: var(--muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}
.dacts {
  display: flex;
  gap: 7px;
}

@media (max-width: 900px) {
  .rbody {
    flex-direction: column;
  }
  .rpanel {
    width: auto;
    height: auto;
    border-inline-start: none;
    border-top: 1px solid var(--border);
  }
  .rpreview iframe {
    height: 70vh;
  }
}
</style>
