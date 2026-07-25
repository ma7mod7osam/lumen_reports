function escapeCell(value) {
  if (value === null || value === undefined) return ''
  const s = String(value)
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s
}

export function toCsv(rows) {
  return rows.map((row) => row.map(escapeCell).join(',')).join('\n')
}

export function downloadFile(filename, content, mime = 'text/csv;charset=utf-8') {
  const blob = content instanceof Blob ? content : new Blob(['﻿' + content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 4000)
}

export function downloadDataUrl(filename, dataUrl) {
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
}

/** CSV for a widget result (series or rows). */
export function resultToCsv(result, title = 'data') {
  if (!result) return null
  if (result.result_type === 'series') {
    return toCsv([[title, 'value'], ...result.labels.map((l, i) => [l, result.values[i]])])
  }
  if (result.result_type === 'rows') {
    const cols = result.columns
    return toCsv([
      cols.map((c) => c.label),
      ...result.rows.map((r) => cols.map((c) => r[c.fieldname])),
    ])
  }
  if (result.result_type === 'number') {
    return toCsv([[title], [result.value]])
  }
  if (result.result_type === 'matrix') {
    // one row per heatmap row, one column per heatmap column
    return toCsv([
      [title, ...result.cols],
      ...result.rows.map((r, i) => [r, ...(result.values[i] || [])]),
    ])
  }
  if (result.result_type === 'tree') {
    // one row per node, indented by level, with its share of the grand total
    const rows = [['Level', title, 'Value', 'Share']]
    const walk = (nodes) => {
      for (const n of nodes || []) {
        rows.push([n.level_name || n.level, '  '.repeat(n.level) + n.label, n.value, (n.share * 100).toFixed(1) + '%'])
        walk(n.children)
      }
    }
    walk(result.nodes)
    return toCsv(rows)
  }
  if (result.result_type === 'points') {
    const sized = result.points.some((p) => p.size != null)
    const header = [title, result.x_label || 'x', result.y_label || 'y']
    if (sized) header.push('size')
    return toCsv([
      header,
      ...result.points.map((p) => {
        const row = [p.label, p.x, p.y]
        if (sized) row.push(p.size)
        return row
      }),
    ])
  }
  return null
}
