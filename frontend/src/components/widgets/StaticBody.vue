<template>
  <!-- Layout furniture: the pieces that make a board read like a document
       rather than a pile of charts. None of these touch the data engine, so
       they never load, never fail, and never need a permission check. -->
  <!-- dir="auto" lets an Arabic heading run right to left and an English one
       left to right, each from its own first letter -->
  <div v-if="widgetType === 'Heading'" class="el-heading" :class="[align, 'lv' + level]">
    <div class="ht" :class="{ ar: isArabic(style.text || t('Section heading')) }" dir="auto">{{ style.text || t('Section heading') }}</div>
    <div v-if="style.subtext" class="hs" :class="{ ar: isArabic(style.subtext) }" dir="auto">{{ style.subtext }}</div>
  </div>

  <div v-else-if="widgetType === 'Text'" class="el-text" :class="[align, size, { framed: !!style.framed }]">
    <p :class="{ ar: isArabic(style.text || t('Write a note for whoever reads this dashboard.')) }" dir="auto">{{ style.text || t('Write a note for whoever reads this dashboard.') }}</p>
  </div>

  <div v-else-if="widgetType === 'Divider'" class="el-divider">
    <span v-if="style.text" class="dl" :class="{ ar: isArabic(style.text) }" dir="auto">{{ style.text }}</span>
    <i class="rule"></i>
  </div>

  <div v-else class="el-image" :class="{ framed: !!style.framed }">
    <img v-if="style.url" :src="style.url" :alt="style.text || ''" :style="{ objectFit: style.fit || 'contain' }" />
    <div v-else class="ph">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
        <rect x="3" y="3" width="18" height="18" rx="3" />
        <circle cx="9" cy="9" r="2" />
        <path d="m21 15-4.6-4.6L5 22" />
      </svg>
      <span>{{ t('Add an image URL in the side panel') }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { t } from '@/lib/i18n'

const props = defineProps({
  widgetType: { type: String, required: true },
  style: { type: Object, default: () => ({}) },
})

const align = computed(() => props.style.align || 'left')
const size = computed(() => props.style.size || 'md')
const level = computed(() => Number(props.style.level) || 1)

function isArabic(text) {
  return /[؀-ۿ]/.test(text || '')
}
</script>

<style scoped>
/* "left" means the start of the line and "right" its end, so an Arabic
   heading set to the default sits on the right where Arabic begins */
.left {
  text-align: start;
}
.center {
  text-align: center;
}
.right {
  text-align: end;
}

.el-heading {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
  padding: 2px 2px 6px;
}
.el-heading .ht {
  color: var(--ink);
  font-weight: 800;
  letter-spacing: -0.028em;
  line-height: 1.2;
}
.el-heading.lv1 .ht {
  font-size: 26px;
}
.el-heading.lv2 .ht {
  font-size: 20px;
}
.el-heading.lv3 .ht {
  font-size: 15px;
  font-family: var(--mono);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
.el-heading .hs {
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
}

.el-text {
  height: 100%;
  color: var(--ink-2);
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.el-text p {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.65;
}
.el-text.sm p {
  font-size: 12.5px;
}
.el-text.md p {
  font-size: 14px;
}
.el-text.lg p {
  font-size: 17px;
  color: var(--ink);
}
.el-text.framed {
  background: var(--panel);
  border: 1px solid var(--panel-border-color, var(--border));
  border-radius: var(--panel-radius);
  box-shadow: var(--panel-shadow, var(--shadow));
  padding: var(--panel-pad);
}

.el-divider {
  height: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
}
.el-divider .dl {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--faint);
  font-weight: 500;
  white-space: nowrap;
}

/* Arabic letters join to their neighbours: any letter-spacing pulls a word
   apart into disconnected letters, and the mono face has no Arabic glyphs */
.ar,
.el-heading.lv3 .ht.ar,
.el-divider .dl.ar {
  letter-spacing: 0;
  text-transform: none;
  font-family: var(--font);
}
.el-divider .dl.ar {
  font-size: 12px;
}
.el-divider .rule {
  flex: 1;
  height: 1px;
  background: var(--border);
  display: block;
}

.el-image {
  height: 100%;
  overflow: hidden;
  border-radius: var(--panel-radius);
}
.el-image.framed {
  background: var(--panel);
  border: 1px solid var(--panel-border-color, var(--border));
  box-shadow: var(--panel-shadow, var(--shadow));
  padding: 10px;
}
.el-image img {
  width: 100%;
  height: 100%;
  display: block;
  border-radius: calc(var(--panel-radius) - 6px);
}
.el-image .ph {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
  padding: 14px;
  border: 1.5px dashed var(--border-2);
  border-radius: var(--panel-radius);
  color: var(--faint);
  font-size: 12px;
  font-weight: 600;
}
</style>
