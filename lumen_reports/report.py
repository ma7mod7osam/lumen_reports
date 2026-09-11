# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

"""Printable reports.

A dashboard becomes a paged document: a header with the company, a flowing
body in the dashboard's reading order, and page numbers in the margin.
WeasyPrint renders it. It ships with Frappe itself (a dependency of v15 and
v16), so there is nothing to install on a site and nothing that differs
between a laptop and Frappe Cloud.

Two rules shape the markup:

- Charts are drawn as SVG geometry, but every word on or around a chart is
  HTML. WeasyPrint's SVG text does no Arabic shaping or bidi, so a category
  name drawn inside the SVG comes out as disconnected, reversed letters.
- The renderer only ever fetches the bundled fonts and the site's own public
  files. A picture pointing anywhere else is left out, so a dashboard cannot
  be used to make the server request an internal address.
"""

import datetime
import html
import math
import os
import re

import frappe
from frappe import _

from lumen_reports import api, query_engine

PAPERS = {"A4": "A4", "Letter": "letter"}
MAX_BARS = 10
MAX_SLICES = 7
MAX_TABLE_ROWS = 60
MAX_MATRIX_ROWS = 14
MAX_MATRIX_COLS = 12
MAX_TREE_CHILDREN = 8
MAX_SERIES = 6

STATIC_TYPES = ("Heading", "Text", "Divider", "Image")
KPI_TYPES = ("Number Card", "Gauge")

# print on white whatever the dashboard's screen theme is: dark paper wastes
# toner and reads badly. The light presets keep their own colors.
PALETTES = {
	"default": ["#1463ff", "#0f9d7a", "#9b5bff", "#e0772c", "#d6447f", "#1f9bb3", "#c9a21b", "#5e6ad2"],
	"sand": ["#b4813c", "#6f8f4f", "#a3564a", "#4a7d8c", "#8a6ba3", "#c9a227", "#77694f", "#3f6b57"],
	"paper": ["#1f2937", "#b3382c", "#6b7280", "#b98900", "#2f6f4f", "#3b5b8c", "#8c5a3b", "#9aa1ab"],
}
BASELINE = "#ccd3e0"

ARABIC_MONTHS = [
	"يناير",
	"فبراير",
	"مارس",
	"أبريل",
	"مايو",
	"يونيو",
	"يوليو",
	"أغسطس",
	"سبتمبر",
	"أكتوبر",
	"نوفمبر",
	"ديسمبر",
]
ENGLISH_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ARABIC_WEEKDAYS = {
	"Mon": "الاثنين",
	"Tue": "الثلاثاء",
	"Wed": "الأربعاء",
	"Thu": "الخميس",
	"Fri": "الجمعة",
	"Sat": "السبت",
	"Sun": "الأحد",
}
WEEKDAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

STRINGS = {
	"en": {
		"generated": "Generated",
		"page": "Page",
		"of": "of",
		"filters": "Filters",
		"all_data": "All data",
		"no_data": "No data yet",
		"other": "Other ({0} more)",
		"of_target": "of {0}",
		"total": "Total",
		"summary": "Executive summary",
		"watch": "Worth checking",
		"prepared_for": "Prepared for {0}",
		"first_rows": "First {0} rows",
		"points": "{0} points",
		"hours": "{0}h {1}m",
		"hours_only": "{0}h",
		"minutes": "{0} min",
		"days": "{0} days",
		"not_shown": "Not shown in print",
		"na": "n/a",
		"range": "{0}: {1} to {2}",
		"value": "Value",
	},
	"ar": {
		"generated": "تاريخ الإنشاء",
		"page": "صفحة",
		"of": "من",
		"filters": "التصفية",
		"all_data": "كل البيانات",
		"no_data": "لا توجد بيانات بعد",
		"other": "أخرى ({0} إضافية)",
		"of_target": "من {0}",
		"total": "الإجمالي",
		"summary": "الملخص التنفيذي",
		"watch": "يستحق المتابعة",
		"prepared_for": "مخصص لـ {0}",
		"first_rows": "أول {0} صفا",
		"points": "{0} نقطة",
		"hours": "{0} س {1} د",
		"hours_only": "{0} س",
		"minutes": "{0} دقيقة",
		"days": "{0} يوم",
		"not_shown": "لا يظهر في النسخة المطبوعة",
		"na": "غير متاح",
		"range": "{0}: من {1} إلى {2}",
		"value": "القيمة",
	},
}


def _t(lang, key, *args):
	text = STRINGS.get(lang, STRINGS["en"]).get(key) or STRINGS["en"][key]
	return text.format(*args) if args else text


def _e(value) -> str:
	return html.escape(str(value if value is not None else ""), quote=True)


_STRONG_RTL = re.compile("[֐-ࣿיִ-﷿ﹰ-ﻼ]")
_STRONG_LTR = re.compile("[A-Za-zÀ-ɏͰ-ϿЀ-ӿ]")
_AUTO_DIR = re.compile(r' dir="auto"([^>]*)>([^<]*)')


def _direction(text):
	"""The direction of a piece of text, taken from its first strong letter,
	which is what dir="auto" does in a browser."""
	for ch in text:
		if _STRONG_RTL.match(ch):
			return "rtl"
		if _STRONG_LTR.match(ch):
			return "ltr"
	return None


def _resolve_dirs(markup: str) -> str:
	"""WeasyPrint ignores dir="auto", so an English name ending in a full stop
	on an Arabic page prints as ".West View Software Ltd". Resolve every
	auto direction to a real one from the text it wraps."""

	def fix(m):
		d = _direction(html.unescape(m.group(2)))
		attr = f' dir="{d}"' if d else ""
		return f"{attr}{m.group(1)}>{m.group(2)}"

	return _AUTO_DIR.sub(fix, markup)


# ---------------------------------------------------------------- options


def _options(raw) -> dict:
	raw = frappe.parse_json(raw) if isinstance(raw, str) else (raw or {})

	def flag(key, default):
		value = raw.get(key, default)
		if isinstance(value, str):
			return value.lower() in ("1", "true", "yes")
		return bool(value)

	return {
		"paper": raw.get("paper") if raw.get("paper") in PAPERS else "A4",
		"lang": "ar" if raw.get("lang") == "ar" else "en",
		"header": flag("header", True),
		"page_numbers": flag("page_numbers", True),
		"summary": flag("summary", False),
		"filter_values": raw.get("filter_values") if isinstance(raw.get("filter_values"), dict) else {},
		"prepared_for": str(raw.get("prepared_for") or "")[:120],
	}


# ---------------------------------------------------------------- numbers


def _full(n) -> str:
	"""1,090,597 above a thousand, up to two decimals below it."""
	n = float(n)
	if abs(n) >= 1000:
		return f"{round(n):,}"
	text = f"{n:,.2f}".rstrip("0").rstrip(".")
	return text or "0"


def _compact(n) -> str:
	n = float(n)
	for size, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
		if abs(n) >= size:
			return f"{n / size:.1f}".rstrip("0").rstrip(".") + suffix
	return f"{n:.1f}".rstrip("0").rstrip(".") or "0"


def _value(v, fmt, lang, compact=False) -> str:
	"""Mirror of the app's formatValue, so a printed number reads exactly as
	it does on screen. Digits are always Western."""
	if v is None or v == "":
		return _t(lang, "na")
	try:
		n = float(v)
	except (TypeError, ValueError):
		return str(v)
	if math.isnan(n):
		return _t(lang, "na")
	if fmt == "clock":
		h = int(math.floor(n % 24))
		m = int(round((n - math.floor(n)) * 60))
		return f"{h:02d}:{m:02d}"
	if fmt == "hours":
		h = int(math.floor(n))
		m = int(round((n - h) * 60))
		return _t(lang, "hours", h, m) if m else _t(lang, "hours_only", h)
	if fmt == "minutes":
		return _t(lang, "minutes", round(n))
	if fmt == "days":
		return _t(lang, "days", _full(round(n * 10) / 10))
	if fmt == "percent":
		return f"{_full(round(n * 1000) / 10)}%"
	return _compact(n) if compact else _full(n)


def _label(label, grain, lang) -> str:
	"""Readable axis labels: 2026-01 becomes Jan 2026 (يناير 2026 in Arabic),
	Mon becomes الاثنين. Anything else is shown as the data has it."""
	text = str(label if label is not None else "")
	if not text or text in ("None", "null"):
		return "(blank)" if lang == "en" else "(فارغ)"
	try:
		if grain == "month" and len(text) == 7:
			year, month = int(text[:4]), int(text[5:7])
			names = ARABIC_MONTHS if lang == "ar" else ENGLISH_MONTHS
			return f"{names[month - 1]} {year}"
		if grain == "day" and len(text) == 10:
			d = datetime.date.fromisoformat(text)
			names = ARABIC_MONTHS if lang == "ar" else ENGLISH_MONTHS
			return f"{d.day} {names[d.month - 1]}"
		if grain == "weekday" and lang == "ar":
			return ARABIC_WEEKDAYS.get(text, text)
	except (ValueError, IndexError):
		pass
	return text


# ---------------------------------------------------------------- colors


def _palette(theme) -> list:
	theme = theme or {}
	colors = list(PALETTES.get(theme.get("preset"), PALETTES["default"]))
	brand = str(theme.get("brand") or "")
	if len(brand) == 7 and brand.startswith("#"):
		colors[0] = brand
	return colors


def _tint(hex_color, alpha) -> str:
	"""A hex color at an opacity, as rgba, for heatmap shading."""
	h = hex_color.lstrip("#")
	r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
	return f"rgba({r},{g},{b},{alpha:.2f})"


# ---------------------------------------------------------------- blocks


def _grain(query, key="group_by"):
	return ((query or {}).get(key) or {}).get("time_grain")


def _fold(labels, values, keep):
	"""Largest `keep` items, the rest folded into one Other entry."""
	pairs = [(label, float(v or 0)) for label, v in zip(labels, values)]
	if len(pairs) <= keep + 1:
		return pairs, None
	pairs.sort(key=lambda p: p[1], reverse=True)
	head, tail = pairs[:keep], pairs[keep:]
	return head, (len(tail), sum(v for _, v in tail))


def _kpi_tile(widget, result, palette, lang):
	fmt = result.get("format")
	value = result.get("value")
	target = (widget.get("style") or {}).get("target")
	extra = ""
	if widget["widget_type"] == "Gauge" and target:
		try:
			pct = max(0.0, min(1.0, float(value or 0) / float(target)))
			extra = (
				f'<div class="kbar"><i style="width:{pct * 100:.1f}%;background:{palette[0]}"></i></div>'
				f'<div class="ksub">{_e(_t(lang, "of_target", _value(target, fmt, lang)))}</div>'
			)
		except (TypeError, ValueError, ZeroDivisionError):
			pass
	return (
		'<div class="kpi">'
		f'<div class="kval num">{_e(_value(value, fmt, lang))}</div>'
		f'<div class="klbl" dir="auto">{_e(widget.get("title"))}</div>{extra}</div>'
	)


def _bars(result, query, palette, lang):
	labels = result.get("labels") or []
	values = result.get("values") or []
	if not labels:
		return None
	grain = _grain(query)
	pairs, other = _fold(labels, values, MAX_BARS)
	if not grain:
		pairs.sort(key=lambda p: p[1], reverse=True)
	top = max([abs(v) for _, v in pairs] + [other[1] if other else 0] + [1e-9])
	fmt = result.get("format")
	rows = []
	for i, (label, v) in enumerate(pairs):
		color = palette[i % len(palette)] if len(pairs) <= len(palette) else palette[0]
		rows.append(
			f'<tr><td class="bl" dir="auto">{_e(_label(label, grain, lang))}</td>'
			f'<td class="bt"><i style="width:{abs(v) / top * 100:.1f}%;background:{color}"></i></td>'
			f'<td class="bv num">{_e(_value(v, fmt, lang, compact=True))}</td></tr>'
		)
	if other:
		rows.append(
			f'<tr><td class="bl muted">{_e(_t(lang, "other", other[0]))}</td>'
			f'<td class="bt"><i style="width:{other[1] / top * 100:.1f}%;background:{BASELINE}"></i></td>'
			f'<td class="bv num">{_e(_value(other[1], fmt, lang, compact=True))}</td></tr>'
		)
	return '<table class="bars">' + "".join(rows) + "</table>"


def _donut(result, palette, lang):
	labels = result.get("labels") or []
	values = result.get("values") or []
	if not labels:
		return None
	pairs, other = _fold(labels, values, MAX_SLICES)
	pairs.sort(key=lambda p: p[1], reverse=True)
	slices = [(label, v, palette[i % len(palette)]) for i, (label, v) in enumerate(pairs)]
	if other:
		slices.append((_t(lang, "other", other[0]), other[1], BASELINE))
	total = sum(max(v, 0) for _, v, _c in slices) or 1
	fmt = result.get("format")

	# arcs drawn as stroked circles: each slice is a dash of its share of the
	# circumference, offset by everything before it
	radius, width = 42, 18
	circ = 2 * math.pi * radius
	arcs, offset = [], 0.0
	for _label_text, v, color in slices:
		length = max(v, 0) / total * circ
		arcs.append(
			f'<circle cx="60" cy="60" r="{radius}" fill="none" stroke="{color}" stroke-width="{width}" '
			f'stroke-dasharray="{length:.2f} {circ - length:.2f}" stroke-dashoffset="{-offset:.2f}" '
			'transform="rotate(-90 60 60)"/>'
		)
		offset += length
	legend = "".join(
		f'<tr><td><i class="sw" style="background:{color}"></i></td>'
		f'<td class="ll" dir="auto">{_e(_label(label_text, None, lang))}</td>'
		f'<td class="lv num">{_e(_value(v, fmt, lang, compact=True))}</td>'
		f'<td class="lp num">{max(v, 0) / total * 100:.1f}%</td></tr>'
		for label_text, v, color in slices
	)
	# a table rather than flex: the legend then takes exactly the width left
	# beside the ring instead of pushing out of a half-width card
	return (
		'<table class="donut"><tr><td class="dcell">'
		f'<div class="dsvg"><svg width="120" height="120" viewBox="0 0 120 120">{"".join(arcs)}</svg>'
		f'<div class="dtot"><b class="num">{_e(_value(total, fmt, lang, compact=True))}</b>'
		f"<span>{_e(_t(lang, 'total'))}</span></div></div></td>"
		f'<td><table class="legend">{legend}</table></td></tr></table>'
	)


def _axis_labels(labels, grain, lang, count=6):
	"""A handful of evenly spaced labels under a time chart, as HTML so Arabic
	month names shape correctly. In a right-to-left page the row runs from the
	right, matching the mirrored chart."""
	if not labels:
		return ""
	n = len(labels)
	picks = sorted({round(i * (n - 1) / max(1, min(count, n) - 1)) for i in range(min(count, n))})
	cells = "".join(f"<span>{_e(_label(labels[i], grain, lang))}</span>" for i in picks)
	return f'<div class="xaxis">{cells}</div>'


def _series_svg(series, width, height, palette, kind, rtl, stacked=False):
	"""Lines, areas or bars for one or more aligned series. Geometry only."""
	count = max(len(s["values"]) for s in series)
	if not count:
		return ""
	if stacked:
		totals = [sum(float(s["values"][i] or 0) for s in series) for i in range(count)]
		top = max(totals + [1e-9])
	else:
		top = max([float(v or 0) for s in series for v in s["values"]] + [1e-9])
	pad_top, pad_bottom = 6, 4
	usable = height - pad_top - pad_bottom

	def y(v):
		return pad_top + usable - (float(v or 0) / top) * usable

	parts = [
		f'<line x1="0" y1="{pad_top + usable * f:.1f}" x2="{width}" y2="{pad_top + usable * f:.1f}" '
		'stroke="#e9edf4" stroke-width="1"/>'
		for f in (0.0, 0.5, 1.0)
	]
	if kind == "bar":
		slot = width / count
		base = [0.0] * count
		group = len(series) if not stacked else 1
		for si, s in enumerate(series):
			color = s.get("color") or palette[si % len(palette)]
			for i, v in enumerate(s["values"]):
				v = float(v or 0)
				bw = slot * 0.66 / group
				x = i * slot + slot * 0.17 + (0 if stacked else si * bw)
				y0 = y(base[i]) if stacked else y(0)
				y1 = y(base[i] + v) if stacked else y(v)
				parts.append(
					f'<rect x="{x:.1f}" y="{min(y0, y1):.1f}" width="{bw:.1f}" height="{abs(y0 - y1):.1f}" '
					f'rx="2" fill="{color}"/>'
				)
				if stacked:
					base[i] += v
	else:
		step = width / max(1, count - 1)
		for si, s in enumerate(series):
			color = s.get("color") or palette[si % len(palette)]
			points = [(i * step if count > 1 else width / 2, y(v)) for i, v in enumerate(s["values"])]
			line = " ".join(f"{x:.1f},{yy:.1f}" for x, yy in points)
			if kind == "area" and len(series) == 1:
				area = f"0,{pad_top + usable} " + line + f" {points[-1][0]:.1f},{pad_top + usable}"
				parts.append(f'<polygon points="{area}" fill="{color}" fill-opacity="0.14"/>')
			parts.append(
				f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2.2" '
				'stroke-linejoin="round" stroke-linecap="round"/>'
			)
	body = "".join(parts)
	if rtl:
		# time runs right to left for an Arabic reader
		body = f'<g transform="translate({width},0) scale(-1,1)">{body}</g>'
	# the height is pinned in CSS too: given only a width, WeasyPrint scales an
	# SVG by its viewBox ratio and a half-width chart comes out a third as tall
	return (
		f'<svg class="chart" width="100%" height="{height}" style="height:{height}px" '
		f'viewBox="0 0 {width} {height}" preserveAspectRatio="none">{body}</svg>'
	)


def _y_scale(top, fmt, lang):
	return (
		'<div class="yscale">'
		f'<span class="num">{_e(_value(top, fmt, lang, compact=True))}</span>'
		f'<span class="num">{_e(_value(top / 2, fmt, lang, compact=True))}</span>'
		"<span class=\"num\">0</span></div>"
	)


def _timeseries(result, query, wtype, palette, lang, compact=False):
	labels = result.get("labels") or []
	values = result.get("values") or []
	if not labels:
		return None
	grain = _grain(query)
	kind = "bar" if wtype in ("Bar Chart", "Waterfall", "Stacked Bar") else (
		"area" if wtype in ("Area Chart", "Sparkline") else "line"
	)
	top = max([float(v or 0) for v in values] + [1e-9])
	svg = _series_svg([{"values": values}], 600, 150, palette, kind, lang == "ar")
	return (
		f'<div class="ts">{_y_scale(top, result.get("format"), lang)}<div class="tsc">{svg}'
		f"{_axis_labels(labels, grain, lang, 4 if compact else 6)}</div></div>"
	)


def _matrix(result, query, wtype, palette, lang):
	rows = result.get("rows") or []
	cols = result.get("cols") or []
	values = result.get("values") or []
	if not rows or not cols:
		return None
	grain_r, grain_c = _grain(query), _grain(query, "group_by2")
	fmt = result.get("format")

	# a time axis split into a few series reads best as the chart it was on
	# screen: one line per series, or stacked bars, with an HTML legend
	if grain_r and wtype in ("Line Chart", "Area Chart", "Bar Chart", "Stacked Bar") and len(cols) <= MAX_SERIES:
		series = [
			{"values": [(values[r][c] if c < len(values[r]) else 0) for r in range(len(rows))], "color": palette[c % len(palette)]}
			for c in range(len(cols))
		]
		kind = "line" if wtype in ("Line Chart", "Area Chart") else "bar"
		stacked = wtype == "Stacked Bar"
		if stacked:
			top = max(sum(float(s["values"][i] or 0) for s in series) for i in range(len(rows)))
		else:
			top = max(float(v or 0) for s in series for v in s["values"])
		svg = _series_svg(series, 600, 150, palette, kind, lang == "ar", stacked=stacked)
		legend = "".join(
			f'<span><i class="sw" style="background:{palette[c % len(palette)]}"></i>'
			f'<span dir="auto">{_e(_label(cols[c], grain_c, lang))}</span></span>'
			for c in range(len(cols))
		)
		return (
			f'<div class="ts">{_y_scale(top or 1e-9, fmt, lang)}<div class="tsc">{svg}'
			f'{_axis_labels(rows, grain_r, lang)}</div></div><div class="hlegend">{legend}</div>'
		)

	# anything else prints as a shaded grid: a table of the actual numbers,
	# each cell tinted by its size
	row_idx = list(range(min(len(rows), MAX_MATRIX_ROWS)))
	col_idx = list(range(min(len(cols), MAX_MATRIX_COLS)))
	if grain_r == "weekday":
		row_idx.sort(key=lambda i: WEEKDAY_ORDER.index(rows[i]) if rows[i] in WEEKDAY_ORDER else 99)
	top = max([float(values[r][c] or 0) for r in row_idx for c in col_idx if c < len(values[r])] + [1e-9])
	head = "".join(f'<th class="num">{_e(_label(cols[c], grain_c, lang))}</th>' for c in col_idx)
	body = []
	for r in row_idx:
		cells = []
		for c in col_idx:
			v = values[r][c] if c < len(values[r]) else 0
			alpha = 0.06 + 0.8 * (float(v or 0) / top)
			ink = "#ffffff" if alpha > 0.55 else "#1f2937"
			cells.append(
				f'<td class="num" style="background:{_tint(palette[0], alpha)};color:{ink}">'
				f"{_e(_value(v, fmt, lang, compact=True))}</td>"
			)
		body.append(f'<tr><th dir="auto">{_e(_label(rows[r], grain_r, lang))}</th>{"".join(cells)}</tr>')
	return f'<table class="heat"><thead><tr><th></th>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def _scatter(result, palette, lang):
	points = result.get("points") or []
	if not points:
		return None
	xs = [float(p.get("x") or 0) for p in points]
	ys = [float(p.get("y") or 0) for p in points]
	sizes = [float(p.get("size") or 0) for p in points]
	x0, x1 = min(xs), max(xs) or 1
	y0, y1 = min(ys), max(ys) or 1
	smax = max(sizes + [1e-9])
	w, h = 600, 180

	def sx(v):
		return 10 + (v - x0) / ((x1 - x0) or 1) * (w - 20)

	def sy(v):
		return h - 10 - (v - y0) / ((y1 - y0) or 1) * (h - 20)

	dots = "".join(
		f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="{3 + (math.sqrt(s / smax) * 7 if s else 1):.1f}" '
		f'fill="{palette[0]}" fill-opacity="0.55" stroke="{palette[0]}" stroke-width="1"/>'
		for x, y, s in zip(xs, ys, sizes)
	)
	grid = "".join(
		f'<line x1="0" y1="{h * f:.1f}" x2="{w}" y2="{h * f:.1f}" stroke="#e9edf4"/>' for f in (0.25, 0.5, 0.75)
	)
	body = grid + dots
	if lang == "ar":
		body = f'<g transform="translate({w},0) scale(-1,1)">{body}</g>'
	fmt_x, fmt_y = result.get("x_format"), result.get("y_format")
	x_range = _t(
		lang, "range", result.get("x_label") or "x", _value(x0, fmt_x, lang, True), _value(x1, fmt_x, lang, True)
	)
	y_range = _t(
		lang, "range", result.get("y_label") or "y", _value(y0, fmt_y, lang, True), _value(y1, fmt_y, lang, True)
	)
	# these lines are sentences in the page's language wrapping a field name,
	# so they take the page's direction rather than the field name's
	d = "rtl" if lang == "ar" else "ltr"
	return (
		f'<svg class="chart" width="100%" height="{h}" style="height:{h}px" viewBox="0 0 {w} {h}" '
		f'preserveAspectRatio="none">{body}</svg>'
		f'<div class="xaxis"><span dir="{d}">{_e(x_range)}</span><span dir="{d}">{_e(y_range)}</span>'
		f'<span>{_e(_t(lang, "points", len(points)))}</span></div>'
	)


def _tree(result, lang):
	nodes = result.get("nodes") or []
	if not nodes:
		return None
	fmt = result.get("format")
	rows = []
	# the indent goes on the page's starting side. A logical inline-start would
	# follow the label's own direction, and an English label on an Arabic page
	# would then indent on the wrong side
	side = "right" if lang == "ar" else "left"

	def walk(items, depth):
		for node in items[: (MAX_TREE_CHILDREN * 2 if depth == 0 else MAX_TREE_CHILDREN)]:
			rows.append(
				f'<tr class="d{depth}"><td dir="auto" style="padding-{side}:{8 + depth * 16}px">'
				f"{_e(node.get('label'))}</td>"
				f'<td class="num">{_e(_value(node.get("value"), fmt, lang))}</td>'
				f'<td class="num">{float(node.get("share") or 0) * 100:.1f}%</td></tr>'
			)
			if depth < 1 and node.get("children"):
				walk(node["children"], depth + 1)

	walk(nodes, 0)
	levels = " / ".join(str(level) for level in (result.get("levels") or []))
	return (
		f'<table class="grid tree"><thead><tr><th dir="auto">{_e(levels)}</th>'
		f'<th class="num">{_e(_t(lang, "value"))}</th><th class="num">%</th></tr></thead>'
		f'<tbody>{"".join(rows)}</tbody></table>'
	)


def _table(result, lang):
	columns = result.get("columns") or []
	data = result.get("rows") or []
	if not columns:
		return None
	keys = [c.get("fieldname") or c.get("key") or c.get("label") for c in columns]
	numeric = {
		k
		for c, k in zip(columns, keys)
		if (c.get("fieldtype") or "") in ("Int", "Float", "Currency", "Percent")
	}
	head = "".join(
		f'<th class="{"num" if k in numeric else ""}" dir="auto">{_e(c.get("label") or k)}</th>'
		for c, k in zip(columns, keys)
	)
	body = []
	for row in data[:MAX_TABLE_ROWS]:
		cells = []
		for k in keys:
			v = row.get(k) if isinstance(row, dict) else None
			if k in numeric:
				cells.append(f'<td class="num">{_e(_value(v, None, lang))}</td>')
			else:
				cells.append(f'<td dir="auto">{_e(v if v is not None else "")}</td>')
		body.append("<tr>" + "".join(cells) + "</tr>")
	note = ""
	if len(data) > MAX_TABLE_ROWS:
		note = f'<div class="note">{_e(_t(lang, "first_rows", MAX_TABLE_ROWS))}</div>'
	return f'<table class="grid"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>{note}'


def _chart_body(widget, result, palette, lang, compact=False):
	wtype = widget["widget_type"]
	query = widget.get("query") or {}
	kind = result.get("result_type")
	if kind == "rows":
		return _table(result, lang)
	if kind == "tree":
		return _tree(result, lang)
	if kind == "points":
		return _scatter(result, palette, lang)
	if kind == "matrix":
		return _matrix(result, query, wtype, palette, lang)
	if kind == "series":
		if _grain(query):
			return _timeseries(result, query, wtype, palette, lang, compact)
		if wtype in ("Pie Chart", "Donut Chart"):
			return _donut(result, palette, lang)
		return _bars(result, query, palette, lang)
	return None


def _static(widget, lang):
	style = widget.get("style") or {}
	wtype = widget["widget_type"]
	if wtype == "Heading":
		level = max(1, min(3, int(style.get("level") or 1)))
		sub = f'<div class="hsub" dir="auto">{_e(style.get("subtext"))}</div>' if style.get("subtext") else ""
		return f'<div class="sec lv{level}"><div class="htxt" dir="auto">{_e(style.get("text"))}</div>{sub}</div>'
	if wtype == "Text":
		if not style.get("text"):
			return ""
		cls = "note-block framed" if style.get("framed") else "note-block"
		return f'<div class="{cls}" dir="auto">{_e(style.get("text"))}</div>'
	if wtype == "Divider":
		label = f'<span dir="auto">{_e(style.get("text"))}</span>' if style.get("text") else ""
		return f'<div class="divider">{label}<i></i></div>'
	src = _image_src(style.get("url"))
	if not src:
		return ""
	return f'<div class="picture"><img src="{_e(src)}" alt=""/></div>'


def _image_src(url):
	"""Only the site's own public files make it into print."""
	url = str(url or "").strip()
	if url.startswith("data:image/"):
		return url
	if url.startswith("/files/") and ".." not in url:
		path = frappe.get_site_path("public", url.lstrip("/"))
		if os.path.isfile(path):
			return "file://" + os.path.realpath(path)
	return None


# ---------------------------------------------------------------- document


def _font_dir():
	return frappe.get_app_path("lumen_reports", "public", "fonts")


def _font_faces():
	d = _font_dir()
	faces = [
		("Plus Jakarta Sans", 400, "plus-jakarta-sans-latin-400-normal.woff2"),
		("Plus Jakarta Sans", 700, "plus-jakarta-sans-latin-700-normal.woff2"),
		("Plus Jakarta Sans", 800, "plus-jakarta-sans-latin-800-normal.woff2"),
		("IBM Plex Sans Arabic", 400, "ibm-plex-sans-arabic-arabic-400-normal.woff2"),
		("IBM Plex Sans Arabic", 700, "ibm-plex-sans-arabic-arabic-700-normal.woff2"),
		("IBM Plex Mono", 500, "ibm-plex-mono-latin-500-normal.woff2"),
	]
	return "\n".join(
		f'@font-face {{ font-family: "{family}"; font-weight: {weight}; '
		f'src: url("file://{os.path.join(d, name)}") format("woff2"); }}'
		for family, weight, name in faces
	)


def _safe_fetcher(url, *args, **kwargs):
	from weasyprint.urls import URLFetchingError, default_url_fetcher

	if url.startswith("data:"):
		return default_url_fetcher(url, *args, **kwargs)
	if url.startswith("file://"):
		path = os.path.realpath(url[len("file://") :])
		allowed = (
			os.path.realpath(_font_dir()),
			os.path.realpath(frappe.get_site_path("public", "files")),
		)
		if any(path == root or path.startswith(root + os.sep) for root in allowed):
			return default_url_fetcher(url, *args, **kwargs)
	raise URLFetchingError(f"Blocked in report rendering: {url[:80]}")


def _company():
	name = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
	logo = None
	if name and frappe.db.exists("DocType", "Company") and frappe.db.exists("Company", name):
		logo = _image_src(frappe.db.get_value("Company", name, "company_logo"))
	if not name:
		name = frappe.db.get_single_value("Website Settings", "app_name") or frappe.local.site
	return name, logo


def _fmt_date(dt, lang):
	names = ARABIC_MONTHS if lang == "ar" else ENGLISH_MONTHS
	comma = "،" if lang == "ar" else ","
	return f"{dt.day} {names[dt.month - 1]} {dt.year}{comma} {dt.hour:02d}:{dt.minute:02d}"


def _filters_line(doc, filter_values, lang):
	defs = {f.get("name"): f for f in frappe.parse_json(doc.filters_json or "[]") or []}
	parts = []
	for key, value in (filter_values or {}).items():
		if value in (None, "", [], "__all__") or key not in defs:
			continue
		parts.append(f"{defs[key].get('label') or key}: {value}")
	return " · ".join(parts) if parts else _t(lang, "all_data")


def _collect(doc, filter_values):
	"""Run every data widget once, as the current user, the same way the
	viewer does. A widget that fails is kept with its error, not dropped."""
	layout = {item.get("widget_id"): item for item in frappe.parse_json(doc.layout_json or "[]") or []}
	items = []
	for w in doc.widgets:
		widget = {
			"widget_id": w.widget_id,
			"title": w.title,
			"widget_type": w.widget_type,
			"query": frappe.parse_json(w.query_json or "{}"),
			"style": frappe.parse_json(w.style_json or "{}"),
		}
		pos = layout.get(w.widget_id) or {"x": 0, "y": 999, "w": 12, "h": 5}
		entry = {"widget": widget, "pos": pos, "result": None, "error": None}
		if widget["widget_type"] not in STATIC_TYPES and widget["query"].get("doctype"):
			try:
				extra = api._build_filters_from_values(doc, w, filter_values or {})
				entry["result"] = query_engine.execute(widget["query"], extra)
			except Exception as e:
				frappe.clear_last_message()
				entry["error"] = str(e)[:200]
		items.append(entry)
	items.sort(key=lambda it: (it["pos"].get("y", 0), it["pos"].get("x", 0)))
	return items


def _summary_html(items, lang):
	"""An analyst's read of the numbers, only when an AI key is configured.
	Written from this person's own results, so it never says more than
	they are allowed to see."""
	from lumen_reports import ai, copilot

	key, model, _source = ai._resolve_key()
	if not key:
		return ""
	executed = [
		{"widget": it["widget"], "result": it["result"]}
		for it in items
		if it["result"] and it["widget"]["widget_type"] not in STATIC_TYPES
	][:12]
	if not executed:
		return ""
	ask = "Summarize this report for an executive."
	if lang == "ar":
		ask += (
			" Write the headline, findings and watch items in formal Modern Standard Arabic, with"
			" Western digits (0-9) and no diacritics."
		)
	analysis = ai._analyze(ask, executed, {}, key, model)
	if not analysis:
		return ""
	findings = "".join(f'<li dir="auto">{_e(copilot._plain(f, 240))}</li>' for f in analysis["findings"])
	watch = ""
	if analysis.get("watch"):
		items_html = "".join(f'<li dir="auto">{_e(copilot._plain(x, 240))}</li>' for x in analysis["watch"])
		watch = f'<div class="swatch-t">{_e(_t(lang, "watch"))}</div><ul class="watch">{items_html}</ul>'
	return (
		f'<div class="summary"><div class="eyebrow">{_e(_t(lang, "summary"))}</div>'
		f'<div class="shead" dir="auto">{_e(copilot._plain(analysis["headline"], 240))}</div>'
		f"<ul>{findings}</ul>{watch}</div>"
	)


def _body(items, palette, lang):
	"""The dashboard in reading order. Number cards gather into a strip,
	half-width charts pair up two to a row, everything else runs full width."""
	out = []
	kpis = []
	pending_half = None

	def flush_kpis():
		if kpis:
			out.append('<div class="kpis">' + "".join(kpis) + "</div>")
			kpis.clear()

	def flush_half():
		nonlocal pending_half
		if pending_half:
			out.append(f'<div class="row1">{pending_half}</div>')
			pending_half = None

	for it in items:
		w = it["widget"]
		wtype = w["widget_type"]
		if wtype in STATIC_TYPES:
			flush_kpis()
			flush_half()
			block = _static(w, lang)
			if block:
				out.append(block)
			continue
		if wtype in KPI_TYPES and (it["result"] or {}).get("result_type") == "number":
			flush_half()
			kpis.append(_kpi_tile(w, it["result"], palette, lang))
			continue
		flush_kpis()
		half = bool(
			(it["pos"].get("w") or 12) <= 6 and it["result"] and it["result"].get("result_type") == "series"
		)
		if it["error"]:
			body = f'<div class="empty">{_e(_t(lang, "not_shown"))}</div>'
		elif it["result"] is None:
			body = f'<div class="empty">{_e(_t(lang, "no_data"))}</div>'
		else:
			body = _chart_body(w, it["result"], palette, lang, compact=half) or (
				f'<div class="empty">{_e(_t(lang, "no_data"))}</div>'
			)
		card = f'<div class="card"><div class="ctitle" dir="auto">{_e(w.get("title"))}</div>{body}</div>'
		if half:
			if pending_half:
				out.append(f'<div class="row2">{pending_half}{card}</div>')
				pending_half = None
			else:
				pending_half = card
		else:
			flush_half()
			out.append(card)
	flush_kpis()
	flush_half()
	return "\n".join(out)


def _css(options, palette):
	lang = options["lang"]
	accent = palette[0]
	page_size = PAPERS[options["paper"]]
	numbers = ""
	if options["page_numbers"]:
		side = "left" if lang == "ar" else "right"
		numbers = (
			f'@bottom-{side} {{ content: "{_t(lang, "page")} " counter(page) " {_t(lang, "of")} " counter(pages); '
			'font-family: "IBM Plex Sans Arabic", "Plus Jakarta Sans"; font-size: 8pt; color: #98a1b2; }'
		)
	brand_side = "right" if lang == "ar" else "left"
	# the gap between a bar's label and the bar sits on the page's own side;
	# a logical padding would follow an English label's direction instead
	bar_gap_side = "left" if lang == "ar" else "right"
	return f"""
{_font_faces()}
@page {{
  size: {page_size};
  margin: 15mm 14mm 17mm;
  @bottom-{brand_side} {{ content: "Lumen Reports"; font-family: "Plus Jakarta Sans"; font-size: 8pt; color: #98a1b2; }}
  {numbers}
}}
html {{ font-size: 10pt; }}
body {{
  margin: 0;
  color: #0c1322;
  font-family: "Plus Jakarta Sans", "IBM Plex Sans Arabic", sans-serif;
  line-height: 1.45;
}}
html[lang="ar"] body {{ font-family: "IBM Plex Sans Arabic", "Plus Jakarta Sans", sans-serif; }}
.num {{ font-family: "IBM Plex Mono", "Plus Jakarta Sans", monospace; font-variant-numeric: tabular-nums; }}
.muted {{ color: #98a1b2; }}
/* a cell or label keeps the page's alignment even when its own text runs the
   other way, so an English name on an Arabic page still lines up with its
   column; its punctuation is placed by its own direction */
html[lang="ar"] [dir="ltr"]:not(.htxt):not(.hsub):not(.note-block) {{ text-align: right; }}
html[lang="en"] [dir="rtl"]:not(.htxt):not(.hsub):not(.note-block) {{ text-align: left; }}

.rhead {{ padding-bottom: 9pt; border-bottom: 2pt solid {accent}; margin-bottom: 12pt; }}
.rhead td {{ vertical-align: middle; padding: 0; }}
.rhead .logo {{ width: 1%; padding-inline-end: 9pt; }}
.rhead .rmeta {{ width: 38%; }}
.rhead img {{ height: 26pt; max-width: 90pt; object-fit: contain; display: block; }}
.rtitle {{ font-size: 16pt; font-weight: 800; letter-spacing: -0.01em; }}
html[lang="ar"] .rtitle {{ letter-spacing: 0; }}
.rsub {{ font-size: 8pt; color: #687386; margin-top: 2pt; }}
.rmeta {{ text-align: end; font-size: 8pt; color: #687386; }}
.rmeta b {{ display: block; color: #3a4456; font-size: 9pt; }}

.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 7pt; margin-bottom: 10pt; }}
.kpi {{ border: 0.75pt solid #e4e8f0; border-radius: 6pt; padding: 7pt 9pt; break-inside: avoid; }}
.kval {{ font-size: 13.5pt; font-weight: 600; }}
.klbl {{ font-size: 7.5pt; color: #687386; font-weight: 700; margin-top: 1pt; }}
.ksub {{ font-size: 7pt; color: #98a1b2; margin-top: 2pt; }}
.kbar {{ height: 3pt; background: #eef1f6; border-radius: 2pt; margin-top: 5pt; overflow: hidden; }}
.kbar i {{ display: block; height: 3pt; }}

.card {{ border: 0.75pt solid #e4e8f0; border-radius: 6pt; padding: 9pt 11pt; margin-bottom: 10pt; break-inside: avoid; }}
.ctitle {{ font-size: 9.5pt; font-weight: 700; margin-bottom: 7pt; }}
/* minmax(0, 1fr): a chart's drawn width must never force its column wider,
   or the second card of a pair runs off the page edge */
.row2 {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8pt; }}
.row1 {{ display: block; }}
.empty {{ color: #98a1b2; font-size: 8.5pt; padding: 10pt 0; }}
.note {{ color: #98a1b2; font-size: 7.5pt; margin-top: 4pt; }}

table {{ border-collapse: collapse; width: 100%; }}
/* fixed layout so a long name is cut short with an ellipsis instead of
   running into its bar */
.bars {{ table-layout: fixed; }}
.bars td {{ padding: 2.2pt 0; font-size: 8pt; vertical-align: middle; }}
.bars .bl {{ width: 32%; padding-{bar_gap_side}: 7pt; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.bars .bt {{ width: 54%; }}
.bars .bt i {{ display: block; height: 7pt; border-radius: 1.5pt; }}
.bars .bv {{ width: 14%; text-align: end; padding-inline-start: 6pt; font-size: 7.5pt; color: #3a4456; }}

.donut td {{ vertical-align: middle; padding: 0; }}
.donut .dcell {{ width: 128px; padding-inline-end: 10pt; }}
.dsvg {{ position: relative; width: 120px; height: 120px; }}
.dtot {{ position: absolute; top: 40px; left: 0; width: 120px; text-align: center; }}
.dtot b {{ display: block; font-size: 10pt; }}
.dtot span {{ font-size: 6.5pt; color: #98a1b2; }}
.legend td {{ font-size: 8pt; padding: 1.8pt 0; }}
.legend .ll {{ padding-inline: 5pt; }}
.legend .lv, .legend .lp {{ text-align: end; color: #3a4456; padding-inline-start: 7pt; }}
.sw {{ display: inline-block; width: 7pt; height: 7pt; border-radius: 1.5pt; vertical-align: middle; }}

.ts {{ display: flex; gap: 6pt; }}
.yscale {{ display: flex; flex-direction: column; justify-content: space-between; font-size: 6.5pt; color: #98a1b2;
  height: 150px; text-align: end; min-width: 26pt; }}
.tsc {{ flex: 1; min-width: 0; }}
.chart {{ display: block; width: 100%; max-width: 100%; }}
.card {{ min-width: 0; overflow: hidden; }}
.xaxis {{ display: flex; justify-content: space-between; font-size: 6.8pt; color: #98a1b2; margin-top: 3pt; gap: 4pt; }}
.hlegend {{ display: flex; flex-wrap: wrap; gap: 4pt 12pt; font-size: 7.5pt; color: #3a4456; margin-top: 6pt; }}
.hlegend > span {{ display: inline-flex; align-items: center; gap: 4pt; }}

.grid th {{ font-size: 7pt; text-transform: uppercase; letter-spacing: 0.05em; color: #98a1b2; font-weight: 600;
  text-align: start; border-bottom: 0.75pt solid #d4dae5; padding: 4pt 5pt; }}
html[lang="ar"] .grid th {{ letter-spacing: 0; text-transform: none; }}
.grid td {{ font-size: 8pt; padding: 3.4pt 5pt; border-bottom: 0.5pt solid #eef1f6; }}
.grid .num {{ text-align: end; }}
.grid thead {{ display: table-header-group; }}
.grid tr {{ break-inside: avoid; }}
.tree tr.d0 td {{ font-weight: 700; background: #f7f9fc; }}

.heat th {{ font-size: 7pt; color: #687386; font-weight: 600; padding: 3pt 4pt; text-align: start; }}
.heat thead th {{ text-align: center; }}
.heat td {{ font-size: 7pt; text-align: center; padding: 3.5pt 2pt; border: 1.5pt solid #ffffff; border-radius: 3pt; }}

.sec {{ margin: 12pt 0 7pt; break-after: avoid; }}
.sec .htxt {{ font-weight: 800; letter-spacing: -0.01em; }}
.sec.lv1 .htxt {{ font-size: 14pt; }}
.sec.lv2 .htxt {{ font-size: 12pt; }}
.sec.lv3 .htxt {{ font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.08em; color: #687386; }}
html[lang="ar"] .sec .htxt {{ letter-spacing: 0; text-transform: none; }}
.hsub {{ font-size: 8.5pt; color: #687386; margin-top: 1pt; }}
.note-block {{ font-size: 9pt; color: #3a4456; white-space: pre-wrap; margin-bottom: 10pt; }}
.note-block.framed {{ border: 0.75pt solid #e4e8f0; border-radius: 6pt; padding: 9pt 11pt; }}
.divider {{ display: flex; align-items: center; gap: 8pt; margin: 10pt 0; font-size: 7.5pt; color: #98a1b2;
  text-transform: uppercase; letter-spacing: 0.08em; }}
html[lang="ar"] .divider {{ letter-spacing: 0; text-transform: none; }}
.divider i {{ flex: 1; height: 0.75pt; background: #e4e8f0; display: block; }}
.picture {{ margin-bottom: 10pt; text-align: center; break-inside: avoid; }}
.picture img {{ max-width: 100%; max-height: 180pt; }}

.summary {{ border-inline-start: 2.5pt solid {accent}; background: #f7f9fc; padding: 9pt 12pt; margin-bottom: 12pt;
  border-radius: 4pt; break-inside: avoid; }}
.eyebrow {{ font-size: 7pt; text-transform: uppercase; letter-spacing: 0.1em; color: #98a1b2; font-weight: 600; }}
html[lang="ar"] .eyebrow {{ letter-spacing: 0; text-transform: none; }}
.shead {{ font-size: 10.5pt; font-weight: 700; margin: 3pt 0 5pt; }}
.summary ul {{ margin: 0; padding-inline-start: 13pt; font-size: 8.5pt; color: #3a4456; }}
.summary li {{ margin: 1.5pt 0; }}
.swatch-t {{ font-size: 8pt; font-weight: 700; color: #c9821b; margin-top: 6pt; }}
.summary ul.watch {{ color: #9a6412; }}
"""


def render_html(doc, options) -> str:
	options = _options(options)
	lang = options["lang"]
	theme = frappe.parse_json(doc.theme_json or "{}") or {}
	palette = _palette(theme)
	items = _collect(doc, options["filter_values"])
	# a board that opens with a heading repeating its own title would print
	# that title twice under the report header
	if options["header"] and items:
		first = items[0]["widget"]
		text = str((first.get("style") or {}).get("text") or "").strip()
		if first["widget_type"] == "Heading" and text == str(doc.dashboard_title or "").strip():
			items = items[1:]

	header = ""
	if options["header"]:
		company, logo = _company()
		logo_html = f'<img src="{_e(logo)}" alt=""/>' if logo else ""
		sub = _filters_line(doc, options["filter_values"], lang)
		prepared = ""
		if options["prepared_for"]:
			prepared = f"<div>{_e(_t(lang, 'prepared_for', options['prepared_for']))}</div>"
		# a table, not flex: WeasyPrint sizes a flex title to its narrowest
		# word in left-to-right pages and breaks "Retail Sales" in two
		logo_cell = f'<td class="logo">{logo_html}</td>' if logo_html else ""
		header = (
			f'<div class="rhead"><table><tr>{logo_cell}'
			f'<td class="who"><div class="rtitle" dir="auto">{_e(doc.dashboard_title)}</div>'
			f'<div class="rsub" dir="auto">{_e(sub)}</div></td>'
			f'<td class="rmeta"><b dir="auto">{_e(company)}</b>'
			f"<div>{_e(_t(lang, 'generated'))} {_e(_fmt_date(frappe.utils.now_datetime(), lang))}</div>"
			f"{prepared}</td></tr></table></div>"
		)

	summary = _summary_html(items, lang) if options["summary"] else ""
	direction = "rtl" if lang == "ar" else "ltr"
	return _resolve_dirs(
		f'<!doctype html><html lang="{lang}" dir="{direction}"><head><meta charset="utf-8">'
		f"<title>{_e(doc.dashboard_title)}</title><style>{_css(options, palette)}</style></head>"
		f"<body>{header}{summary}{_body(items, palette, lang)}</body></html>"
	)


def render_pdf(doc, options) -> bytes:
	import weasyprint

	markup = render_html(doc, options)
	return weasyprint.HTML(string=markup, url_fetcher=_safe_fetcher).write_pdf()


def _filename(doc, options):
	stamp = frappe.utils.nowdate()
	suffix = "-ar" if _options(options)["lang"] == "ar" else ""
	return f"{doc.route_slug}-{stamp}{suffix}.pdf"


# ---------------------------------------------------------------- endpoints


@frappe.whitelist()
def download(slug: str, options: str | dict | None = None, inline: int | str = 0):
	"""The dashboard as a PDF, rendered with the current person's permissions.
	`inline` shows it in the browser's viewer instead of downloading."""
	doc = api._get_dashboard_doc(slug)  # read permission enforced here
	pdf = render_pdf(doc, options)
	frappe.local.response.filename = _filename(doc, options)
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf" if frappe.utils.cint(inline) else "download"
