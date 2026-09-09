<template>
  <div class="tp">
    <div class="tp-head">
      <div>
        <div class="tp-title">Theme</div>
        <div class="tp-sub">Applies to this dashboard only</div>
      </div>
      <button class="x" title="Close" @click="$emit('close')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
      </button>
    </div>

    <div class="tp-body">
      <div class="grp">
        <label class="eyebrow">Preset</label>
        <div class="presets">
          <button
            class="preset"
            :class="{ on: !form.preset }"
            title="Follow the app theme"
            @click="pick('')"
          >
            <span class="strip app">
              <i style="flex: 2; background: var(--bg)"></i>
              <i style="flex: 1; background: var(--blue)"></i>
              <i style="flex: 1; background: var(--panel)"></i>
            </span>
            <span class="nm">App default</span>
          </button>
          <button
            v-for="p in THEME_PRESETS"
            :key="p.id"
            class="preset"
            :class="{ on: form.preset === p.id }"
            @click="pick(p.id)"
          >
            <span class="strip">
              <i :style="{ flex: 2, background: presetSwatch(p)[0] }"></i>
              <i :style="{ flex: 1, background: presetSwatch(p)[1] }"></i>
              <i :style="{ flex: 1, background: presetSwatch(p)[2] }"></i>
            </span>
            <span class="nm">{{ p.name }}</span>
          </button>
        </div>
      </div>

      <div class="grp">
        <label class="eyebrow">Brand color</label>
        <div class="brandrow">
          <input type="color" class="swatch" :value="brandValue" @input="onBrand($event.target.value)" />
          <input
            type="text"
            class="hex mono"
            :value="form.brand"
            placeholder="Preset default"
            spellcheck="false"
            @change="onBrand($event.target.value.trim())"
          />
          <button v-if="form.brand" class="x sm" title="Back to the preset color" @click="onBrand('')">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5" /></svg>
          </button>
        </div>
      </div>

      <div class="grp">
        <label class="eyebrow">Card style</label>
        <div class="segm">
          <button
            v-for="c in CARD_STYLES"
            :key="c.id"
            :class="{ on: effectiveCard === c.id }"
            @click="set('card', c.id)"
          >
            {{ c.label }}
          </button>
        </div>
      </div>

      <div class="two">
        <div class="grp">
          <label class="eyebrow">Corner radius</label>
          <div class="sliderow">
            <input type="range" min="0" max="28" step="2" :value="radiusValue" @input="set('radius', Number($event.target.value))" />
            <span class="mono num">{{ radiusValue }}</span>
          </div>
        </div>
        <div class="grp">
          <label class="eyebrow">Density</label>
          <div class="segm">
            <button
              v-for="d in DENSITIES"
              :key="d.id"
              :class="{ on: (form.density || 'comfort') === d.id }"
              @click="set('density', d.id)"
            >
              {{ d.label }}
            </button>
          </div>
        </div>
      </div>

      <div class="grp">
        <label class="eyebrow">Background</label>
        <div class="surfaces">
          <button
            v-for="s in SURFACES"
            :key="s.id"
            class="surface"
            :class="{ on: (form.surface || 'solid') === s.id }"
            :style="surfaceStyle(s.id)"
            :title="s.label"
            @click="set('surface', s.id)"
          >
            <span>{{ s.label }}</span>
          </button>
        </div>
      </div>

      <div class="grp">
        <label class="eyebrow">Font</label>
        <select class="sel" :value="form.font" @change="set('font', $event.target.value)">
          <option v-for="f in FONTS" :key="f.id" :value="f.id">{{ f.label }}</option>
        </select>
      </div>

      <div class="grp">
        <label class="eyebrow">Chart colors</label>
        <div class="dots">
          <i v-for="(c, i) in previewPalette" :key="i" :style="{ background: c }"></i>
        </div>
        <p class="hint">
          Charts follow the theme. A widget with its own accent keeps it, so a
          highlight you set by hand survives a preset change.
        </p>
      </div>

      <button v-if="!isDefaultTheme(form)" class="lbtn danger reset" @click="resetAll">
        Reset to the app theme
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import {
  CARD_STYLES,
  DEFAULT_THEME,
  DENSITIES,
  FONTS,
  SURFACES,
  THEME_PRESETS,
  findPreset,
  isDefaultTheme,
  presetSwatch,
  themeVars,
} from '@/lib/dashboardTheme'
import '@/components/builder/controls.css'

const props = defineProps({ theme: { type: Object, default: () => ({}) } })
const emit = defineEmits(['apply', 'close'])

const form = reactive({ ...DEFAULT_THEME, ...(props.theme || {}) })

watch(
  () => props.theme,
  (next) => Object.assign(form, { ...DEFAULT_THEME, ...(next || {}) }),
  { deep: true }
)

const preset = computed(() => findPreset(form.preset))
const effectiveCard = computed(() => form.card || preset.value?.card || 'outlined')
const radiusValue = computed(() =>
  form.radius === null || form.radius === undefined || form.radius === '' ? 16 : Number(form.radius)
)
const brandValue = computed(() => form.brand || preset.value?.vars['--blue'] || '#1463ff')

// the eight categorical colors as this theme would draw them
const previewPalette = computed(() => {
  const vars = themeVars(form)
  const slots = ['--c1', '--c2', '--c3', '--c4', '--c5', '--c6', '--c7', '--c8']
  return slots.map((s) => vars[s] || `var(${s})`)
})

function push() {
  emit('apply', { ...form })
}

function set(key, value) {
  form[key] = value
  push()
}

function pick(id) {
  form.preset = id
  push()
}

function onBrand(value) {
  form.brand = value || ''
  push()
}

function resetAll() {
  Object.assign(form, DEFAULT_THEME)
  push()
}

function surfaceStyle(id) {
  const vars = themeVars({ ...form, surface: id })
  return { background: vars['--canvas-bg'] || vars['--bg'] || 'var(--bg)' }
}
</script>

<style scoped>
.tp {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.tp-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 14px 12px;
  border-bottom: 1px solid var(--border);
}
.tp-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--ink);
}
.tp-sub {
  font-size: 11.5px;
  color: var(--muted);
  font-weight: 500;
  margin-top: 1px;
}
.x {
  width: 28px;
  height: 28px;
  flex: none;
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
.x.sm {
  width: 26px;
  height: 26px;
  border: 1px solid var(--border-2);
}
.tp-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.grp {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.eyebrow {
  font-family: var(--mono);
  font-size: 9.5px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
  font-weight: 600;
}

.presets {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.preset {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  background: var(--panel);
  cursor: pointer;
  text-align: left;
}
.preset:hover {
  border-color: var(--blue-300);
}
.preset.on {
  border-color: var(--blue);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--blue) 22%, transparent);
}
.preset .strip {
  height: 24px;
  border-radius: 7px;
  display: flex;
  overflow: hidden;
  border: 1px solid var(--border);
}
.preset .strip i {
  display: block;
}
.preset .nm {
  font-size: 11px;
  font-weight: 700;
  color: var(--ink-2);
}

.brandrow {
  display: flex;
  align-items: center;
  gap: 8px;
}
.swatch {
  width: 34px;
  height: 34px;
  flex: none;
  padding: 0;
  border: 1px solid var(--border-2);
  border-radius: 9px;
  background: transparent;
  cursor: pointer;
}
.swatch::-webkit-color-swatch-wrapper {
  padding: 3px;
}
.swatch::-webkit-color-swatch {
  border: none;
  border-radius: 6px;
}
.hex {
  flex: 1;
  min-width: 0;
  height: 34px;
  padding: 0 10px;
  border-radius: 9px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--ink);
  font-size: 12px;
  outline: none;
}
.hex:focus {
  border-color: var(--blue-300);
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
  font-size: 11.5px;
  font-weight: 700;
  color: var(--muted);
  cursor: pointer;
  white-space: nowrap;
}
.segm button.on {
  background: var(--panel);
  color: var(--ink);
  box-shadow: var(--shadow);
}

.sliderow {
  display: flex;
  align-items: center;
  gap: 9px;
}
.sliderow input[type='range'] {
  flex: 1;
  min-width: 0;
  accent-color: var(--blue);
}
.num {
  font-size: 11.5px;
  color: var(--ink-2);
  width: 20px;
  text-align: right;
}

.surfaces {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.surface {
  height: 42px;
  border-radius: 10px;
  border: 1px solid var(--border);
  cursor: pointer;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 4px;
  font-family: var(--font);
  font-size: 9.5px;
  font-weight: 700;
  color: var(--muted);
  overflow: hidden;
}
.surface span {
  background: color-mix(in srgb, var(--panel) 80%, transparent);
  border-radius: 5px;
  padding: 1px 5px;
}
.surface.on {
  border-color: var(--blue);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--blue) 22%, transparent);
}

.sel {
  height: 36px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid var(--border-2);
  background: var(--panel);
  color: var(--ink);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 500;
  outline: none;
  width: 100%;
}

.dots {
  display: flex;
  gap: 6px;
}
.dots i {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  display: block;
  border: 1px solid color-mix(in srgb, var(--ink) 8%, transparent);
}
.hint {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--muted);
  font-weight: 500;
}
.reset {
  width: 100%;
  justify-content: center;
}
</style>
