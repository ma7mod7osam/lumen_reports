<template>
  <div ref="el" class="theme-scope" :style="scopeStyle">
    <slot />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { themeVars, findPreset, isDefaultTheme } from '@/lib/dashboardTheme'
import { themeScope, themeVersion } from '@/lib/theme'

const props = defineProps({
  theme: { type: Object, default: null },
  // the viewer paints the page behind the cards; the builder canvas doesn't,
  // so the studio chrome keeps its own background
  paint: { type: Boolean, default: false },
})

const el = ref(null)
const active = computed(() => !isDefaultTheme(props.theme))

const scopeStyle = computed(() => {
  if (!active.value) return {}
  const style = { ...themeVars(props.theme) }
  const preset = findPreset(props.theme?.preset)
  if (preset) style.colorScheme = preset.base
  if (props.paint) {
    style.background = style['--canvas-bg'] || style['--bg'] || ''
    style.color = style['--ink'] || ''
  }
  return style
})

// charts read their colors from this element rather than from <html>, so a
// themed dashboard colors its own data. Registering the element is enough:
// custom properties inherit, so anything the theme leaves unset still comes
// from the app.
function register() {
  themeScope.value = active.value ? el.value : null
}

onMounted(register)
onBeforeUnmount(() => {
  if (themeScope.value === el.value) themeScope.value = null
})

watch(
  () => props.theme,
  async () => {
    register()
    // let the new custom properties land before charts re-read them
    await nextTick()
    themeVersion.value += 1
  },
  { deep: true }
)
</script>

<style scoped>
.theme-scope {
  /* a painted scope is the page surface itself, so it has to fill the space
     it was given rather than shrink to its content */
  display: block;
}
</style>
