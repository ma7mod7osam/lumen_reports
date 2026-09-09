<template>
  <div class="mx-auto max-w-5xl px-6 py-10">
    <div class="head">
      <h1>Create a dashboard</h1>
      <p>Describe it and the assistant drafts it, or start from a template</p>
    </div>

    <!-- describe it -->
    <form class="hero" @submit.prevent="describe">
      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 3v2M12 19v2M5.6 5.6 7 7M17 17l1.4 1.4M3 12h2M19 12h2M5.6 18.4 7 17M17 7l1.4-1.4" />
        <circle cx="12" cy="12" r="4" />
      </svg>
      <input
        v-model="prompt"
        type="text"
        placeholder="A monthly sales dashboard per branch, with targets and top customers"
        spellcheck="false"
      />
      <button class="lbtn primary" type="submit" :disabled="!prompt.trim()">Build it</button>
    </form>

    <div class="rule">
      <span class="mono">Or start from a template</span>
      <i></i>
    </div>

    <div v-if="loading" class="cards">
      <div v-for="i in 3" :key="i" class="skel" style="height: 196px; border-radius: 16px"></div>
    </div>

    <div v-else class="cards">
      <button
        v-for="t in starters"
        :key="t.id"
        class="tcard"
        :disabled="!!building"
        @click="use(t)"
      >
        <span class="thumb">
          <span v-for="(row, ri) in thumbRows(t)" :key="ri" class="trow">
            <i v-for="(cell, ci) in row" :key="ci" :class="'mini ' + cell.kind" :style="{ flex: cell.span }">
              <ChartIcon v-if="cell.type" :type="cell.type" :size="13" />
            </i>
          </span>
        </span>
        <span class="tmeta">
          <span class="tname">{{ t.name }}</span>
          <span class="tsub">{{ t.widget_count }} widgets · {{ t.doctype }}</span>
          <span class="tdesc">{{ t.description }}</span>
        </span>
        <span v-if="building === t.id" class="tbusy">Building…</span>
      </button>

      <router-link to="/new/blank" class="tcard blank">
        <span class="plus">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
        </span>
        <span class="tname">Start blank</span>
        <span class="tsub">An empty canvas</span>
      </router-link>
    </div>

    <p v-if="error" class="err-note">{{ error }}</p>
    <p v-else-if="!loading && !starters.length" class="foot">
      No template matches the apps installed here. Start blank, or describe what you need.
    </p>
    <p v-else class="foot">
      A template runs against your own data first and leaves out anything this site cannot answer.
    </p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { call } from 'frappe-ui'
import ChartIcon from '@/components/widgets/ChartIcon.vue'
import '@/components/builder/controls.css'

const router = useRouter()
const prompt = ref('')
const starters = ref([])
const loading = ref(true)
const building = ref('')
const error = ref('')

onMounted(async () => {
  try {
    starters.value = await call('lumen_reports.starters.list_starters')
  } catch (e) {
    error.value = e.messages?.[0] || e.message || String(e)
  } finally {
    loading.value = false
  }
})

function describe() {
  if (!prompt.value.trim()) return
  router.push({ name: 'AskAI', query: { q: prompt.value.trim() } })
}

async function use(starter) {
  if (building.value) return
  building.value = starter.id
  error.value = ''
  try {
    const result = await call('lumen_reports.starters.create_from_starter', {
      starter_id: starter.id,
    })
    router.push({ name: 'DashboardEdit', params: { slug: result.slug } })
  } catch (e) {
    error.value = e.messages?.[0] || e.message || String(e)
    building.value = ''
  }
}

/** A rough picture of the template's shape, drawn from its widget types. */
function thumbRows(starter) {
  const types = (starter.widget_types || []).filter((t) => t !== 'Heading' && t !== 'Divider')
  const kpis = types.filter((t) => t === 'Number Card')
  const rest = types.filter((t) => t !== 'Number Card').slice(0, 3)
  const rows = []
  if (kpis.length) {
    rows.push(kpis.slice(0, 4).map(() => ({ kind: 'kpi', span: 1 })))
  }
  if (rest.length) {
    rows.push(rest.map((t, i) => ({ kind: 'big', span: i === 0 ? 2 : 1, type: t })))
  }
  return rows
}
</script>

<style scoped>
.head {
  text-align: center;
  margin-bottom: 26px;
}
.head h1 {
  font-size: 27px;
  font-weight: 800;
  letter-spacing: -0.025em;
  color: var(--ink);
}
.head p {
  font-size: 13.5px;
  color: var(--muted);
  margin-top: 4px;
}

.hero {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--panel);
  border: 1.5px solid var(--blue-300);
  border-radius: 16px;
  padding: 14px 16px;
  box-shadow: 0 8px 24px color-mix(in srgb, var(--blue) 10%, transparent);
  margin-bottom: 30px;
}
.hero svg {
  flex: none;
}
.hero input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  outline: none;
  font-family: var(--font);
  font-size: 14.5px;
  color: var(--ink);
}
.hero input::placeholder {
  color: var(--faint);
}

.rule {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}
.rule span {
  font-size: 10px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
  white-space: nowrap;
}
.rule i {
  flex: 1;
  height: 1px;
  background: var(--border);
  display: block;
}

.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
@media (max-width: 900px) {
  .cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 600px) {
  .cards {
    grid-template-columns: 1fr;
  }
}

.tcard {
  position: relative;
  display: flex;
  flex-direction: column;
  text-align: left;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: var(--shadow);
  cursor: pointer;
  font-family: var(--font);
  padding: 0;
  transition: border-color 0.15s, transform 0.15s;
  text-decoration: none;
}
.tcard:hover:not(:disabled) {
  border-color: var(--blue);
  transform: translateY(-2px);
}
.tcard:disabled {
  opacity: 0.6;
  cursor: default;
}
.thumb {
  height: 118px;
  background: var(--panel-2);
  border-bottom: 1px solid var(--border);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.trow {
  display: flex;
  gap: 6px;
  flex: 1;
}
.trow:first-child:not(:only-child) {
  flex: none;
  height: 20px;
}
.mini {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--blue);
  min-width: 0;
}
.tmeta {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.tname {
  font-size: 13.5px;
  font-weight: 800;
  color: var(--ink);
}
.tsub {
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
}
.tdesc {
  font-size: 11.5px;
  color: var(--muted);
  margin-top: 4px;
  line-height: 1.45;
}
.tbusy {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--panel) 78%, transparent);
  font-size: 13px;
  font-weight: 700;
  color: var(--blue);
}

.tcard.blank {
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 196px;
  border-style: dashed;
  box-shadow: none;
  background: transparent;
}
.plus {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: var(--panel-2);
  color: var(--muted);
  display: flex;
  align-items: center;
  justify-content: center;
}

.foot,
.err-note {
  text-align: center;
  margin-top: 20px;
  font-size: 12px;
  color: var(--faint);
  font-weight: 600;
}
.err-note {
  color: var(--danger);
}
</style>
