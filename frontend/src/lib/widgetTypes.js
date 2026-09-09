/**
 * What a widget can be, in one place: the data widgets that run a query and
 * the layout elements that don't.
 */

/** Elements that carry no query — headings, notes, rules, pictures. */
export const STATIC_TYPES = ['Heading', 'Text', 'Divider', 'Image']

export function isStatic(type) {
  return STATIC_TYPES.includes(type)
}

/** Chart and data widgets, in the order the insert rail shows them. */
export const CHART_PALETTE = [
  { label: 'Number', value: 'Number Card' },
  { label: 'Gauge', value: 'Gauge' },
  { label: 'Sparkline', value: 'Sparkline' },
  { label: 'Bar', value: 'Bar Chart' },
  { label: 'Stacked', value: 'Stacked Bar' },
  { label: 'Ranked', value: 'Horizontal Bar' },
  { label: 'Line', value: 'Line Chart' },
  { label: 'Area', value: 'Area Chart' },
  { label: 'Waterfall', value: 'Waterfall' },
  { label: 'Progress', value: 'Progress Bars' },
  { label: 'Donut', value: 'Donut Chart' },
  { label: 'Pie', value: 'Pie Chart' },
  { label: 'Rings', value: 'Rings' },
  { label: 'Radar', value: 'Radar' },
  { label: 'Funnel', value: 'Funnel' },
  { label: 'Scatter', value: 'Scatter' },
  { label: 'Heatmap', value: 'Heatmap' },
  { label: 'Tree', value: 'Tree Report' },
  { label: 'Table', value: 'Table' },
]

export const ELEMENT_PALETTE = [
  { label: 'Heading', value: 'Heading' },
  { label: 'Text', value: 'Text' },
  { label: 'Divider', value: 'Divider' },
  { label: 'Image', value: 'Image' },
]

export const DEFAULT_SIZES = {
  'Number Card': { w: 3, h: 2 },
  Table: { w: 12, h: 5 },
  Sparkline: { w: 3, h: 3 },
  Gauge: { w: 3, h: 3 },
  Rings: { w: 4, h: 4 },
  Radar: { w: 4, h: 5 },
  'Progress Bars': { w: 4, h: 4 },
  Heatmap: { w: 12, h: 5 },
  'Tree Report': { w: 12, h: 7 },
  Heading: { w: 12, h: 1 },
  Text: { w: 4, h: 3 },
  Divider: { w: 12, h: 1 },
  Image: { w: 4, h: 4 },
  default: { w: 6, h: 5 },
}

export function defaultSize(type) {
  return DEFAULT_SIZES[type] || DEFAULT_SIZES.default
}

/** Sensible starting content so a freshly inserted element is never blank. */
export function defaultStyle(type) {
  if (type === 'Heading') return { text: 'Section heading', level: 1, align: 'left' }
  if (type === 'Text') return { text: '', align: 'left', size: 'md' }
  if (type === 'Divider') return { text: '' }
  if (type === 'Image') return { url: '', fit: 'contain', framed: true }
  return {}
}
