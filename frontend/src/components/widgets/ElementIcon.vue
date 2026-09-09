<template>
  <!-- glyphs for the layout elements, drawn to match ChartIcon's weight -->
  <svg v-if="type === 'Heading'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="4" width="18" height="4" rx="1.6" /><rect x="3" y="11" width="12" height="2.6" rx="1.3" opacity="0.5" /><rect x="3" y="16.4" width="15" height="2.6" rx="1.3" opacity="0.5" /></svg>
  <svg v-else-if="type === 'Text'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="5" width="18" height="2.6" rx="1.3" /><rect x="3" y="10" width="18" height="2.6" rx="1.3" opacity="0.7" /><rect x="3" y="15" width="13" height="2.6" rx="1.3" opacity="0.45" /></svg>
  <svg v-else-if="type === 'Divider'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><rect x="2" y="11" width="20" height="2.4" rx="1.2" /><circle cx="7" cy="6" r="1.4" opacity="0.4" /><circle cx="12" cy="6" r="1.4" opacity="0.4" /><circle cx="17" cy="6" r="1.4" opacity="0.4" /></svg>
  <svg v-else-if="type === 'Image'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="3" /><circle cx="8.8" cy="9.5" r="1.7" /><path d="m21 15.5-4.8-4.6L6 20" /></svg>
</template>

<script setup>
defineProps({
  type: { type: String, required: true },
  size: { type: [Number, String], default: 13 },
})
</script>
