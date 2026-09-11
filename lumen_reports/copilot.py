# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

"""The studio copilot.

One turn is the person's message plus the board exactly as the studio holds
it, unsaved edits included. The model answers with a short reply and a list
of typed operations. Every operation is checked here and simulated on a copy
of the board, and what comes back is the board it would produce. The studio
applies that in one step, so a single Undo takes the whole turn back.

Nothing is saved here. The person sees the list of changes before any of
them touch the canvas.

Anything that touches data goes through the same engine as the rest of the
app: new widgets are built by ask_ai's pipeline, changed widgets by
modify_ai_widget's, and summaries only read results the person is allowed
to see.
"""

import copy
import json
import math
import re

import frappe
from frappe import _

from lumen_reports import ai, api, query_engine

COLS = 12
MAX_OPS = 20
MAX_ROW = 300
HISTORY_TURNS = 10
MAX_SUMMARY_WIDGETS = 12

STATIC_TYPES = ("Heading", "Text", "Divider", "Image")
# the model cannot invent an image URL, so it may place every element but that one
AI_ELEMENTS = ("Heading", "Text", "Divider")

THEME_PRESETS = {
	"light": "Lumen Light, the default clean light look with a blue accent",
	"dark": "Lumen Dark, near-black navy with a bright blue accent",
	"emerald": "Emerald, dark green with teal and lime accents",
	"midnight": "Midnight, deep indigo dark with a periwinkle accent",
	"sand": "Sand, warm beige light with ochre and olive",
	"paper": "Paper, editorial white with black ink, one red accent and flat cards",
}
CARD_STYLES = ("flat", "outlined", "elevated", "glass")
DENSITIES = ("compact", "comfort")
FONTS = ("", "system", "serif", "mono")
SURFACES = ("solid", "gradient", "tint")
TINTS = ("blue", "green", "amber", "violet")

# which chart types can show the data a widget already returns. A pie of a
# monthly series or a line across unrelated categories is a wrong chart, not
# a style choice, so a swap outside the family is refused rather than applied.
TYPE_FAMILIES = {
	"number": {"Number Card", "Gauge"},
	"category": {
		"Bar Chart",
		"Horizontal Bar",
		"Pie Chart",
		"Donut Chart",
		"Funnel",
		"Rings",
		"Radar",
		"Progress Bars",
	},
	"time": {"Line Chart", "Area Chart", "Bar Chart", "Sparkline", "Waterfall"},
	"matrix": {"Bar Chart", "Stacked Bar", "Line Chart", "Area Chart", "Heatmap", "Radar"},
	"points": {"Scatter"},
	"tree": {"Tree Report"},
	"rows": {"Table"},
}

SIZES = {
	"Number Card": (3, 2),
	"Gauge": (3, 3),
	"Sparkline": (3, 3),
	"Heading": (12, 1),
	"Divider": (12, 1),
	"Text": (12, 2),
	"Table": (12, 5),
	"Heatmap": (12, 5),
	"Tree Report": (12, 7),
}


# ---------------------------------------------------------------- text


_DIACRITICS = re.compile("[ً-ْٰ]")
_ARABIC = re.compile("[؀-ۿ]")


def _plain(text, limit=400) -> str:
	"""Copy a person reads. No Arabic diacritics and no dashes as punctuation,
	which the product's own writing rules forbid in anything it generates."""
	text = _DIACRITICS.sub("", str(text or "")).strip()
	comma = "، " if _ARABIC.search(text) else ", "
	text = re.sub(r"\s*[—–]\s*", comma, text)
	text = re.sub(r"\s{2,}", " ", text)
	return text[:limit]


# ---------------------------------------------------------------- board


def _shape(widget) -> str:
	"""The kind of result a widget's query produces."""
	t = widget.get("widget_type")
	if t in STATIC_TYPES:
		return "element"
	q = widget.get("query") or {}
	if q.get("shape") == "tree":
		return "tree"
	if q.get("aggregate_y"):
		return "points"
	if q.get("group_by2"):
		return "matrix"
	if q.get("group_by"):
		return "time" if (q.get("group_by") or {}).get("time_grain") else "category"
	if q.get("fields") and not q.get("aggregate"):
		return "rows"
	return "number"


def _read_board(board) -> dict:
	"""Normalise the studio's board into the state the simulator works on."""
	board = frappe.parse_json(board) if isinstance(board, str) else (board or {})
	widgets = []
	for w in board.get("widgets") or []:
		if not isinstance(w, dict) or not w.get("widget_id"):
			continue
		widgets.append(
			{
				"widget_id": str(w["widget_id"]),
				"title": w.get("title") or "",
				"widget_type": w.get("widget_type") or "Bar Chart",
				"query": w.get("query") or {},
				"style": w.get("style") or {},
			}
		)
	types = {w["widget_id"]: w["widget_type"] for w in widgets}
	layout = {}
	for item in board.get("layout") or []:
		wid = str((item or {}).get("widget_id") or "")
		if wid in types:
			# a heading or a rule may be one row tall; clamping it to a chart's
			# minimum would quietly grow every heading on the board
			layout[wid] = _clamp(item, element=types[wid] in STATIC_TYPES)
	# a widget the studio has not placed yet still needs a cell
	for w in widgets:
		if w["widget_id"] not in layout:
			width, height = SIZES.get(w["widget_type"], (6, 5))
			layout[w["widget_id"]] = {"x": 0, "y": _bottom(layout), "w": width, "h": height}
	return {
		"title": str(board.get("title") or ""),
		"theme": board.get("theme") if isinstance(board.get("theme"), dict) else {},
		"widgets": widgets,
		"layout": layout,
	}


def _clamp(item, element=False) -> dict:
	def num(key, default):
		try:
			return int(round(float(item.get(key, default))))
		except (TypeError, ValueError):
			return default

	w = max(2, min(COLS, num("w", 6)))
	h = max(1 if element else 2, min(24, num("h", 5)))
	x = max(0, min(COLS - w, num("x", 0)))
	y = max(0, min(MAX_ROW, num("y", 0)))
	return {"x": x, "y": y, "w": w, "h": h}


def _bottom(layout) -> int:
	return max((p["y"] + p["h"] for p in layout.values()), default=0)


def _collides(a, b) -> bool:
	return (
		a["x"] < b["x"] + b["w"]
		and b["x"] < a["x"] + a["w"]
		and a["y"] < b["y"] + b["h"]
		and b["y"] < a["y"] + a["h"]
	)


def _compact(layout: dict) -> dict:
	"""Resolve overlaps, then float everything up to close the gaps, without
	changing the reading order the plan asked for."""
	order = sorted(layout.items(), key=lambda kv: (kv[1]["y"], kv[1]["x"]))
	placed = []
	for wid, item in order:
		item = dict(item)
		while any(_collides(item, other) for _, other in placed):
			item["y"] += 1
		placed.append((wid, item))
	for i, (_wid, item) in enumerate(placed):
		while item["y"] > 0:
			trial = dict(item, y=item["y"] - 1)
			if any(_collides(trial, other) for j, (_, other) in enumerate(placed) if j != i):
				break
			item["y"] -= 1
	return {wid: item for wid, item in placed}


def _shift_down(layout: dict, rows: int):
	for item in layout.values():
		item["y"] += rows


def _new_id(prefix="cp") -> str:
	return prefix + frappe.generate_hash(length=6)


def _describe(widget, pos) -> dict:
	"""What the model is told about one widget: enough to reason about it,
	nothing it could mistake for data."""
	d = {
		"id": widget["widget_id"],
		"title": widget.get("title"),
		"type": widget.get("widget_type"),
		"x": pos["x"],
		"y": pos["y"],
		"w": pos["w"],
		"h": pos["h"],
	}
	if widget["widget_type"] in STATIC_TYPES:
		d["text"] = str((widget.get("style") or {}).get("text") or "")[:80]
		return d
	q = widget.get("query") or {}
	d["source"] = (
		f"{q.get('doctype')} (lines of {q['parent_doctype']})" if q.get("parent_doctype") else q.get("doctype")
	)
	agg = q.get("aggregate") or {}
	if agg:
		d["measure"] = " ".join(p for p in (agg.get("function"), agg.get("field")) if p)
	group = q.get("group_by") or {}
	if group:
		d["by"] = group.get("field") + (f" per {group['time_grain']}" if group.get("time_grain") else "")
	if q.get("group_by2"):
		d["split_by"] = (q.get("group_by2") or {}).get("field")
	d["shape"] = _shape(widget)
	return d


# ---------------------------------------------------------------- prompt


def _guide() -> str:
	presets = "\n".join(f"    {k}: {v}" for k, v in THEME_PRESETS.items())
	families = "\n".join(f"    {k}: {', '.join(sorted(v))}" for k, v in TYPE_FAMILIES.items())
	return (
		"OPERATIONS (use only these, each is a JSON object with an \"op\" and a \"label\"):\n"
		'- {"op": "set_layout", "items": [{"id", "x", "y", "w", "h"}]}\n'
		"    Move and resize. List every widget whose position changes. x + w must not exceed 12.\n"
		"    Sizes that read well: number card 3x2 (four in a row), gauge 3x3, chart 6x5 (two in a row)\n"
		"    or 8x5 beside a 4x5 companion, wide chart or table 12x5, heading or divider 12x1.\n"
		'- {"op": "set_theme", "theme": {...}}  Only the keys you change:\n'
		"    preset, one of:\n" + presets + "\n"
		'    brand: a hex color such as "#2bc79b". card: flat, outlined, elevated or glass.\n'
		"    radius: 0 to 28. density: compact or comfort. font: \"\" (default), system, serif or mono.\n"
		"    surface: solid, gradient or tint.\n"
		'- {"op": "retitle", "id", "title"}\n'
		'- {"op": "set_type", "id", "widget_type"}  Only within the widget\'s shape family:\n'
		+ families
		+ "\n"
		'- {"op": "set_style", "id", "accent": 0-7}  chart color slot. Number cards take "tint":\n'
		"    blue, green, amber or violet instead.\n"
		'- {"op": "remove", "id"}\n'
		'- {"op": "add_element", "element": "Heading" | "Text" | "Divider", "text", "subtext" (Heading),\n'
		'    "level": 1 | 2 | 3 (Heading), "position": "top" | "bottom"}\n'
		'- {"op": "add_widgets", "request", "position": "top" | "bottom"}  New KPIs, charts or tables\n'
		"    built from data. \"request\" is a precise English description naming the measures,\n"
		"    dimensions and period. One operation may ask for several widgets.\n"
		'- {"op": "change_data", "id", "instruction"}  Change what one widget measures, filters or\n'
		"    groups by. \"instruction\" in English.\n"
		'- {"op": "add_summary", "position": "top" | "bottom"}  An executive summary written from the\n'
		"    board's real numbers.\n"
		'- {"op": "explain"}  They asked what the numbers show, not for a change.\n'
		'- {"op": "rename_dashboard", "title"}\n\n'
		"RULES\n"
		"- Every operation has a \"label\": one short line telling the person what it does, in THEIR\n"
		"  language, naming widgets by title and never by id.\n"
		"- \"reply\" is one or two short sentences in THEIR language.\n"
		"- If they wrote Arabic in any dialect, write formal Modern Standard Arabic with Western digits\n"
		"  (0-9) and no diacritics. In any language, never use the em dash.\n"
		"- Use only ids from the widget list. Never invent one.\n"
		"- Arranging a board (tidy, organize, arrange, رتب, نظم): number cards across the first row,\n"
		"  the main trend chart wide under them with a companion beside it, then the remaining charts\n"
		"  in pairs, tables and wide charts last, and any heading directly above what it introduces.\n"
		"- Dark mode means a dark preset (dark, midnight or emerald). Match color words to the\n"
		"  closest preset, and add a brand color only when they name a specific color.\n"
		"- When the message is ambiguous in a way that changes the result, return instead\n"
		'  {"clarify": "<one short question in their language>", "options": ["<2 to 4 short answers>"]}.\n'
		"- A greeting or thanks needs no operations: return an empty list with a reply.\n"
		"- Add 2 or 3 \"suggestions\": short next steps, in their language, that would genuinely\n"
		"  improve THIS board.\n\n"
		'Respond with ONLY JSON: {"reply": "...", "operations": [...], "suggestions": [...]}'
	)


def _history_block(history) -> str:
	if not history:
		return ""
	lines = "\n".join(f"{h.get('role', 'user')}: {str(h.get('text', ''))[:300]}" for h in history)
	return "Conversation so far:\n" + lines + "\n\n"


# ---------------------------------------------------------------- operations


class _Turn:
	"""Everything one turn needs while it simulates operations."""

	def __init__(self, state, prompt, key, model):
		self.state = state
		self.prompt = prompt
		self.key = key
		self.model = model
		self.changes = []
		self.notes = []
		self.analysis = None
		self.layout_touched = False

	def widget(self, wid):
		return next((w for w in self.state["widgets"] if w["widget_id"] == str(wid or "")), None)

	def done(self, op, fallback):
		self.changes.append(_plain(op.get("label") or fallback, 160))

	def refuse(self, text):
		self.notes.append(_plain(text, 200))

	def base_doctype(self):
		counts = {}
		for w in self.state["widgets"]:
			q = w.get("query") or {}
			dt = q.get("parent_doctype") or q.get("doctype")
			if dt:
				counts[dt] = counts.get(dt, 0) + 1
		return max(counts, key=counts.get) if counts else None

	def place(self, new_widgets, position):
		"""Put freshly built widgets on the grid, as a block at the top or the
		bottom, packed the same way ask_ai packs a new dashboard."""
		layout = self.state["layout"]
		packed = ai._auto_layout(new_widgets, start_y=0)
		block = max((p["y"] + p["h"] for p in packed), default=0)
		if position == "top":
			_shift_down(layout, block)
			start = 0
		else:
			start = _bottom(layout)
		for p in packed:
			layout[p["widget_id"]] = {"x": p["x"], "y": p["y"] + start, "w": p["w"], "h": p["h"]}
		if position == "top":
			self.state["widgets"][0:0] = new_widgets
		else:
			self.state["widgets"].extend(new_widgets)


def _op_set_layout(turn, op):
	moved = 0
	for item in op.get("items") or []:
		if not isinstance(item, dict):
			continue
		w = turn.widget(item.get("id"))
		if not w:
			continue
		turn.state["layout"][w["widget_id"]] = _clamp(item, element=w["widget_type"] in STATIC_TYPES)
		moved += 1
	if moved:
		turn.layout_touched = True
		turn.done(op, _("Rearranged {0} widgets").format(moved))


def _op_set_theme(turn, op):
	raw = op.get("theme") if isinstance(op.get("theme"), dict) else {}
	clean = {}
	if raw.get("preset") in THEME_PRESETS:
		clean["preset"] = raw["preset"]
	brand = str(raw.get("brand") or "").strip()
	if re.fullmatch(r"#[0-9a-fA-F]{6}", brand):
		clean["brand"] = brand.lower()
	if raw.get("card") in CARD_STYLES:
		clean["card"] = raw["card"]
	if raw.get("density") in DENSITIES:
		clean["density"] = raw["density"]
	if raw.get("font") in FONTS:
		clean["font"] = raw["font"]
	if raw.get("surface") in SURFACES:
		clean["surface"] = raw["surface"]
	try:
		if raw.get("radius") not in (None, ""):
			clean["radius"] = max(0, min(28, int(raw["radius"])))
	except (TypeError, ValueError):
		pass
	if not clean:
		turn.refuse(_("The theme change did not name anything the theme panel offers."))
		return
	turn.state["theme"] = {**turn.state["theme"], **clean}
	turn.done(op, _("Changed the theme"))


def _op_retitle(turn, op):
	w = turn.widget(op.get("id"))
	title = _plain(op.get("title"), 120)
	if not w or not title:
		return
	w["title"] = title
	if w["widget_type"] == "Heading":
		w["style"] = {**w["style"], "text": title}
	turn.done(op, _("Renamed a widget to {0}").format(title))


def _op_set_type(turn, op):
	w = turn.widget(op.get("id"))
	target = op.get("widget_type")
	if not w or not target or w["widget_type"] == target:
		return
	family = TYPE_FAMILIES.get(_shape(w), set())
	if target not in family:
		turn.refuse(
			_("{0} cannot be shown as {1}: its data does not fit that chart.").format(w["title"], target)
		)
		return
	w["widget_type"] = target
	turn.done(op, _("Changed {0} to {1}").format(w["title"], target))


def _op_set_style(turn, op):
	w = turn.widget(op.get("id"))
	if not w or w["widget_type"] in STATIC_TYPES:
		return
	style = dict(w["style"])
	if w["widget_type"] == "Number Card":
		if op.get("tint") not in TINTS:
			return
		style["tint"] = op["tint"]
	else:
		try:
			style["accent"] = max(0, min(7, int(op.get("accent"))))
		except (TypeError, ValueError):
			return
	w["style"] = style
	turn.done(op, _("Recolored {0}").format(w["title"]))


def _op_remove(turn, op):
	w = turn.widget(op.get("id"))
	if not w:
		return
	turn.state["widgets"] = [x for x in turn.state["widgets"] if x["widget_id"] != w["widget_id"]]
	turn.state["layout"].pop(w["widget_id"], None)
	turn.layout_touched = True
	turn.done(op, _("Removed {0}").format(w["title"]))


def _op_add_element(turn, op):
	kind = op.get("element")
	if kind not in AI_ELEMENTS:
		return
	text = _plain(op.get("text"), 600)
	if kind != "Divider" and not text:
		return
	style = {"text": text}
	if kind == "Heading":
		style["align"] = "left"
		try:
			style["level"] = max(1, min(3, int(op.get("level") or 1)))
		except (TypeError, ValueError):
			style["level"] = 1
		if op.get("subtext"):
			style["subtext"] = _plain(op["subtext"], 160)
	elif kind == "Text":
		style.update({"align": "left", "size": "md", "framed": True})
	width, height = SIZES[kind]
	if kind == "Text":
		height = max(2, min(5, 1 + math.ceil(len(text) / 140)))
	element = {
		"widget_id": _new_id(),
		"title": text[:60] or kind,
		"widget_type": kind,
		"query": {},
		"style": style,
	}
	layout = turn.state["layout"]
	if op.get("position") == "top":
		_shift_down(layout, height)
		layout[element["widget_id"]] = {"x": 0, "y": 0, "w": width, "h": height}
		turn.state["widgets"].insert(0, element)
	else:
		layout[element["widget_id"]] = {"x": 0, "y": _bottom(layout), "w": width, "h": height}
		turn.state["widgets"].append(element)
	turn.done(op, _("Added a {0}").format(kind.lower()))


def _op_add_widgets(turn, op):
	request = str(op.get("request") or "").strip()
	if not request:
		return
	base = turn.base_doctype()
	if base:
		request = f"This dashboard is built on {base}. {request}"
	try:
		built = ai.ask_ai(
			request,
			existing_titles=[w["title"] for w in turn.state["widgets"] if w.get("title")],
			answered=True,
			analyze=False,
		)
	except Exception as e:
		frappe.clear_last_message()
		turn.refuse(_("Could not build the new widgets: {0}").format(_plain(str(e), 160)))
		return
	fresh = []
	for entry in built.get("widgets") or []:
		spec = entry.get("widget") or {}
		fresh.append(
			{
				"widget_id": _new_id(),
				"title": spec.get("title") or "New widget",
				"widget_type": spec.get("widget_type"),
				"query": spec.get("query") or {},
				"style": spec.get("style") or {},
			}
		)
		if entry.get("empty"):
			turn.refuse(_("{0} has no data yet. It was added anyway so it fills in when data arrives.").format(
				spec.get("title") or "A widget"
			))
	if not fresh:
		turn.refuse(_("No widget could be built for that request."))
		return
	turn.place(fresh, "top" if op.get("position") == "top" else "bottom")
	turn.done(op, _("Added {0} widgets").format(len(fresh)))


def _op_change_data(turn, op):
	w = turn.widget(op.get("id"))
	instruction = str(op.get("instruction") or "").strip()
	if not w or not instruction:
		return
	if w["widget_type"] in STATIC_TYPES:
		turn.refuse(_("{0} carries no data to change.").format(w["title"] or w["widget_type"]))
		return
	try:
		entry = ai.modify_ai_widget(instruction, w)
	except Exception as e:
		frappe.clear_last_message()
		turn.refuse(_("Could not change {0}: {1}").format(w["title"], _plain(str(e), 160)))
		return
	spec = entry.get("widget") or {}
	w["title"] = spec.get("title") or w["title"]
	w["widget_type"] = spec.get("widget_type") or w["widget_type"]
	w["query"] = spec.get("query") or w["query"]
	turn.done(op, _("Changed the data behind {0}").format(w["title"]))


def _board_results(turn):
	"""Run the board's data widgets once, as this person, for a narrative."""
	out = []
	for w in turn.state["widgets"]:
		if w["widget_type"] in STATIC_TYPES or not (w.get("query") or {}).get("doctype"):
			continue
		try:
			out.append({"widget": w, "result": query_engine.execute(w["query"])})
		except Exception:
			frappe.clear_last_message()
		if len(out) >= MAX_SUMMARY_WIDGETS:
			break
	return out


def _read_numbers(turn, question):
	executed = _board_results(turn)
	if not executed:
		return None, []
	doctypes = []
	for item in executed:
		q = item["widget"]["query"]
		dt = q.get("parent_doctype") or q.get("doctype")
		if dt and dt not in doctypes:
			doctypes.append(dt)
	context = ai._data_context(doctypes[:3])
	return ai._analyze(question, executed, context, turn.key, turn.model), executed


def _op_add_summary(turn, op):
	analysis, _executed = _read_numbers(turn, turn.prompt or "Summarize this dashboard for an executive")
	if not analysis:
		turn.refuse(_("There was not enough data on the board to write a summary from."))
		return
	lines = [_plain(analysis["headline"], 220), ""]
	lines += ["• " + _plain(f, 220) for f in analysis["findings"]]
	text = "\n".join(lines)
	height = max(3, min(7, 2 + math.ceil(len(analysis["findings"]) * 0.8)))
	element = {
		"widget_id": _new_id(),
		"title": "Executive summary",
		"widget_type": "Text",
		"query": {},
		"style": {"text": text, "align": "left", "size": "md", "framed": True},
	}
	layout = turn.state["layout"]
	if op.get("position") == "bottom":
		layout[element["widget_id"]] = {"x": 0, "y": _bottom(layout), "w": 12, "h": height}
		turn.state["widgets"].append(element)
	else:
		_shift_down(layout, height)
		layout[element["widget_id"]] = {"x": 0, "y": 0, "w": 12, "h": height}
		turn.state["widgets"].insert(0, element)
	turn.done(op, _("Added an executive summary"))


def _op_explain(turn, op):
	analysis, _executed = _read_numbers(turn, turn.prompt)
	if not analysis:
		turn.refuse(_("There is no data on this board to read yet."))
		return
	turn.analysis = {
		"headline": _plain(analysis["headline"], 220),
		"findings": [_plain(f, 220) for f in analysis["findings"]],
		"watch": [_plain(x, 220) for x in analysis.get("watch") or []],
	}


def _op_rename_dashboard(turn, op):
	title = _plain(op.get("title"), 120)
	if not title:
		return
	turn.state["title"] = title
	turn.done(op, _("Renamed the dashboard to {0}").format(title))


OPERATIONS = {
	"set_layout": _op_set_layout,
	"set_theme": _op_set_theme,
	"retitle": _op_retitle,
	"set_type": _op_set_type,
	"set_style": _op_set_style,
	"remove": _op_remove,
	"add_element": _op_add_element,
	"add_widgets": _op_add_widgets,
	"change_data": _op_change_data,
	"add_summary": _op_add_summary,
	"explain": _op_explain,
	"rename_dashboard": _op_rename_dashboard,
}


# ---------------------------------------------------------------- endpoint


@frappe.whitelist()
def copilot(
	prompt: str,
	board: str | dict,
	history: str | list | None = None,
	selected: str | None = None,
	answered: bool | str = False,
):
	"""One copilot turn. Returns the reply, the list of changes, and the board
	those changes would produce. The studio applies it; nothing is saved here."""
	ai._require_user()
	# the board arrives from the browser and a summary executes its queries, so
	# this is ad-hoc querying: the same builder gate as the studio's live preview
	api._require_builder()
	prompt = (prompt or "").strip()
	if not prompt:
		frappe.throw(_("Type a request first"))
	key, model, _source = ai._resolve_key()
	if not key:
		frappe.throw(_("Add a Gemini API key in AI settings first"), title=_("No API key"))

	state = _read_board(board)
	before = copy.deepcopy(state)
	history = [h for h in (frappe.parse_json(history or "[]") or []) if isinstance(h, dict)][-HISTORY_TURNS:]
	answered = frappe.parse_json(answered) if isinstance(answered, str) else bool(answered)

	digest = [_describe(w, state["layout"][w["widget_id"]]) for w in state["widgets"]]
	focus = ""
	chosen = next((w for w in state["widgets"] if w["widget_id"] == str(selected or "")), None)
	if chosen:
		focus = (
			f'\nThe person has selected the widget "{chosen["title"]}" (id {chosen["widget_id"]}). '
			"Words like this, it, هذا, هذي and هذه refer to it. Change only it unless they clearly mean "
			"the whole board.\n"
		)
	answered_block = ""
	if answered:
		answered_block = (
			"\nThe person has just answered your question. Act on it now and do not ask again.\n"
		)

	plan_prompt = (
		"You are the copilot inside Lumen Reports, a dashboard studio for Frappe and ERPNext. "
		"The person is editing the dashboard below. Turn their message into a short reply and a "
		"list of operations that the studio will apply once they confirm.\n"
		f"Today's date is {frappe.utils.nowdate()}.\n\n"
		f'Dashboard "{state["title"] or "Untitled"}". Theme: {json.dumps(state["theme"])}\n'
		"Grid: 12 columns. x is the column (0-11), y the row, w the width in columns, h the height "
		"in rows of 64px.\n"
		"Widgets:\n" + json.dumps(digest, ensure_ascii=False, default=str) + "\n" + focus + answered_block + "\n"
		+ _history_block(history)
		+ f"Message: {prompt}\n\n"
		+ _guide()
	)
	plan = ai._generate(plan_prompt, key, model)
	if not isinstance(plan, dict):
		frappe.throw(_("The AI returned an unreadable response. Try rephrasing."))

	if plan.get("clarify") and not answered:
		return {
			"clarify": _plain(plan["clarify"], 240),
			"options": [_plain(o, 80) for o in (plan.get("options") or []) if isinstance(o, str)][:4],
		}

	turn = _Turn(state, prompt, key, model)
	for op in (plan.get("operations") or [])[:MAX_OPS]:
		if not isinstance(op, dict):
			continue
		handler = OPERATIONS.get(op.get("op"))
		if handler:
			handler(turn, op)

	if turn.layout_touched:
		state["layout"] = _compact(state["layout"])

	changed = json.dumps(before, sort_keys=True, default=str) != json.dumps(state, sort_keys=True, default=str)
	return {
		"reply": _plain(plan.get("reply") or "", 400),
		"changes": turn.changes,
		"notes": turn.notes,
		"analysis": turn.analysis,
		"suggestions": [_plain(s, 90) for s in (plan.get("suggestions") or []) if isinstance(s, str)][:3],
		"proposal": (
			{
				"title": state["title"],
				"theme": state["theme"],
				"widgets": state["widgets"],
				"layout": [{"widget_id": wid, **pos} for wid, pos in state["layout"].items()],
			}
			if changed
			else None
		),
	}
