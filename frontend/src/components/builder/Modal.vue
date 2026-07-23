<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style="background: rgba(7, 9, 15, 0.55); backdrop-filter: blur(4px)"
      @mousedown.self="$emit('close')"
    >
      <div
        class="panel flex max-h-[92vh] w-full flex-col overflow-hidden"
        :style="{ maxWidth: width, boxShadow: 'var(--shadow-md)' }"
      >
        <div class="panel-h" style="flex: none">
          <div>
            <div class="t">{{ title }}</div>
            <div v-if="subtitle" class="s">{{ subtitle }}</div>
          </div>
          <button class="icon-btn" style="width: 32px; height: 32px; border-radius: 8px; border: none; background: transparent; color: var(--muted); cursor: pointer; display: flex; align-items: center; justify-content: center" @click="$emit('close')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-auto">
          <slot />
        </div>
        <div v-if="$slots.footer" style="flex: none; border-top: 1px solid var(--border); padding: 14px 18px">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  width: { type: String, default: '560px' },
})
defineEmits(['close'])
</script>
