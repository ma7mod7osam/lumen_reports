<template>
  <div ref="chartEl" class="h-full w-full" style="min-height: 120px"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { formatNumber, formatValue } from '@/lib/palette'
import { cssv, chartPalette, themeVersion } from '@/lib/theme'

const props = defineProps({
  widgetType: { type: String, required: true },
  result: { type: Object, default: null },
  selectable: { type: Boolean, default: false },
  // the widget's query — used to detect time series (never folded)
  query: { type: Object, default: null },
  // palette slot for single-series charts (user-chosen accent color)
  accent: { type: Number, default: 0 },
  // gauge only: the target the value is measured against
  target: { type: [Number, String], default: null },
})

const WEEKDAY_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function sortWeekdays(labels) {
  // engine returns labels alphabetically; put weekdays in calendar order
  if (labels.length && labels.every((l) => WEEKDAY_ORDER.includes(l))) {
    return [...labels].sort((a, b) => WEEKDAY_ORDER.indexOf(a) - WEEKDAY_ORDER.indexOf(b))
  }
  return labels
}
const emit = defineEmits(['select'])

// ---- high-cardinality handling ------------------------------------------
// beyond a handful of identities a pie is unreadable and a bar axis is a
// picket fence: fold the tail into a muted, non-interactive "Other" bucket
const MAX_SLICES = 8 // pie/donut: 7 + Other
const MAX_BARS = 20 // bar: 19 + Other
const MAX_RADAR_AXES = 10 // a radar web past this is unreadable
const MAX_RADAR_SERIES = 4 // overlapping webs muddy each other
const MAX_RINGS = 5 // concentric rings run out of radius fast

function prettyLabel(text) {
  if (!text) return ''
  return String(text)
    .replace(/_/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase())
}

/** rank -> cap -> restore the engine's ordering (weekdays in calendar order) */
function topPairs(labels, values, max) {
  let pairs = labels.map((label, i) => [label, Number(values[i]) || 0])
  if (pairs.length > max) {
    const keep = new Set(
      [...pairs]
        .sort((a, b) => b[1] - a[1])
        .slice(0, max)
        .map((p) => p[0])
    )
    pairs = pairs.filter((p) => keep.has(p[0]))
  }
  if (pairs.length && pairs.every((p) => WEEKDAY_ORDER.includes(p[0]))) {
    pairs.sort((a, b) => WEEKDAY_ORDER.indexOf(a[0]) - WEEKDAY_ORDER.indexOf(b[0]))
  }
  return pairs
}

function otherLabel(count) {
  return `Other (${count} more)`
}

function isOther(name) {
  return typeof name === 'string' && /^Other \(\d+ more\)$/.test(name)
}

function isTimeSeries() {
  return !!props.query?.group_by?.time_grain
}

function foldSeries(result, maxItems) {
  const labels = result.labels || []
  const values = result.values || []
  if (labels.length <= maxItems) return { labels, values }
  // rank by value; keep the engine's original order for the survivors
  const ranked = labels
    .map((label, i) => ({ value: Number(values[i]) || 0, i }))
    .sort((a, b) => b.value - a.value)
  const keep = new Set(ranked.slice(0, maxItems - 1).map((r) => r.i))
  const outLabels = []
  const outValues = []
  let rest = 0
  let restCount = 0
  labels.forEach((label, i) => {
    if (keep.has(i)) {
      outLabels.push(label)
      outValues.push(values[i])
    } else {
      rest += Number(values[i]) || 0
      restCount++
    }
  })
  outLabels.push(otherLabel(restCount))
  outValues.push(rest)
  return { labels: outLabels, values: outValues }
}

defineExpose({
  getDataURL: () => chart?.getDataURL({ pixelRatio: 2, backgroundColor: cssv('--panel') }),
})

const chartEl = ref(null)
let chart = null
let resizeObserver = null

onMounted(() => {
  ensureChart()
  if (props.result) render()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
  chart = null
})

watch(
  () => [props.result, props.widgetType, props.accent],
  () => props.result && render()
)
watch(themeVersion, () => props.result && chart && render())

function ensureChart() {
  if (chart || !chartEl.value) return
  chart = echarts.init(chartEl.value, null, { renderer: 'svg' })
  resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(chartEl.value)
  chart.on('click', (params) => {
    // the synthetic "Other" bucket is not a real dimension value — never cross-filter on it
    if (props.selectable && params.name && !isOther(params.name)) {
      emit('select', { label: params.name })
    }
  })
  // debug/test handle
  chartEl.value.__lumen_chart = chart
}

function axisChrome() {
  return {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      color: cssv('--faint'),
      fontSize: 10,
      fontFamily: 'IBM Plex Mono',
    },
  }
}

function tooltipChrome(trigger) {
  return {
    trigger,
    backgroundColor: cssv('--ink'),
    borderWidth: 0,
    padding: [6, 10],
    textStyle: { color: cssv('--bg'), fontSize: 12, fontFamily: 'Plus Jakarta Sans' },
    extraCssText: 'border-radius:8px;box-shadow:' + cssv('--shadow-md') + ';',
    valueFormatter: (v) =>
      props.result?.format ? formatValue(v, props.result.format) : formatNumber(v),
  }
}

function baseCartesian(labels) {
  return {
    grid: { left: 6, right: 8, top: 14, bottom: 4, containLabel: true },
    tooltip: tooltipChrome('axis'),
    xAxis: { type: 'category', data: labels, boundaryGap: true, ...axisChrome() },
    yAxis: {
      type: 'value',
      splitNumber: 4,
      splitLine: { lineStyle: { color: cssv('--grid-line'), width: 1 } },
      axisLabel: {
        color: cssv('--faint'),
        fontSize: 10,
        fontFamily: 'IBM Plex Mono',
        formatter: (v) => formatNumber(v, { compact: true }),
      },
    },
  }
}

function buildOption() {
  const type = props.widgetType
  const palette = chartPalette()
  // single-series charts wear the user-chosen accent (palette slot)
  const c1 = palette[(props.accent || 0) % palette.length]

  if (type === 'Heatmap') return buildHeatmap(palette)
  if (type === 'Gauge') return buildGauge(palette)
  if (type === 'Scatter') return buildScatter(palette)
  if (type === 'Radar') return buildRadar(palette)
  if (type === 'Rings') return buildRings(palette)

  // fold long categorical tails into "Other"; never fold a time axis
  let { labels = [], values = [] } = props.result || {}
  if (type === 'Pie Chart' || type === 'Donut Chart' || type === 'Funnel') {
    ;({ labels, values } = foldSeries({ labels, values }, MAX_SLICES))
  } else if ((type === 'Bar Chart' || type === 'Horizontal Bar') && !isTimeSeries()) {
    ;({ labels, values } = foldSeries({ labels, values }, MAX_BARS))
  }
  // weekday series in calendar order (fold keeps pairs aligned via re-zip)
  if (labels.length && labels.every((l) => WEEKDAY_ORDER.includes(l))) {
    const zipped = labels.map((l, i) => [l, values[i]])
    zipped.sort((a, b) => WEEKDAY_ORDER.indexOf(a[0]) - WEEKDAY_ORDER.indexOf(b[0]))
    labels = zipped.map((z) => z[0])
    values = zipped.map((z) => z[1])
  }

  if (type === 'Waterfall') {
    // each value is a delta; bars float on an invisible running-balance stack
    const inflow = palette[1 % palette.length]
    const outflow = cssv('--danger')
    const bases = []
    const spans = []
    const colors = []
    let running = 0
    values.forEach((v) => {
      const n = Number(v) || 0
      bases.push(n >= 0 ? running : running + n)
      spans.push(Math.abs(n))
      colors.push(n >= 0 ? inflow : outflow)
      running += n
    })
    // closing balance
    const cats = [...labels, 'Total']
    bases.push(0)
    spans.push(Math.abs(running))
    colors.push(c1)

    const deltaAt = (i) => (i < values.length ? Number(values[i]) || 0 : running)
    const option = baseCartesian(cats)
    if (cats.length > 10) {
      option.xAxis.axisLabel = { ...option.xAxis.axisLabel, rotate: 42, fontSize: 9, hideOverlap: true }
      option.grid.bottom = 8
    }
    return {
      ...option,
      tooltip: {
        ...tooltipChrome('axis'),
        formatter: (entries) => {
          const i = entries[0].dataIndex
          const raw = deltaAt(i)
          const sign = i < values.length && raw > 0 ? '+' : ''
          return `<b>${cats[i]}</b> ${sign}${formatNumber(raw)}`
        },
      },
      series: [
        {
          type: 'bar',
          stack: 'wf',
          data: bases,
          itemStyle: { color: 'transparent' },
          emphasis: { itemStyle: { color: 'transparent' } },
          silent: true,
        },
        {
          type: 'bar',
          stack: 'wf',
          data: spans.map((value, i) => ({
            value,
            itemStyle: { color: colors[i], borderRadius: 4 },
          })),
          barMaxWidth: 34,
          label: {
            show: true,
            position: 'top',
            color: cssv('--faint'),
            fontSize: 9.5,
            fontFamily: 'IBM Plex Mono',
            formatter: ({ dataIndex }) => {
              const raw = deltaAt(dataIndex)
              const sign = dataIndex < values.length && raw > 0 ? '+' : ''
              return sign + formatNumber(raw, { compact: true })
            },
          },
        },
      ],
    }
  }

  if (type === 'Sparkline') {
    const nums = values.map((v) => Number(v) || 0)
    const last = nums.length ? nums[nums.length - 1] : 0
    const first = nums.length ? nums[0] : 0
    const change = first ? ((last - first) / Math.abs(first)) * 100 : 0
    const up = change >= 0
    return {
      grid: { left: 0, right: 0, top: '54%', bottom: 0 },
      tooltip: { ...tooltipChrome('axis'), axisPointer: { type: 'line' } },
      xAxis: { type: 'category', data: labels, show: false, boundaryGap: false },
      yAxis: { type: 'value', show: false, min: 'dataMin', max: 'dataMax' },
      series: [
        {
          type: 'line',
          data: nums,
          smooth: 0.4,
          showSymbol: false,
          lineStyle: { width: 2.4, color: c1, cap: 'round' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: echarts.color.modifyAlpha(c1, 0.3) },
              { offset: 1, color: echarts.color.modifyAlpha(c1, 0) },
            ]),
          },
        },
      ],
      graphic: [
        {
          type: 'text',
          left: 1,
          top: 2,
          style: {
            text: props.result?.format ? formatValue(last, props.result.format) : formatNumber(last),
            fill: cssv('--ink'),
            fontSize: 26,
            fontWeight: 800,
            fontFamily: 'Plus Jakarta Sans',
          },
        },
        {
          type: 'text',
          left: 2,
          top: 34,
          style: {
            text: `${up ? '▲' : '▼'} ${Math.abs(change).toFixed(1)}%${labels.length ? ` since ${labels[0]}` : ''}`,
            fill: up ? cssv('--success') : cssv('--danger'),
            fontSize: 11.5,
            fontWeight: 700,
            fontFamily: 'Plus Jakarta Sans',
          },
        },
      ],
    }
  }

  if (type === 'Horizontal Bar') {
    const muted = cssv('--baseline')
    // largest at the top
    const rev = labels.map((l, i) => [l, values[i]]).reverse()
    return {
      grid: { left: 8, right: 44, top: 6, bottom: 4, containLabel: true },
      tooltip: tooltipChrome('axis'),
      xAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: cssv('--grid-line'), width: 1 } },
        axisLabel: {
          color: cssv('--faint'),
          fontSize: 9,
          fontFamily: 'IBM Plex Mono',
          formatter: (v) => formatNumber(v, { compact: true }),
        },
      },
      yAxis: {
        type: 'category',
        data: rev.map((z) => z[0]),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: cssv('--ink-2'),
          fontSize: 11,
          fontWeight: 600,
          fontFamily: 'Plus Jakarta Sans',
          width: 110,
          overflow: 'truncate',
        },
      },
      series: [
        {
          type: 'bar',
          data: rev.map(([label, value]) => ({
            value,
            itemStyle: {
              color: isOther(label) ? muted : c1,
              borderRadius: [0, 5, 5, 0],
            },
          })),
          barMaxWidth: 18,
          cursor: props.selectable ? 'pointer' : 'default',
          label: {
            show: true,
            position: 'right',
            color: cssv('--faint'),
            fontSize: 10,
            fontFamily: 'IBM Plex Mono',
            formatter: ({ value }) => formatNumber(value, { compact: true }),
          },
        },
      ],
    }
  }

  if (type === 'Funnel') {
    return {
      tooltip: { ...tooltipChrome('item') },
      series: [
        {
          type: 'funnel',
          sort: 'descending',
          gap: 4,
          top: 8,
          bottom: 8,
          left: '6%',
          width: '88%',
          data: labels.map((label, i) => ({
            name: label,
            value: values[i],
            itemStyle: {
              color: isOther(label)
                ? cssv('--baseline')
                : echarts.color.modifyAlpha(palette[i % palette.length], Math.max(1 - i * 0.09, 0.55)),
              borderWidth: 0,
            },
          })),
          label: {
            show: true,
            position: 'inside',
            color: '#fff',
            fontWeight: 700,
            fontSize: 11.5,
            fontFamily: 'Plus Jakarta Sans',
          },
          emphasis: { label: { fontSize: 12 } },
          cursor: props.selectable ? 'pointer' : 'default',
        },
      ],
    }
  }

  if (type === 'Bar Chart') {
    const option = baseCartesian(labels)
    // crowded categorical axes get slanted, smaller labels
    if (labels.length > 10) {
      option.xAxis.axisLabel = {
        ...option.xAxis.axisLabel,
        rotate: 42,
        fontSize: 9,
        interval: 0,
        hideOverlap: true,
      }
      option.grid.bottom = 8
    }
    const muted = cssv('--baseline')
    return {
      ...option,
      series: [
        {
          type: 'bar',
          data: labels.map((label, i) => ({
            value: values[i],
            // the Other bucket must not impersonate a real category
            itemStyle: isOther(label)
              ? { color: muted, borderRadius: [5, 5, 5, 5] }
              : { color: c1, borderRadius: [5, 5, 5, 5] },
          })),
          barMaxWidth: 42,
          cursor: props.selectable ? 'pointer' : 'default',
          emphasis: { itemStyle: { color: cssv('--blue-600') } },
        },
      ],
    }
  }

  if (type === 'Line Chart' || type === 'Area Chart') {
    const isArea = type === 'Area Chart'
    const option = baseCartesian(labels)
    option.xAxis.boundaryGap = false
    return {
      ...option,
      series: [
        {
          type: 'line',
          data: values,
          smooth: 0.42,
          symbol: 'circle',
          symbolSize: 8,
          showSymbol: false,
          lineStyle: { width: 2.5, color: c1, cap: 'round', join: 'round' },
          itemStyle: { color: c1, borderColor: cssv('--panel'), borderWidth: 2 },
          areaStyle: isArea
            ? {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: echarts.color.modifyAlpha(c1, 0.28) },
                  { offset: 1, color: echarts.color.modifyAlpha(c1, 0) },
                ]),
              }
            : undefined,
        },
      ],
    }
  }

  if (type === 'Pie Chart' || type === 'Donut Chart') {
    const isDonut = type === 'Donut Chart'
    const total = values.reduce((a, v) => a + (Number(v) || 0), 0)
    return {
      tooltip: {
        ...tooltipChrome('item'),
        confine: true,
        // pin the tooltip to the top of the chart so it never lands on the
        // donut's center total; follow the cursor's x, clamped inside the chart
        position: (point, params, dom, rect, size) => {
          const chartW = size.viewSize[0]
          const tipW = size.contentSize[0]
          const x = Math.min(Math.max(point[0] - tipW / 2, 4), chartW - tipW - 4)
          return [x, 4]
        },
      },
      legend: {
        bottom: 0,
        icon: 'roundRect',
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 14,
        type: 'scroll',
        textStyle: {
          color: cssv('--ink-2'),
          fontSize: 12.5,
          fontWeight: 600,
          fontFamily: 'Plus Jakarta Sans',
        },
      },
      series: [
        {
          type: 'pie',
          radius: isDonut ? ['58%', '82%'] : '82%',
          center: ['50%', '42%'],
          padAngle: 2,
          cursor: props.selectable ? 'pointer' : 'default',
          data: labels.map((label, i) => ({
            name: label,
            value: values[i],
            itemStyle: {
              color: isOther(label) ? cssv('--baseline') : palette[i % palette.length],
            },
          })),
          itemStyle: { borderColor: cssv('--panel'), borderWidth: 2, borderRadius: 3 },
          label: { show: false },
          emphasis: {
            label: { show: false },
            itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.15)' },
          },
        },
      ],
      graphic: isDonut
        ? [
            {
              type: 'text',
              left: 'center',
              top: '36%',
              style: {
                text: formatNumber(total, { compact: total >= 100000 }),
                fill: cssv('--ink'),
                fontSize: 22,
                fontWeight: 800,
                fontFamily: 'Plus Jakarta Sans',
                textAlign: 'center',
              },
            },
            {
              type: 'text',
              left: 'center',
              top: '46%',
              style: {
                text: 'TOTAL',
                fill: cssv('--muted'),
                fontSize: 10,
                fontFamily: 'IBM Plex Mono',
                textAlign: 'center',
              },
            },
          ]
        : [],
    }
  }

  return {}
}

function buildGauge(palette) {
  const c1 = palette[(props.accent || 0) % palette.length]
  const value = Number(props.result?.value) || 0
  const target = Number(props.target) || 0
  // with a target: % achieved; without: assume the value already is a percent
  const pct = target ? (value / target) * 100 : value <= 1 ? value * 100 : value
  return {
    tooltip: {
      ...tooltipChrome('item'),
      formatter: () =>
        target
          ? `${formatNumber(value, { compact: value >= 100000 })} of ${formatNumber(target, { compact: target >= 100000 })}`
          : `${Math.round(pct)}%`,
    },
    series: [
      {
        type: 'gauge',
        startAngle: 195,
        endAngle: -15,
        center: ['50%', '68%'],
        radius: '105%',
        min: 0,
        max: 100,
        progress: { show: true, roundCap: true, width: 14, itemStyle: { color: c1 } },
        axisLine: { roundCap: true, lineStyle: { width: 14, color: [[1, cssv('--panel-3')]] } },
        pointer: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: {
          valueAnimation: true,
          formatter: (v) => `${Math.round(v)}%`,
          color: cssv('--ink'),
          fontSize: 26,
          fontWeight: 800,
          fontFamily: 'Plus Jakarta Sans',
          offsetCenter: [0, '-12%'],
        },
        data: [{ value: Math.max(0, Math.min(pct, 100)) }],
      },
    ],
  }
}

function buildScatter(palette) {
  const c1 = palette[(props.accent || 0) % palette.length]
  const points = props.result?.points || []
  const sized = points.some((p) => p.size != null)
  const maxSize = sized ? Math.max(...points.map((p) => Number(p.size) || 0), 1) : 1
  const xLabel = prettyLabel(props.result?.x_label) || 'X'
  const yLabel = prettyLabel(props.result?.y_label) || 'Y'
  const fmt = (v, f) => (f ? formatValue(v, f) : formatNumber(v))

  const valueAxis = (name, extra) => ({
    type: 'value',
    name,
    nameTextStyle: { color: cssv('--faint'), fontSize: 9.5, fontFamily: 'IBM Plex Mono' },
    splitLine: { lineStyle: { color: cssv('--grid-line'), width: 1 } },
    axisLine: { show: false },
    axisTick: { show: false },
    scale: true,
    axisLabel: {
      color: cssv('--faint'),
      fontSize: 9,
      fontFamily: 'IBM Plex Mono',
      formatter: (v) => formatNumber(v, { compact: true }),
    },
    ...extra,
  })

  return {
    grid: { left: 6, right: 18, top: 22, bottom: 6, containLabel: true },
    tooltip: {
      ...tooltipChrome('item'),
      formatter: (p) => {
        const [x, y, size] = p.value
        const lines = [
          `<b>${p.name}</b>`,
          `${xLabel}: ${fmt(x, props.result?.x_format)}`,
          `${yLabel}: ${fmt(y, props.result?.y_format)}`,
        ]
        if (sized) lines.push(`Size: ${formatNumber(size)}`)
        return lines.join('<br/>')
      },
    },
    xAxis: valueAxis(xLabel, { nameLocation: 'middle', nameGap: 22 }),
    yAxis: valueAxis(yLabel, { nameLocation: 'end', nameGap: 10 }),
    series: [
      {
        type: 'scatter',
        data: points.map((p) => ({
          name: p.label,
          value: [Number(p.x) || 0, Number(p.y) || 0, Number(p.size) || 0],
        })),
        symbolSize: sized
          ? (val) => 10 + Math.sqrt((val[2] || 0) / maxSize) * 26
          : 13,
        itemStyle: {
          color: echarts.color.modifyAlpha(c1, 0.6),
          borderColor: c1,
          borderWidth: 1.5,
        },
        emphasis: { itemStyle: { color: c1, shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.18)' } },
        cursor: props.selectable ? 'pointer' : 'default',
      },
    ],
  }
}

function buildRadar(palette) {
  const c1 = palette[(props.accent || 0) % palette.length]
  const result = props.result || {}
  let axes = []
  let webs = [] // [{name, values[]}]

  if (result.result_type === 'matrix') {
    // group_by (rows) are the spokes, group_by2 (columns) are the compared entities
    const rawRows = result.rows || []
    const rawCols = result.cols || []
    const rowTotals = rawRows.map((_r, ri) =>
      rawCols.reduce((sum, _c, ci) => sum + (Number(result.values?.[ri]?.[ci]) || 0), 0)
    )
    axes = topPairs(rawRows, rowTotals, MAX_RADAR_AXES).map((p) => p[0])
    webs = rawCols.slice(0, MAX_RADAR_SERIES).map((colName) => {
      const ci = rawCols.indexOf(colName)
      return {
        name: colName,
        values: axes.map((r) => Number(result.values?.[rawRows.indexOf(r)]?.[ci]) || 0),
      }
    })
  } else {
    const pairs = topPairs(result.labels || [], result.values || [], MAX_RADAR_AXES)
    axes = pairs.map((p) => p[0])
    webs = [{ name: 'Value', values: pairs.map((p) => p[1]) }]
  }

  const max = Math.max(1, ...webs.flatMap((w) => w.values))
  const multi = webs.length > 1
  return {
    tooltip: tooltipChrome('item'),
    legend: multi
      ? {
          bottom: 0,
          icon: 'roundRect',
          itemWidth: 10,
          itemHeight: 10,
          itemGap: 14,
          textStyle: {
            color: cssv('--ink-2'),
            fontSize: 12,
            fontWeight: 600,
            fontFamily: 'Plus Jakarta Sans',
          },
        }
      : undefined,
    radar: {
      indicator: axes.map((name) => ({ name, max: max * 1.08 })),
      radius: '64%',
      center: ['50%', multi ? '46%' : '52%'],
      splitNumber: 4,
      axisName: {
        color: cssv('--ink-2'),
        fontSize: 10.5,
        fontWeight: 600,
        fontFamily: 'Plus Jakarta Sans',
      },
      splitLine: { lineStyle: { color: cssv('--grid-line') } },
      splitArea: { areaStyle: { color: [cssv('--panel'), cssv('--panel-2')], opacity: 0.55 } },
      axisLine: { lineStyle: { color: cssv('--grid-line') } },
    },
    series: [
      {
        type: 'radar',
        data: webs.map((web, i) => {
          const color = multi ? palette[i % palette.length] : c1
          return {
            name: web.name,
            value: web.values,
            symbol: 'circle',
            symbolSize: 5,
            lineStyle: { width: 2.2, color },
            itemStyle: { color },
            areaStyle: { color: echarts.color.modifyAlpha(color, multi ? 0.14 : 0.2) },
          }
        }),
      },
    ],
  }
}

function buildRings(palette) {
  const target = Number(props.target) || 0
  const pairs = topPairs(props.result?.labels || [], props.result?.values || [], MAX_RINGS)
  const labels = pairs.map((p) => p[0])
  const raw = pairs.map((p) => p[1])
  const total = raw.reduce((a, v) => a + v, 0) || 1
  // with a target every ring is progress toward it; without, it's share of total
  const pct = raw.map((v) => Math.max(0, Math.min((target ? v / target : v / total) * 100, 100)))
  const pctByLabel = Object.fromEntries(labels.map((l, i) => [l, pct[i]]))
  const rawByLabel = Object.fromEntries(labels.map((l, i) => [l, raw[i]]))

  const ring = (data, color, z, silent) => ({
    type: 'bar',
    coordinateSystem: 'polar',
    data,
    roundCap: true,
    barGap: '-100%',
    barWidth: 11,
    itemStyle: { color },
    silent,
    z,
  })

  return {
    tooltip: {
      ...tooltipChrome('item'),
      formatter: (p) =>
        `<b>${p.seriesName}</b> ${formatNumber(rawByLabel[p.seriesName])} · ${Math.round(
          pctByLabel[p.seriesName]
        )}%`,
    },
    legend: {
      orient: 'vertical',
      right: 4,
      top: 'middle',
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 11,
      textStyle: {
        color: cssv('--ink-2'),
        fontSize: 12,
        fontWeight: 600,
        fontFamily: 'Plus Jakarta Sans',
      },
      formatter: (name) => `${name}  ${Math.round(pctByLabel[name] || 0)}%`,
    },
    polar: { radius: ['30%', '86%'], center: ['30%', '50%'] },
    angleAxis: { max: 100, startAngle: 90, show: false },
    radiusAxis: { type: 'category', data: labels, show: false },
    series: [
      // muted track behind every ring
      ring(labels.map(() => 100), cssv('--panel-3'), 1, true),
      ...labels.map((label, i) =>
        Object.assign(
          ring(
            labels.map((_l, j) => (j === i ? pct[i] : null)),
            palette[i % palette.length],
            2,
            false
          ),
          { name: label }
        )
      ),
    ],
  }
}

function buildHeatmap(palette) {
  const c1 = palette[(props.accent || 0) % palette.length]
  const rows = sortWeekdays(props.result?.rows || [])
  const cols = sortWeekdays(props.result?.cols || [])
  const rawRows = props.result?.rows || []
  const rawCols = props.result?.cols || []
  const valueAt = (r, c) => {
    const ri = rawRows.indexOf(r)
    const ci = rawCols.indexOf(c)
    return (props.result?.values?.[ri] || [])[ci] || 0
  }
  const data = []
  let maxV = 0
  rows.forEach((r, y) => {
    cols.forEach((c, x) => {
      const v = valueAt(r, c)
      maxV = Math.max(maxV, v)
      data.push([x, y, v])
    })
  })
  return {
    grid: { left: 8, right: 8, top: 8, bottom: 4, containLabel: true },
    tooltip: {
      ...tooltipChrome('item'),
      formatter: (p) => `<b>${rows[p.value[1]]} ${cols[p.value[0]]}</b> ${formatNumber(p.value[2])}`,
    },
    xAxis: {
      type: 'category',
      data: cols,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: cssv('--faint'), fontSize: 9, fontFamily: 'IBM Plex Mono' },
    },
    yAxis: {
      type: 'category',
      data: [...rows].reverse(),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: cssv('--faint'), fontSize: 9, fontFamily: 'IBM Plex Mono' },
    },
    visualMap: {
      show: false,
      min: 0,
      max: maxV || 1,
      inRange: { color: [echarts.color.modifyAlpha(c1, 0.07), c1] },
    },
    series: [
      {
        type: 'heatmap',
        // y axis is reversed for top-down reading
        data: data.map(([x, y, v]) => [x, rows.length - 1 - y, v]),
        itemStyle: { borderColor: cssv('--panel'), borderWidth: 2, borderRadius: 3 },
        emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.2)' } },
        label: { show: false },
      },
    ],
  }
}

function render() {
  ensureChart()
  if (!chart) return
  chart.setOption(buildOption(), { notMerge: true })
}
</script>
