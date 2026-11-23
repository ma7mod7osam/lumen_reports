<!-- Copyright (c) 2026 Lumen Solutions. All rights reserved.
     SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
     Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions. -->
<template>
  <main class="wrap">
    <div class="top">
      <div>
        <h1>{{ t('Audit trail') }}</h1>
        <p>{{ t('Every recorded change, one row each, across the whole site.') }}</p>
      </div>
      <router-link to="/" class="lbtn">{{ t('Back to dashboards') }}</router-link>
    </div>

    <p v-if="denied" class="err">
      {{ t('You need the Lumen Auditor role to read the audit trail. Ask your administrator.') }}
    </p>

    <template v-else>
      <div class="panel">
        <div class="panel-b filters">
          <div class="lfield req">
            <label>{{ t('From') }}</label>
            <input v-model="form.from_date" type="date" />
          </div>
          <div class="lfield req">
            <label>{{ t('To') }}</label>
            <input v-model="form.to_date" type="date" />
          </div>

          <div v-for="pick in PICKERS" :key="pick.key" class="lfield">
            <label>{{ t(pick.label) }}</label>
            <select v-model="form[pick.key]">
              <option value="">{{ t('Any') }}</option>
              <option v-for="o in (choices[pick.source] || [])" :key="o" :value="o">{{ o }}</option>
            </select>
          </div>

          <div v-for="typed in TYPED" :key="typed.key" class="lfield">
            <label>{{ t(typed.label) }}</label>
            <input v-model="form[typed.key]" type="text" :placeholder="t(typed.hint)" />
          </div>
        </div>

        <div class="bar">
          <span v-if="error" class="err inline">{{ error }}</span>
          <span v-else-if="busy" class="note">{{ t('Reading the history...') }}</span>
          <span v-else-if="result" class="note">
            {{ t('Changes found') }}: <b class="mono">{{ result.rows.length }}</b>
          </span>
          <span v-else class="note">{{ t('Choose a period, then run it.') }}</span>
          <span style="flex: 1"></span>
          <button class="lbtn" :disabled="busy || !result" @click="exportCsv">{{ t('Export CSV') }}</button>
          <button
            v-if="canPrint"
            class="lbtn"
            :disabled="busy || !result"
            @click="printPdf"
          >
            {{ t('Print PDF') }}
          </button>
          <button class="lbtn primary" :disabled="busy" @click="run">{{ t('Run') }}</button>
        </div>
      </div>

      <div v-for="note in (result?.notes || [])" :key="note" class="advice">{{ note }}</div>

      <div v-if="result" class="panel tablewrap">
        <TableBody :result="result" />
      </div>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { call } from 'frappe-ui'
import TableBody from '@/components/widgets/TableBody.vue'
import { downloadFile, resultToCsv } from '@/lib/csv'
import { lang, t } from '@/lib/i18n'
import '@/components/builder/controls.css'

const KEY = 'lumen_reports.audit_trail'

// the pickers are filled from the trail itself, not from the site's lists: an
// auditor often holds no other role, so asking for every User would be refused
const PICKERS = [
  { key: 'company', label: 'Company', source: 'companies' },
  { key: 'module', label: 'Module', source: 'modules' },
  { key: 'doctype', label: 'Document type', source: 'doctypes' },
  { key: 'user', label: 'Changed by', source: 'users' },
  { key: 'action', label: 'Action', source: 'actions' },
  { key: 'status', label: 'Document status', source: 'statuses' },
]

const TYPED = [
  { key: 'document', label: 'Document no.', hint: 'Exact document name' },
  { key: 'field', label: 'Field', hint: 'Part of the field name' },
  { key: 'branch', label: 'Branch', hint: 'Where the document has one' },
  { key: 'cost_center', label: 'Cost centre', hint: 'Where the document has one' },
]

function blank() {
  const today = new Date()
  const first = new Date(today.getFullYear(), today.getMonth(), 1)
  const iso = (d) => d.toISOString().slice(0, 10)
  const out = { from_date: iso(first), to_date: iso(today) }
  for (const p of [...PICKERS, ...TYPED]) out[p.key] = ''
  return out
}

const form = reactive(blank())
const choices = ref({})
const result = ref(null)
const busy = ref(false)
const error = ref('')
// Whether this person holds the role is settled before any request: the server
// writes audit.can_see() into boot as window.lumen_auditor (www/lumen.py), which
// is the same answer that gates the header link. It must never be inferred from
// a failed request. It was, and a real auditor who HELD the role was told to go
// and ask his administrator for it, because what actually failed was an HTTP
// method refused on our side. A request that fails now says what it failed at.
// Only boot, or the server naming a role refusal, closes the page.
// In the Vite dev server boot is unrendered, so anything but an explicit false
// counts as allowed, as capabilities.js does.
const refused = ref(false)
const denied = computed(() => window.lumen_auditor === false || refused.value)

onMounted(async () => {
  try {
    choices.value = await call('lumen_reports.audit.options')
  } catch (e) {
    // the pickers are a convenience, not the page: the dates and the typed
    // filters still run, so say what went wrong and leave the page standing
    error.value = readable(e) || t('The filter choices could not be read.')
  }
})

function sent() {
  const out = {}
  for (const [k, v] of Object.entries(form)) {
    if (v === '' || v === null) continue
    // the report takes these as lists, so one chosen value travels as a list
    out[k] = ['company', 'module', 'doctype', 'user', 'action', 'status'].includes(k) ? [v] : v
  }
  return out
}

async function run() {
  error.value = ''
  busy.value = true
  result.value = null
  try {
    const answer = await call('lumen_reports.integrations.sources.run_report', {
      key: KEY,
      filters: sent(),
    })
    if (answer.status !== 'ok') {
      refused.value = answer.status === 'needs_role' || answer.status === 'not_permitted'
      error.value = answer.message || t('That could not be read.')
      return
    }
    result.value = answer.result
  } catch (e) {
    error.value = readable(e) || t('That could not be read.')
  } finally {
    busy.value = false
  }
}

function readable(failure) {
  const strip = (x) => String(x || '').replace(/<[^>]+>/g, '').trim()
  if (Array.isArray(failure?.messages) && failure.messages.length) return strip(failure.messages[0])
  return strip(failure?.message)
}

// printing needs WeasyPrint, which does not ship with Frappe v14; the rest of
// the page works there, so the button goes rather than failing when pressed
const canPrint = computed(() => window.reports_enabled !== false)

function printPdf() {
  const query = new URLSearchParams({
    key: KEY,
    filters: JSON.stringify(sent()),
    // a wide report has nowhere to go on a portrait page
    options: JSON.stringify({ paper: 'A4 Landscape', lang: lang.value, header: 1 }),
  })
  window.open(`/api/method/lumen_reports.integrations.sources.download_report?${query}`, '_blank')
}

function exportCsv() {
  const csv = resultToCsv(result.value, 'audit-trail')
  if (csv) downloadFile(`audit-trail-${form.from_date}-${form.to_date}.csv`, csv)
}
</script>

<style scoped>
.wrap {
  max-width: 1400px;
  margin: 0 auto;
  padding: 26px 24px 80px;
}
.top {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
}
.top h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: var(--ink);
  letter-spacing: -0.01em;
}
.top p {
  margin: 5px 0 0;
  font-size: 13.5px;
  color: var(--muted);
  font-weight: 500;
}
.top .lbtn {
  margin-inline-start: auto;
  flex: none;
  text-decoration: none;
}

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px;
}
.lfield.req > label::after {
  content: ' *';
  color: var(--danger);
}
.lfield select {
  height: 36px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--ink);
  font-family: var(--font);
  font-size: 13px;
  width: 100%;
  outline: none;
}

.bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px 16px;
  border-top: 1px solid var(--border);
}
.note {
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}
.err.inline {
  margin: 0;
  font-size: 12px;
}
.advice {
  margin: 12px 0 0;
  padding: 9px 14px;
  border-radius: 10px;
  background: var(--warning-bg);
  color: var(--warning);
  font-size: 12.5px;
  font-weight: 600;
}
.tablewrap {
  margin-top: 16px;
  height: 60vh;
  overflow: hidden;
  padding: 0;
}
</style>
