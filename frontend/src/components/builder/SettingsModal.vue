<template>
  <Modal title="Dashboard settings" width="620px" @close="$emit('close')">
    <div class="flex flex-col gap-4" style="padding: 18px">
      <div class="grid grid-cols-2 gap-3">
        <div class="lfield">
          <label>Title</label>
          <input type="text" v-model="local.title" placeholder="e.g. Sales Overview" />
        </div>
        <div class="lfield">
          <label>Slug (URL)</label>
          <input type="text" v-model="local.slug" :disabled="!isNew" placeholder="sales-overview" />
        </div>
      </div>
      <div class="lfield">
        <label>Description</label>
        <textarea v-model="local.description" rows="2" placeholder="What does this dashboard show?"></textarea>
      </div>
      <div class="flex gap-6">
        <label class="flex cursor-pointer items-center gap-2" style="font-size: 13.5px; font-weight: 600; color: var(--ink-2)">
          <input type="checkbox" v-model="local.auto_refresh" /> Live updates
        </label>
        <label class="flex cursor-pointer items-center gap-2" style="font-size: 13.5px; font-weight: 600; color: var(--ink-2)">
          <input type="checkbox" v-model="local.is_published" /> Published
        </label>
      </div>

      <!-- audience: who a published dashboard is for -->
      <div v-if="local.is_published" class="lfield">
        <label>Who can see it</label>
        <p style="font-size: 12.5px; color: var(--muted); margin-bottom: 6px">
          Empty means everyone with Lumen access. Add roles to restrict it — each viewer
          still only sees the data their own permissions allow.
        </p>
        <div class="flex flex-wrap items-center gap-2">
          <span v-for="r in local.visible_to_roles" :key="r" class="aud-chip">
            {{ r }}
            <button class="aud-x" :title="'Remove ' + r" @click="removeRole(r)">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>
          </span>
          <select class="mini" style="width: 200px" :value="''" @change="(e) => addRole(e)">
            <option value="" disabled>Add role…</option>
            <option v-for="r in availableRoles" :key="r" :value="r">{{ r }}</option>
          </select>
        </div>
      </div>

      <!-- dashboard filters -->
      <div class="lfield">
        <label>Dashboard filters</label>
        <p style="font-size: 12.5px; color: var(--muted); margin-bottom: 6px">
          Filters apply to every widget built on a matching doctype. Pick any link, choice, or
          checkbox field — including line-item fields like Item or Item Group.
        </p>
        <div v-if="!filterFields.length" class="note" style="margin: 0 0 8px">
          Add a widget first — filter fields come from your widgets' data sources.
        </div>
        <div class="flex flex-col gap-2">
          <div
            v-for="(f, i) in local.filters"
            :key="i"
            class="flex items-center gap-2 rounded-[10px] p-2"
            style="border: 1px solid var(--border)"
          >
            <input type="text" v-model="f.label" placeholder="Label" class="mini" style="flex: 1" />
            <select :value="f.name" class="mini" style="flex: 1.4" @change="(e) => pickField(f, e.target.value)">
              <option value="" disabled>Field…</option>
              <optgroup label="Fields">
                <option v-for="ff in parentFields" :key="ff.key" :value="ff.key">{{ ff.label }}</option>
              </optgroup>
              <optgroup v-if="childFields.length" label="Line items">
                <option v-for="ff in childFields" :key="ff.key" :value="ff.key">{{ ff.label }}</option>
              </optgroup>
            </select>
            <span class="badge b-gray" style="height: 20px">{{ f.fieldtype || '—' }}</span>
            <button class="icon-x" @click="local.filters.splice(i, 1)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>
          </div>
          <button
            class="chip"
            style="align-self: flex-start; border-style: dashed"
            :disabled="!filterFields.length"
            @click="addFilter"
          >
            + Add filter
          </button>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <button class="lbtn" @click="$emit('close')">Cancel</button>
        <button class="lbtn primary" :disabled="!local.title" @click="apply">Apply</button>
      </div>
    </template>
  </Modal>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { call } from 'frappe-ui'
import Modal from '@/components/builder/Modal.vue'

const props = defineProps({
  settings: { type: Object, required: true },
  isNew: { type: Boolean, default: false },
  // union of filterable field descriptors across widget doctypes
  filterFields: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'apply'])

const local = reactive(JSON.parse(JSON.stringify(props.settings)))
if (!Array.isArray(local.visible_to_roles)) local.visible_to_roles = []

const parentFields = computed(() => props.filterFields.filter((f) => f.source !== 'child'))
const childFields = computed(() => props.filterFields.filter((f) => f.source === 'child'))

// audience picker
const allRoles = ref([])
onMounted(async () => {
  try {
    allRoles.value = await call('lumen_reports.api.get_assignable_roles')
  } catch (e) {
    allRoles.value = [] // viewer opening settings read-only; picker just stays empty
  }
})
const availableRoles = computed(() => allRoles.value.filter((r) => !local.visible_to_roles.includes(r)))

function addRole(e) {
  const role = e.target.value
  if (role && !local.visible_to_roles.includes(role)) local.visible_to_roles.push(role)
  e.target.value = ''
}
function removeRole(role) {
  local.visible_to_roles = local.visible_to_roles.filter((r) => r !== role)
}

function addFilter() {
  local.filters.push({ name: '', label: '', fieldtype: '' })
}

// copy the chosen field descriptor into the filter definition (stored verbatim)
function pickField(filter, key) {
  const f = props.filterFields.find((x) => x.key === key)
  if (!f) return
  filter.name = f.key
  filter.fieldtype = f.fieldtype
  filter.source = f.source
  filter.fieldname = f.fieldname
  filter.child_doctype = f.child_doctype || null
  filter.parent_doctype = f.parent_doctype || null
  filter.base_doctype = f.base_doctype || null
  filter.link_doctype = f.link_doctype || null
  filter.options = f.options || null
  if (!filter.label) filter.label = f.label
}

function apply() {
  if (!local.slug) local.slug = local.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  emit('apply', JSON.parse(JSON.stringify(local)))
}
</script>

<style scoped>
.aud-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px 4px 11px;
  border-radius: 99px;
  background: color-mix(in srgb, var(--blue) 9%, var(--panel));
  border: 1px solid color-mix(in srgb, var(--blue) 25%, var(--border));
  color: var(--ink);
  font-size: 12.5px;
  font-weight: 600;
}
.aud-x {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 17px;
  height: 17px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}
.aud-x:hover {
  background: color-mix(in srgb, var(--danger) 12%, transparent);
  color: var(--danger);
}
.mini {
  height: 32px;
  padding: 0 8px;
  border-radius: 8px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--ink);
  font-family: var(--font);
  font-size: 12.5px;
  outline: none;
  min-width: 0;
}
.icon-x {
  border: none;
  background: transparent;
  color: var(--faint);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: flex;
}
.icon-x:hover {
  color: var(--danger);
  background: var(--panel-2);
}
</style>
