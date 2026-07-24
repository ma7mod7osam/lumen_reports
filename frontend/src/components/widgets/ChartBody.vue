<template>
  <div ref="chartEl" class="h-full w-full" style="min-height: 120px"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { formatNumber } from '@/lib/palette'
import { cssv, chartPalette, themeVersion } from '@/lib/theme'

const props = defineProps({
  widgetType: { type: String, required: true },
  result: { type: Object, default: null },
  selectable: { type: Boolean, default: false },
  // the widget's query — used to detect time series (never folded)
  query: { type: Object, default: null },
})
const emit = defineEmits(['select'])

// ---- high-cardinality handling ------------------------------------------
// beyond a handful of identities a pie is unreadable and a bar axis is a
// picket fence: fold the tail into a muted, non-interactive "Other" bucket
const MAX_SLICES = 8 // pie/donut: 7 + Other
const MAX_BARS = 20 // bar: 19 + Other

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
  () => [props.result, props.widgetType],
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
    valueFormatter: (v) => formatNumber(v),
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
  const c1 = palette[0]

  // fold long categorical tails into "Other"; never fold a time axis
  let { labels = [], values = [] } = props.result || {}
  if (type === 'Pie Chart' || type === 'Donut Chart') {
    ;({ labels, values } = foldSeries({ labels, values }, MAX_SLICES))
  } else if (type === 'Bar Chart' && !isTimeSeries()) {
    ;({ labels, values } = foldSeries({ labels, values }, MAX_BARS))
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

function render() {
  ensureChart()
  if (!chart) return
  chart.setOption(buildOption(), { notMerge: true })
}
</script>
