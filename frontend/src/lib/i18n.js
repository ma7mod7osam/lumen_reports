import { computed, ref } from 'vue'
import ar from '@/lib/locales/ar'
import { themeVersion } from '@/lib/theme'

/**
 * Two languages, one switch. English strings are their own keys, so a string
 * nobody has translated yet still reads correctly instead of showing a key.
 * Digits stay Western in both languages.
 */

const STORAGE_KEY = 'lumen-lang'

function initial() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'ar' || saved === 'en') return saved
  } catch {
    /* storage can be blocked; fall through to the site's language */
  }
  // the Frappe user's own language, handed over at page load
  return String(window.lumen_lang || '').startsWith('ar') ? 'ar' : 'en'
}

export const lang = ref(initial())
export const isRtl = computed(() => lang.value === 'ar')

export function applyLang() {
  document.documentElement.lang = lang.value
  document.documentElement.dir = isRtl.value ? 'rtl' : 'ltr'
}

export function setLang(next) {
  lang.value = next === 'ar' ? 'ar' : 'en'
  try {
    localStorage.setItem(STORAGE_KEY, lang.value)
  } catch {
    /* the choice just won't survive a reload */
  }
  applyLang()
  // charts mirror their axes for right-to-left, so they redraw like on a
  // theme change
  themeVersion.value += 1
}

/** Translate; {0}, {1} are replaced by the extra arguments in order. */
export function t(text, ...args) {
  let out = lang.value === 'ar' ? ar[text] ?? text : text
  args.forEach((value, i) => {
    out = out.split(`{${i}}`).join(String(value))
  })
  return out
}

const AR_MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
const EN_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const AR_WEEKDAYS = { Mon: 'الاثنين', Tue: 'الثلاثاء', Wed: 'الأربعاء', Thu: 'الخميس', Fri: 'الجمعة', Sat: 'السبت', Sun: 'الأحد' }

/**
 * Chart labels the engine returns in machine form. 2026-01 reads as
 * Jan 2026 or يناير 2026, Mon as الاثنين. Anything else passes through.
 */
export function axisLabel(label, grain) {
  const text = String(label ?? '')
  if (grain === 'month' && /^\d{4}-\d{2}$/.test(text)) {
    const [y, m] = text.split('-').map(Number)
    return `${(lang.value === 'ar' ? AR_MONTHS : EN_MONTHS)[m - 1]} ${y}`
  }
  if (grain === 'weekday' && lang.value === 'ar') return AR_WEEKDAYS[text] || text
  return text
}
