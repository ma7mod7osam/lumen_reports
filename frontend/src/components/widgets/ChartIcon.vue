<template>
  <!-- one glyph per widget type, shared by the variant bar and the wizard chips -->
  <svg v-if="type === 'Bar Chart'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="12" width="4.5" height="9" rx="1" /><rect x="10" y="5" width="4.5" height="16" rx="1" /><rect x="17" y="9" width="4.5" height="12" rx="1" /></svg>
  <svg v-else-if="type === 'Horizontal Bar'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="4" width="17" height="4" rx="1" /><rect x="3" y="10" width="12" height="4" rx="1" /><rect x="3" y="16" width="7" height="4" rx="1" /></svg>
  <svg v-else-if="type === 'Line Chart'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m3 16 5.5-6 4.5 4L21 6" /></svg>
  <svg v-else-if="type === 'Area Chart'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><path d="M3 20V16l5.5-6 4.5 4L21 6v14H3Z" opacity="0.45" /><path d="m3 16 5.5-6 4.5 4L21 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
  <svg v-else-if="type === 'Sparkline'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 15.5c2-4 3.2 1.6 5-1.5 1.9-3.2 2.6 3.2 4.4.4C13.2 11.6 14 17 16 13.4c1.6-3 2.6 1.3 6-5.4" /></svg>
  <svg v-else-if="type === 'Waterfall'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><rect x="2.5" y="14" width="4" height="5" rx="1" /><rect x="8" y="9" width="4" height="5" rx="1" opacity="0.75" /><rect x="13.5" y="11" width="4" height="5" rx="1" opacity="0.75" /><rect x="19" y="4" width="4" height="15" rx="1" /></svg>
  <svg v-else-if="type === 'Donut Chart'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4.5"><circle cx="12" cy="12" r="7.5" /></svg>
  <svg v-else-if="type === 'Pie Chart'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3a9 9 0 1 0 9 9h-9V3Z" /><path d="M14 2.2A9 9 0 0 1 21.8 10H14V2.2Z" opacity="0.55" /></svg>
  <svg v-else-if="type === 'Rings'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round"><circle cx="12" cy="12" r="9" stroke-width="2.4" opacity="0.28" /><path d="M12 3a9 9 0 0 1 8 4.9" stroke-width="2.4" /><circle cx="12" cy="12" r="5" stroke-width="2.4" opacity="0.28" /><path d="M12 7a5 5 0 0 1 4.6 3" stroke-width="2.4" /></svg>
  <svg v-else-if="type === 'Radar'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="M12 2.5 21 9l-3.4 10.5H6.4L3 9 12 2.5Z" opacity="0.42" /><path d="M12 7.5l5 3.6-1.9 5.9H8.9L7 11.1 12 7.5Z" fill="currentColor" fill-opacity="0.18" /></svg>
  <svg v-else-if="type === 'Funnel'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><path d="M4 4h16l-3 5H7L4 4Z" /><path d="M8 11h8l-2 4h-4l-2-4Z" opacity="0.75" /><path d="M10.6 17h2.8l-.9 3.5h-1L10.6 17Z" opacity="0.5" /></svg>
  <svg v-else-if="type === 'Scatter'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><circle cx="6" cy="16.5" r="2.6" /><circle cx="12" cy="9" r="3.4" opacity="0.7" /><circle cx="18" cy="14" r="2" opacity="0.85" /><circle cx="9.5" cy="4.6" r="1.7" opacity="0.5" /></svg>
  <svg v-else-if="type === 'Heatmap'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="5.6" height="5.6" rx="1.4" opacity="0.3" /><rect x="9.8" y="3" width="5.6" height="5.6" rx="1.4" opacity="0.6" /><rect x="16.6" y="3" width="5.6" height="5.6" rx="1.4" opacity="0.25" /><rect x="3" y="9.8" width="5.6" height="5.6" rx="1.4" opacity="0.75" /><rect x="9.8" y="9.8" width="5.6" height="5.6" rx="1.4" /><rect x="16.6" y="9.8" width="5.6" height="5.6" rx="1.4" opacity="0.45" /><rect x="3" y="16.6" width="5.6" height="5.6" rx="1.4" opacity="0.2" /><rect x="9.8" y="16.6" width="5.6" height="5.6" rx="1.4" opacity="0.5" /><rect x="16.6" y="16.6" width="5.6" height="5.6" rx="1.4" opacity="0.85" /></svg>
  <svg v-else-if="type === 'Gauge'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M3.5 18a9 9 0 1 1 17 0" opacity="0.3" /><path d="M3.5 18A9 9 0 0 1 9 9.7" /><path d="M12 18v-4.5" stroke-width="2.2" /></svg>
  <svg v-else-if="type === 'Number Card'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="5" width="18" height="14" rx="3" /><path d="M7.5 14.5V9.5l-1.6 1.2M13 14.5h3.8" stroke-width="2.2" /></svg>
  <svg v-else-if="type === 'Table'" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2.5" /><path d="M3 9.5h18M9.5 9.5V20" /></svg>
</template>

<script setup>
defineProps({
  type: { type: String, required: true },
  size: { type: [Number, String], default: 13 },
})
</script>
