<template>
  <div class="panel flex h-full flex-col" :class="{ err: !!error }">
    <div v-if="title" class="panel-h" style="padding: 13px 18px">
      <div>
        <div class="t" dir="auto">{{ title }}</div>
        <div v-if="subtitle" class="s" dir="auto">{{ subtitle }}</div>
      </div>
      <slot name="actions" />
    </div>
    <div class="relative min-h-0 flex-1" style="padding: 14px 18px 16px">
      <div v-if="error" class="empty" style="padding: 20px">
        <div class="ic">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v5M12 16h.01" />
          </svg>
        </div>
        <div style="font-weight: 700; color: var(--ink)">{{ t("Couldn't load this widget") }}</div>
        <div style="font-size: 12.5px">{{ shortError }}</div>
      </div>
      <template v-else>
        <div v-if="loading && !hasData" class="flex h-full flex-col gap-3">
          <div class="skel" style="height: 60%; min-height: 42px"></div>
          <div class="skel" style="height: 14px; width: 70%"></div>
          <div class="skel" style="height: 14px; width: 45%"></div>
        </div>
        <slot v-else />
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { t } from '@/lib/i18n'

const props = defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  hasData: { type: Boolean, default: false },
  error: { default: null },
})

const shortError = computed(() => {
  if (!props.error) return ''
  const message = props.error.messages?.[0] || props.error.message || String(props.error)
  return message.length > 120 ? message.slice(0, 120) + '…' : message
})
</script>
