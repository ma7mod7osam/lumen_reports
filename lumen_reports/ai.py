# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

"""Ask AI: natural-language question -> Lumen widget spec -> validated result.

The model NEVER touches the database. It only ever produces the same JSON
query definition the no-code wizard produces; that spec is executed through
the permission-aware query engine, so the asking user can only ever see data
their role already allows. Bring-your-own-key: each user stores their own
Gemini API key (encrypted); calls are made server-side with that key.
"""

import json

import frappe
import requests
from frappe import _

from lumen_reports import query_engine
from lumen_reports.api import get_doctype_fields

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
# floating alias maintained by Google — always points at the current flash model,
# so it keeps working as they retire dated model names
DEFAULT_MODEL = "gemini-flash-latest"
REQUEST_TIMEOUT = 90
MAX_DOCTYPES_TO_INSPECT = 3

# model-name tokens that aren't text/analytics models
EXCLUDED_MODEL_TOKENS = (
	"image",
	"tts",
	"audio",
	"robotics",
	"computer-use",
	"omni",
	"clip",
	"banana",
	"live",
)

WIDGET_TYPES = [
	"Number Card",
	"Bar Chart",
	"Stacked Bar",
	"Horizontal Bar",
	"Line Chart",
	"Area Chart",
	"Sparkline",
	"Waterfall",
	"Progress Bars",
	"Donut Chart",
	"Pie Chart",
	"Rings",
	"Radar",
	"Funnel",
	"Gauge",
	"Scatter",
	"Heatmap",
	"Tree Report",
	"Table",
]

# chart types that need a plain one-value-per-category series
SERIES_TYPES = (
	"Horizontal Bar",
	"Sparkline",
	"Waterfall",
	"Progress Bars",
	"Donut Chart",
	"Pie Chart",
	"Rings",
	"Funnel",
)
# cartesian charts: one series normally, grouped/stacked when group_by2 is set
MULTI_TYPES = ("Bar Chart", "Stacked Bar", "Line Chart", "Area Chart")

SPEC_GUIDE = """You output a JSON object describing one or more Lumen widgets:
{
  "title": "short title for the whole answer (used as dashboard name)",
  "explanation": "one or two sentences describing what is shown",
  "widgets": [ <widget>, ... ]
}

How many widgets:
- A single focused question ("revenue by brand") -> exactly 1 widget.
- A dashboard-style or compound request ("dashboard", "detailed", or several dimensions listed)
  -> 4 to 8 complementary widgets: start with 2-4 Number Card KPIs (e.g. total revenue,
  invoice count, average order value), then one chart per requested dimension, and finish
  with one Table of top records. Never two widgets for the same dimension.

Each <widget> is:
{
  "title": "short human title",
  "widget_type": one of %(widget_types)s,
  "query": {
    "doctype": "<base doctype>",            // a line-item child table IF parent_doctype is set
    "parent_doctype": "<parent>",            // ONLY for line-item (child table) bases
    "aggregate": {"function": "count|sum|avg|min|max", "field": "<numeric field>"},  // omit field for count; omit aggregate for Table
    "group_by": {"field": "<field>", "via": {"link_field": "<link>", "doctype": "<target>"}, "time_grain": "hour|weekday|day|week|month|year"},
        // omit for Number Card/Gauge; via only for related fields; time_grain only for Date/Datetime fields
    "group_by2": {...same shape...},   // second dimension: stacks/lines, heatmap columns,
                                       // radar webs, or tree level 2
    "group_by3": {...same shape...},   // Tree Report level 3 ONLY
    "shape": "tree",                   // Tree Report ONLY — makes the group_bys nesting levels
    "aggregate_y": {"function": "...", "field": "..."},     // Scatter ONLY: the vertical measure
    "aggregate_size": {"function": "...", "field": "..."},  // Scatter ONLY, optional: bubble size
    "fields": ["field", {"field": "f", "via": {...}}],  // Table only, max 8 columns
    "filters": [["<field>", "=|!=|>|<|>=|<=|like|in|between", value]],  // field may also be {"field","via"}
    "sort": {"field": "<field>", "order": "asc|desc"},  // Table only
    "limit": 20                                          // Table only
  }
}
Rules:
- Use ONLY doctypes and fields from the metadata given to you. Never invent fields.
- Charts need group_by; Number Card must not have group_by; Table uses fields not aggregate.
- For "by <master attribute>" questions (e.g. revenue by brand), use the line-item child table as
  the base with parent_doctype set, and group_by the related field with its via spec.
- Filter out cancelled documents with ["docstatus","=",1] for submittable doctypes (invoices, orders).
- IMPORTANT: when a dimension exists BOTH as a column on the line item AND in related_fields via the
  item master (e.g. brand, item_group), ALWAYS use the related_fields version with its via spec —
  the line's own copy is a snapshot that is often empty on historical rows.
  Example — "revenue by brand":
  {"doctype": "Sales Invoice Item", "parent_doctype": "Sales Invoice",
   "aggregate": {"function": "sum", "field": "amount"},
   "group_by": {"field": "brand", "via": {"link_field": "item_code", "doctype": "Item"}},
   "filters": [["docstatus", "=", 1]]}
- Computed metrics — for values that exist in no field (average check-in time, office
  hours, margins), use "aggregate": {"function": "avg", "expr": <node>, "format": "..."}
  instead of "field". <node> is a field name, a number, or {"op": ..., "args": [<node>, <node>]}:
  * clock(x) — time of day as hours since midnight. Average check-in time:
    {"function": "avg", "expr": {"op": "clock", "args": ["in_time"]}, "format": "clock"}
  * diff_hours(a,b) / diff_minutes(a,b) / diff_days(a,b) — b minus a. Average office hours:
    {"function": "avg", "expr": {"op": "diff_hours", "args": ["in_time", "out_time"]}, "format": "hours"}
  * add/sub/mul/div(a,b) — arithmetic. Unpaid ratio:
    {"function": "avg", "expr": {"op": "div", "args": ["outstanding_amount", "grand_total"]}, "format": "percent"}
  ONLY these ops exist; every field in expr must exist on the base doctype.
  "format" one of clock|hours|minutes|days|percent controls display.
- Form follows the data — these are HARD rules, not taste:
  * time series (day/week/month/year grain) -> Line or Area; hour/weekday distributions -> Bar.
    NEVER Pie/Donut/Funnel for anything time-based.
  * categorical breakdown -> Bar; ranked top-N (especially long names like customers) ->
    Horizontal Bar; Donut/Pie ONLY for share-of-total with <=6 categories.
  * Funnel -> staged processes only (order pipeline, status progression), <=7 stages.
  * Gauge -> ONE metric measured against a target: aggregate without group_by plus
    "style": {"target": <number>} on the widget (e.g. monthly sales target).
  * Heatmap -> exactly two dimensions via group_by (rows) + group_by2 (columns).
    THE form for busy-times questions: {"group_by": {"field": "creation", "time_grain": "weekday"},
    "group_by2": {"field": "creation", "time_grain": "hour"}}.
  * Sparkline -> a compact trend beside a headline figure: a TIME series (day/week/month grain)
    when the point is "where is this heading", not the individual periods. Never categorical.
  * Waterfall -> how a total is built up or drawn down step by step (cash in/out, monthly
    contributions to a year total, budget variance). Values may be negative. <=8 steps.
    A closing "Total" bar is added automatically — do not add one yourself.
  * Rings -> 2-5 headline metrics as progress dials. With "style": {"target": <number>} each
    ring is progress toward that target; without one, each ring is its share of the total.
  * Radar -> comparing 3-10 metrics/spokes, optionally for up to 4 entities at once.
    One web: group_by = the spokes. Several webs: group_by = spokes, group_by2 = the entity
    (e.g. scorecard per warehouse: group_by item_group, group_by2 warehouse).
  * Scatter -> a RELATIONSHIP between two measures, one point per category:
    group_by = what a point is, "aggregate" = x, "aggregate_y" = y, optional "aggregate_size".
    Example — price vs volume per item:
    {"doctype": "Sales Invoice Item", "parent_doctype": "Sales Invoice",
     "group_by": {"field": "item_code"},
     "aggregate": {"function": "avg", "field": "rate"},
     "aggregate_y": {"function": "sum", "field": "qty"},
     "aggregate_size": {"function": "count"}, "filters": [["docstatus", "=", 1]]}
  * TWO dimensions at once ("sales by month BY channel", "revenue per region per
    category") -> add group_by2 and pick the form from what is being asked:
      - "compare", "side by side", "versus each other" -> Bar Chart (grouped bars)
      - "mix", "composition", "share of total", "makes up" -> Stacked Bar
      - a trend per entity, or actual-vs-target/this-year-vs-last -> Line Chart
    Keep it to <=6 series; more becomes a Heatmap.
  * Progress Bars -> 2-8 named metrics each as a labelled bar, with
    "style": {"target": <number>} for progress toward a shared target (warehouse
    capacity, per-branch attainment). Without a target each bar is relative to
    the largest. Prefer this over Rings when the labels are long.
  * Tree Report -> a drill-down breakdown where the user names a HIERARCHY
    ("category then brand then item", "region > salesperson"): set
    "shape": "tree" plus group_by / group_by2 / group_by3 as the levels.
    Totals roll up and every row shows its share of the grand total.
    Example: {"doctype": "Sales Invoice Item", "parent_doctype": "Sales Invoice",
     "shape": "tree", "aggregate": {"function": "sum", "field": "amount"},
     "group_by": {"field": "item_group", "via": {"link_field": "item_code", "doctype": "Item"}},
     "group_by2": {"field": "brand", "via": {"link_field": "item_code", "doctype": "Item"}},
     "group_by3": {"field": "item_code"}, "filters": [["docstatus", "=", 1]]}
  * single figure -> Number Card; record lists -> Table.
- Dates: time_grain month unless the question implies daily/weekly/yearly.
- Time-of-day questions (peak hours, busiest time): group by a Datetime field such as
  "creation" with time_grain "hour" — a Bar Chart of hour-of-day across all days.
- Date filter values MUST be concrete ISO dates ("2026-01-01"), never phrases like "this year".
  For "this year" use ["<date field>", "between", ["<jan 1>", "<dec 31>"]] with real dates.

Field matching — understanding beats guessing:
- Users speak business language ("sales man", "branch", "cashier", "category"). Match it by
  MEANING against both fieldname and label, including fields marked "custom": true (the
  user added those themselves — they often hold exactly what the user means) and child
  tables (e.g. salesperson data usually lives in the Sales Team child table's sales_person).
- NEVER silently substitute an unrelated field. If nothing matches confidently, respond with
  {"clarify": "<short question>", "options": ["<closest field label 1>", "<closest 2>", ...]}
  naming the nearest fields you actually found — asking beats a wrong chart.
- In "explanation", say explicitly how you mapped ambiguous words
  (e.g. 'using Sales Team → Sales Person for "sales man"').

Be insightful, not literal:
- Include widgets the user didn't explicitly request when they obviously help answer the
  underlying business question — a trend over time, top/bottom performers, a share breakdown,
  a KPI row for context. A good analyst anticipates.
- Vary chart types by what tells the story best; never several widgets of the same shape
  when one would do.

Ask before you assume:
- ASK FIRST — return {"clarify": "<one short question>", "options": ["<3-4 answers>"]}
  and NO widgets — whenever any of these is true:
  * a word in the request maps to two or more plausible fields (offer the candidates)
  * the request is broad ("how are we doing", "show me performance", "build a dashboard")
    and the metadata covers several subject areas it could mean (offer the areas)
  * it implies a comparison without saying against what ("vs target", "are we better")
  * it names a period you cannot turn into dates ("recently", "peak season", "lately")
  Rules for options: use real fields/values from the metadata, put the most likely first,
  and make the LAST option an escape so the user is never stuck — "Just show me
  everything", "Use all time", "Cover all of it".
- Ask ONE question, never a list. If the conversation history shows you already asked a
  clarifying question, do NOT ask again — take the user's answer and build.
- When you DO build, list every judgement you made as a "questions" entry, phrased as a
  tappable refinement the user can send straight back: "Limit this to 2026 only?",
  "Should returns be excluded?", "Break it down by branch as well?". These become buttons —
  write them so that clicking one is a complete instruction on its own.
- Never ask about something you can see in the metadata, and never ask more than 3.

Also include in the top-level JSON:
- "suggestions": 2-4 short follow-up ideas the user could pick to extend this dashboard
  (plain sentences like "Add a monthly trend of returns"; each must be answerable from the
  metadata you were given).
- "questions": 1-3 refinements, per the "Ask before you assume" rules above. Include at
  least one whenever you assumed a date range, a status filter, or a field mapping.
Respond with ONLY the JSON object.""" % {"widget_types": json.dumps(WIDGET_TYPES)}


# ---------------------------------------------------------------- settings


def _get_settings_doc(create=False):
	user = frappe.session.user
	name = frappe.db.get_value("Lumen AI Settings", {"user": user})
	if name:
		return frappe.get_doc("Lumen AI Settings", name)
	if not create:
		return None
	doc = frappe.new_doc("Lumen AI Settings")
	doc.user = user
	return doc


def _require_user():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login"), frappe.PermissionError)


def _personal_key():
	doc = _get_settings_doc()
	if not doc:
		return None, None
	try:
		key = doc.get_password("gemini_api_key", raise_exception=False)
	except Exception:
		key = None
	return key, (doc.model or None)


def _site_key():
	site = frappe.get_cached_doc("Lumen AI Site Settings")
	try:
		key = site.get_password("gemini_api_key", raise_exception=False)
	except Exception:
		key = None
	return key, (site.model or None)


def _resolve_key():
	"""Personal key wins; the site-wide key is the shared fallback."""
	key, model = _personal_key()
	if key:
		return key, model or DEFAULT_MODEL, "user"
	key, model = _site_key()
	if key:
		return key, model or DEFAULT_MODEL, "site"
	return None, DEFAULT_MODEL, None


def _is_admin():
	return "System Manager" in frappe.get_roles()


@frappe.whitelist()
def get_ai_status():
	"""Key availability for the current user. Never returns any key."""
	_require_user()
	personal, personal_model = _personal_key()
	site, site_model = _site_key()
	_key, model, source = _resolve_key()
	return {
		"configured": source is not None,
		"source": source,  # "user" | "site" | None
		"model": model,
		"personal_configured": bool(personal),
		"personal_model": personal_model or DEFAULT_MODEL,
		"site_configured": bool(site),
		"site_model": site_model or DEFAULT_MODEL,
		"is_admin": _is_admin(),
	}


@frappe.whitelist()
def save_ai_settings(api_key: str | None = None, model: str | None = None):
	"""Save the current user's Gemini key (encrypted) and/or model choice."""
	_require_user()
	doc = _get_settings_doc(create=True)
	if model:
		doc.model = model
	if api_key:
		doc.gemini_api_key = api_key
	doc.flags.ignore_permissions = True  # scoped to session user above
	doc.save()
	frappe.db.commit()
	return get_ai_status()


@frappe.whitelist()
def clear_ai_key():
	_require_user()
	doc = _get_settings_doc()
	if doc:
		doc.gemini_api_key = ""
		doc.flags.ignore_permissions = True
		doc.save()
		frappe.db.commit()
	return get_ai_status()


@frappe.whitelist()
def save_site_ai_settings(api_key: str | None = None, model: str | None = None):
	"""Save the shared site-wide key. System Managers only."""
	frappe.only_for("System Manager")
	site = frappe.get_doc("Lumen AI Site Settings")
	if model:
		site.model = model
	if api_key:
		site.gemini_api_key = api_key
	site.save()
	frappe.db.commit()
	return get_ai_status()


@frappe.whitelist()
def clear_site_ai_key():
	frappe.only_for("System Manager")
	site = frappe.get_doc("Lumen AI Site Settings")
	site.gemini_api_key = ""
	site.save()
	frappe.db.commit()
	return get_ai_status()


@frappe.whitelist()
def list_models():
	"""Text-capable Gemini models available to the resolved key, so the model
	dropdown always reflects what the key can actually use."""
	_require_user()
	key, _model, _source = _resolve_key()
	if not key:
		return []
	try:
		response = requests.get(
			GEMINI_MODELS_URL,
			headers={"x-goog-api-key": key},
			params={"pageSize": 200},
			timeout=20,
		)
		response.raise_for_status()
		rows = response.json().get("models", [])
	except Exception:
		return []

	names = []
	for m in rows:
		if "generateContent" not in (m.get("supportedGenerationMethods") or []):
			continue
		name = m.get("name", "").replace("models/", "")
		if not name.startswith("gemini-"):
			continue
		if any(token in name for token in EXCLUDED_MODEL_TOKENS):
			continue
		names.append(name)
	# floating aliases first — they don't rot when Google retires dated names
	names.sort(key=lambda n: (0 if "latest" in n else 1, n))
	return names


# ---------------------------------------------------------------- gemini


def _scrub(text: str, key: str) -> str:
	"""Never let the API key appear in any user-visible error."""
	return str(text).replace(key, "***") if key else str(text)


def _generate(prompt: str, key: str, model: str) -> dict:
	"""One Gemini call, JSON-mode. Returns the parsed JSON object.

	The key travels in the x-goog-api-key header — never in the URL — so it
	can't leak through exception messages, logs, or proxies."""
	body = {
		"contents": [{"role": "user", "parts": [{"text": prompt}]}],
		"generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
	}
	try:
		response = requests.post(
			GEMINI_URL.format(model=model),
			headers={"x-goog-api-key": key},
			json=body,
			timeout=REQUEST_TIMEOUT,
		)
	except requests.RequestException as e:
		frappe.throw(_("Could not reach the Gemini API: {0}").format(_scrub(e, key)))

	if response.status_code != 200:
		detail = ""
		try:
			detail = _scrub(response.json().get("error", {}).get("message", "")[:200], key)
		except Exception:
			pass
		if response.status_code in (400, 401, 403) and "key" in detail.lower():
			frappe.throw(_("Your Gemini API key was rejected. Check it in AI settings. ({0})").format(detail))
		if response.status_code == 429:
			frappe.throw(
				_("Gemini rate limit reached. Wait a minute and try again, or switch model in AI settings. ({0})").format(
					detail or "quota exceeded"
				)
			)
		frappe.throw(_("Gemini API error {0}: {1}").format(response.status_code, detail))

	try:
		text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
		return json.loads(text)
	except Exception:
		frappe.throw(_("The AI returned an unreadable response. Try rephrasing your question."))


# ---------------------------------------------------------------- metadata


def _readable_doctypes() -> list:
	readable = set(frappe.get_user().get_can_read())
	rows = frappe.get_all(
		"DocType",
		filters={"istable": 0, "issingle": 0},
		pluck="name",
		order_by="name",
		limit_page_length=0,
	)
	return [r for r in rows if r in readable]


# dimension/measure fieldtypes carry the business meaning — they go first
PROMPT_PRIORITY_FIELDTYPES = {
	"Link",
	"Select",
	"Currency",
	"Float",
	"Int",
	"Percent",
	"Date",
	"Datetime",
	"Check",
	"Data",
}


def _slim_one(r: dict) -> dict:
	d = {"fieldname": r.get("fieldname"), "label": r.get("label"), "fieldtype": r.get("fieldtype")}
	if r.get("custom"):
		d["custom"] = True  # user-added field — business words often live here
	return d


def _slim_fields(payload: dict) -> dict:
	"""Compact field metadata for the prompt. Custom fields and dimension/
	measure types are ranked FIRST so they survive the cap — big doctypes have
	200+ fields and the user's own custom fields must never be cut off."""
	fields = payload.get("fields", [])
	ranked = sorted(
		fields,
		key=lambda f: (
			0 if f.get("custom") else 1,
			0 if f.get("fieldtype") in PROMPT_PRIORITY_FIELDTYPES else 1,
		),
	)
	return {
		"fields": [_slim_one(r) for r in ranked[:90]],
		"numeric": [f["fieldname"] for f in payload.get("numeric", [])],
		"date": [f["fieldname"] for f in payload.get("date", [])],
		"related_fields": [
			{"field": r["field"], "label": r["label"], "fieldtype": r["fieldtype"], "via": r["via"]}
			for r in payload.get("related_fields", [])
		][:40],
		"line_item_tables": payload.get("line_item_tables", []),
	}


def _mini_table_meta(child_doctype: str, parent_doctype: str) -> dict | None:
	"""Ultra-compact metadata for secondary child tables (Sales Team, Payments,
	Taxes...) so the model can find e.g. sales_person without a full payload."""
	try:
		meta = frappe.get_meta(child_doctype)
	except Exception:
		return None
	fields = [
		_slim_one(
			{
				"fieldname": df.fieldname,
				"label": df.label,
				"fieldtype": df.fieldtype,
				"custom": df.get("is_custom_field"),
			}
		)
		for df in meta.fields
		if df.fieldtype in PROMPT_PRIORITY_FIELDTYPES and not df.hidden
	][:15]
	if not fields:
		return None
	return {
		"parent_doctype": parent_doctype,
		"note": "child table — use as base doctype with parent_doctype set",
		"fields": fields,
	}


def _metadata_for(doctypes: list) -> dict:
	out = {}
	for doctype in doctypes[:MAX_DOCTYPES_TO_INSPECT]:
		try:
			meta_payload = get_doctype_fields(doctype)
		except Exception:
			continue
		out[doctype] = _slim_fields(meta_payload)
		tables = meta_payload.get("line_item_tables", [])
		# first (main) line table gets full metadata for line-grain queries...
		for table in tables[:1]:
			try:
				child_payload = get_doctype_fields(table["child_doctype"], parent_doctype=doctype)
				out[table["child_doctype"]] = _slim_fields(child_payload)
				out[table["child_doctype"]]["parent_doctype"] = doctype
			except Exception:
				pass
		# ...the rest (Sales Team, Payments, ...) get compact metadata so the
		# model can still find fields like sales_person instead of guessing
		for table in tables[1:]:
			if table["child_doctype"] in out:
				continue
			mini = _mini_table_meta(table["child_doctype"], doctype)
			if mini:
				out[table["child_doctype"]] = mini
	return out


# ---------------------------------------------------------------- ask


@frappe.whitelist()
def ask_ai(prompt: str, history=None, existing_titles=None, answered=False):
	"""Natural-language question -> widget spec + executed result.

	`history` is the running conversation ([{role, text}, ...], kept client
	side) so follow-ups and answers to clarifying questions have context.
	`existing_titles` are widgets already on the user's board, so a follow-up
	adds new perspectives instead of recreating what exists.
	`answered` marks this call as the reply to a clarifying question — the model
	must build now, because a second question in a row is a dead end."""
	_require_user()
	prompt = (prompt or "").strip()
	if not prompt:
		frappe.throw(_("Ask a question first"))
	history = [h for h in (frappe.parse_json(history or "[]") or []) if isinstance(h, dict)][-10:]
	existing_titles = [t for t in (frappe.parse_json(existing_titles or "[]") or []) if t][:20]
	answered = frappe.parse_json(answered) if isinstance(answered, str) else bool(answered)

	key, model, source = _resolve_key()
	if not key:
		frappe.throw(_("Add a Gemini API key in AI settings first"), title=_("No API key"))

	history_block = ""
	if history:
		lines = "\n".join(f"{h.get('role', 'user')}: {str(h.get('text', ''))[:300]}" for h in history)
		history_block = (
			"Conversation so far (use it to resolve references like 'that', 'same period', "
			"and answers to your earlier questions):\n" + lines + "\n\n"
		)
	# never ask twice in a row: the user just answered a question
	if answered:
		history_block += (
			"IMPORTANT: the user has ALREADY answered your clarifying question — their "
			"answer is in the message below. Build the widgets now. Do NOT return "
			'"clarify" again under any circumstance; if something is still unclear, pick '
			"the most reasonable reading and note it in \"questions\" instead.\n\n"
		)

	# step 1: pick relevant doctypes
	pick = _generate(
		"You help build analytics widgets on a Frappe/ERPNext site.\n"
		+ history_block
		+ f"Latest user message: {prompt}\n\n"
		"Available doctypes (pick the 1-3 most relevant for answering the question; "
		"prefer transaction doctypes like Sales Invoice for revenue/sales questions):\n"
		+ json.dumps(_readable_doctypes())
		+ '\n\nRespond ONLY with JSON: {"doctypes": ["..."]} — or, if the request is too '
		'ambiguous to attempt, {"clarify": "<one short question>", "options": ["<likely '
		'answer>", ...]} with 2-4 tappable answer options when they are predictable.',
		key,
		model,
	)
	if pick.get("clarify") and not answered:
		return {
			"clarify": pick["clarify"],
			"options": [o for o in (pick.get("options") or []) if isinstance(o, str)][:4],
		}
	chosen = [d for d in (pick.get("doctypes") or []) if isinstance(d, str)]
	if not chosen:
		frappe.throw(_("The AI could not identify relevant data for that question."))

	metadata = _metadata_for(chosen)
	if not metadata:
		frappe.throw(_("You don't have access to the data needed for that question."))

	existing_block = ""
	if existing_titles:
		existing_block = (
			"\n\nWidgets ALREADY on the user's board (do NOT recreate these — return only "
			"new, different widgets that extend the board):\n" + json.dumps(existing_titles)
		)

	# step 2: build the widget spec
	build_prompt = (
		"You help build analytics widgets on a Frappe/ERPNext site.\n"
		f"Today's date is {frappe.utils.nowdate()}.\n"
		+ history_block
		+ f"Latest user message: {prompt}\n\n"
		f"{SPEC_GUIDE}\n\n"
		"Metadata for the relevant doctypes (doctype -> fields; entries with "
		"parent_doctype are line-item child tables of that parent):\n"
		+ json.dumps(metadata, default=str)
		+ existing_block
	)
	spec = _generate(build_prompt, key, model)
	# the model may realize only after seeing the metadata that it must ask
	if isinstance(spec, dict) and spec.get("clarify"):
		if not answered:
			return {
				"clarify": spec["clarify"],
				"options": [o for o in (spec.get("options") or []) if isinstance(o, str)][:4],
			}
		# it asked again anyway — force a build rather than leave the user stuck
		spec = _generate(
			build_prompt
			+ "\n\nYou returned another question. That is not allowed here: the user has "
			"already answered one. Choose the most reasonable interpretation and return "
			'the widgets JSON now, noting the interpretation in "questions".',
			key,
			model,
		)
	widgets, errors = _validate_widgets(spec)

	if errors:
		# one batch self-repair round: feed every engine complaint back at once
		repair = _generate(
			build_prompt
			+ "\n\nYour previous answer was:\n"
			+ json.dumps(spec, default=str)
			+ "\n\nThese widgets failed validation:\n"
			+ "\n".join(f"- widget[{i}] {title!r}: {err}" for i, title, err in errors)
			+ "\n\nReturn the corrected FULL JSON answer (all widgets, fixed).",
			key,
			model,
		)
		repaired_widgets, repair_errors = _validate_widgets(repair)
		if repaired_widgets:
			spec = repair
			widgets, errors = repaired_widgets, repair_errors

	if not widgets:
		detail = "; ".join(err for _i, _t, err in errors[:3]) or "no valid widgets"
		frappe.throw(_("Couldn't build a working report for that question: {0}").format(detail))

	# never silently discard the user's intent: widgets whose data came back
	# empty (no returns yet, no invoices today...) are flagged, not dropped —
	# the UI lets the user include them for when data arrives
	for w in widgets:
		w["empty"] = _is_empty(w["result"])

	return {
		"title": spec.get("title") or prompt[:60],
		"explanation": spec.get("explanation") or "",
		"widgets": widgets,
		"suggestions": [s for s in (spec.get("suggestions") or []) if isinstance(s, str)][:4],
		"questions": [q for q in (spec.get("questions") or []) if isinstance(q, str)][:3],
	}


@frappe.whitelist()
def modify_ai_widget(prompt: str, widget):
	"""Revise one existing widget from a natural-language instruction.
	Same safety path as ask_ai: the model only emits a spec, which is
	validated and executed through the permission-aware engine."""
	_require_user()
	prompt = (prompt or "").strip()
	if not prompt:
		frappe.throw(_("Describe the change first"))
	widget = frappe.parse_json(widget)
	key, model, _source = _resolve_key()
	if not key:
		frappe.throw(_("Add a Gemini API key in AI settings first"), title=_("No API key"))

	query = widget.get("query") or {}
	base_doctype = query.get("parent_doctype") or query.get("doctype")
	metadata = _metadata_for([base_doctype]) if base_doctype else {}

	current = {
		"title": widget.get("title"),
		"widget_type": widget.get("widget_type"),
		"query": query,
	}
	build_prompt = (
		"You modify ONE analytics widget on a Frappe/ERPNext site.\n"
		f"Today's date is {frappe.utils.nowdate()}.\n\n"
		f"{SPEC_GUIDE}\n\n"
		"Metadata for the relevant doctypes:\n"
		+ json.dumps(metadata, default=str)
		+ "\n\nCurrent widget:\n"
		+ json.dumps(current, default=str)
		+ f"\n\nUser instruction: {prompt}\n\n"
		"Apply ONLY the requested change, keeping everything else (filters, base, title unless asked). "
		'Return JSON: {"explanation": "...", "widgets": [<exactly one modified widget>]}.'
	)

	spec = _generate(build_prompt, key, model)
	widgets, errors = _validate_widgets(spec)
	if not widgets and errors:
		repair = _generate(
			build_prompt
			+ "\n\nYour previous answer was:\n"
			+ json.dumps(spec, default=str)
			+ "\n\nIt failed validation:\n"
			+ "\n".join(err for _i, _t, err in errors)
			+ "\n\nReturn the corrected JSON answer.",
			key,
			model,
		)
		widgets, errors = _validate_widgets(repair)
		spec = repair
	if not widgets:
		detail = "; ".join(err for _i, _t, err in errors[:3]) or "no valid widget"
		frappe.throw(_("Couldn't apply that change: {0}").format(detail))

	entry = widgets[0]
	# keep the original styling (tint etc.) — the AI only reshapes the data spec
	entry["widget"]["style"] = widget.get("style") or {}
	entry["explanation"] = spec.get("explanation") or ""
	return entry


MAX_WIDGETS = 8


def _validate_widgets(spec):
	"""Validate every widget in an answer through the permission-aware engine.
	Returns (valid widgets with results, [(index, title, error), ...])."""
	if not isinstance(spec, dict):
		return [], [(0, "", "answer is not a JSON object")]
	raw = spec.get("widgets")
	if not isinstance(raw, list):
		# tolerate a bare single-widget object
		raw = [spec] if spec.get("widget_type") else []
	valid, errors = [], []
	for i, w in enumerate(raw[:MAX_WIDGETS]):
		result, error = _try_widget(w)
		title = (w or {}).get("title") or f"widget {i}"
		if error:
			errors.append((i, title, error))
		else:
			style = w.get("style") if isinstance(w.get("style"), dict) else {}
			valid.append(
				{
					"widget": {
						"title": title,
						"widget_type": w.get("widget_type"),
						"query": w.get("query"),
						# keep only known style keys (gauge target, tint, accent)
						"style": {k: style[k] for k in ("tint", "accent", "target", "subtitle") if k in style},
					},
					"result": result,
				}
			)
	return valid, errors


def _try_widget(w):
	"""Validate one widget by executing it through the engine."""
	if not isinstance(w, dict):
		return None, "widget is not an object"
	widget_type = w.get("widget_type")
	query = w.get("query")
	if widget_type not in WIDGET_TYPES:
		return None, f"invalid widget_type {widget_type!r}"
	if not isinstance(query, dict):
		return None, "missing query object"
	try:
		result = query_engine.execute(query)
	except Exception as e:
		frappe.clear_last_message()
		return None, str(e)[:300]

	# shape sanity: each widget type demands a matching result shape
	kind = result.get("result_type")
	if widget_type in ("Number Card", "Gauge") and kind != "number":
		return None, f"{widget_type} query must aggregate without group_by"
	if widget_type == "Table" and kind != "rows":
		return None, "Table query must use fields, not aggregate"
	if widget_type == "Heatmap" and kind != "matrix":
		return None, "Heatmap needs BOTH group_by (rows) and group_by2 (columns)"
	if widget_type == "Scatter" and kind != "points":
		return None, "Scatter needs aggregate (x) AND aggregate_y (y) plus a group_by"
	if widget_type == "Radar" and kind not in ("series", "matrix"):
		return None, "Radar needs aggregate + group_by (the spokes)"
	if widget_type == "Tree Report" and kind != "tree":
		return None, 'Tree Report needs "shape": "tree" plus 2-3 group_by levels'
	if widget_type == "Stacked Bar" and kind != "matrix":
		return None, "Stacked Bar needs group_by (x axis) AND group_by2 (the stacks)"
	if kind == "tree" and widget_type != "Tree Report":
		return None, 'a "shape": "tree" query can only be a Tree Report'
	if kind == "matrix" and widget_type not in ("Heatmap", "Radar") + MULTI_TYPES:
		return None, "two-dimensional results must be a Heatmap, Radar, or a grouped/stacked chart"
	if kind == "points" and widget_type != "Scatter":
		return None, "a query with aggregate_y can only be shown as a Scatter"
	if widget_type in SERIES_TYPES and kind != "series":
		return None, "chart query needs aggregate + group_by"
	if widget_type in MULTI_TYPES and kind not in ("series", "matrix"):
		return None, "chart query needs aggregate + group_by"

	if kind == "matrix" and widget_type in MULTI_TYPES and len(result.get("cols") or []) > 8:
		# too many stacks/lines to tell apart — a heatmap scales, a legend doesn't
		w["widget_type"] = "Heatmap"

	# form follows the data — coerce chart types that don't suit the series
	if kind == "series":
		grain = (query.get("group_by") or {}).get("time_grain")
		count = len(result.get("labels") or [])
		shares = ("Pie Chart", "Donut Chart", "Funnel", "Horizontal Bar", "Rings", "Radar")
		if widget_type in shares:
			if grain in ("hour", "weekday"):
				w["widget_type"] = "Bar Chart"  # a distribution, not shares/rank
			elif grain:
				w["widget_type"] = "Line Chart"  # a time sequence is a trend
			elif widget_type in ("Pie Chart", "Donut Chart") and count > 8:
				w["widget_type"] = "Horizontal Bar"  # too many slices — ranked bars read best
			elif widget_type == "Rings" and count > 5:
				w["widget_type"] = "Horizontal Bar"  # rings run out of radius
			elif widget_type == "Radar" and count > 10:
				w["widget_type"] = "Horizontal Bar"  # too many spokes to read
		# a sparkline traces a sequence; a waterfall accumulates along one
		elif widget_type in ("Sparkline", "Waterfall") and not grain and count > 8:
			w["widget_type"] = "Horizontal Bar"
		elif widget_type == "Sparkline" and grain in ("hour", "weekday"):
			w["widget_type"] = "Bar Chart"  # a distribution has no running trend
	return result, None


def _is_empty(result):
	"""A widget that came back with nothing to show (empty or all-null series)."""
	kind = result.get("result_type")
	if kind == "series":
		labels = result.get("labels") or []
		return not labels or all(label in (None, "") for label in labels)
	if kind == "rows":
		return not (result.get("rows") or [])
	if kind == "matrix":
		return not (result.get("rows") or []) or not (result.get("cols") or [])
	if kind == "points":
		return not (result.get("points") or [])
	if kind == "tree":
		return not (result.get("nodes") or [])
	return False  # a number (even 0) is signal


# ---------------------------------------------------------------- persist


DEFAULT_SIZES = {
	"Number Card": {"w": 3, "h": 2},
	"Sparkline": {"w": 3, "h": 3},
	"Gauge": {"w": 3, "h": 3},
	"Rings": {"w": 4, "h": 4},
	"Radar": {"w": 4, "h": 5},
	"Progress Bars": {"w": 4, "h": 4},
	"Heatmap": {"w": 12, "h": 5},
	"Tree Report": {"w": 12, "h": 7},
	"Table": {"w": 12, "h": 5},
	"default": {"w": 6, "h": 5},
}

KPI_TINTS = ["blue", "green", "amber", "violet"]


def _auto_layout(widgets, start_y=0):
	"""Pack widgets left-to-right, top-to-bottom on the 12-column grid."""
	layout = []
	x, y, row_h = 0, start_y, 0
	for w in widgets:
		size = DEFAULT_SIZES.get(w["widget_type"]) or DEFAULT_SIZES["default"]
		if x + size["w"] > 12:
			x, y, row_h = 0, y + row_h, 0
		layout.append({"widget_id": w["widget_id"], "x": x, "y": y, **size})
		x += size["w"]
		row_h = max(row_h, size["h"])
		if x >= 12:
			x, y, row_h = 0, y + row_h, 0
	return layout


def _unique_slug(base: str) -> str:
	slug = frappe.scrub(base or "ai-dashboard").replace("_", "-").strip("-") or "ai-dashboard"
	candidate, n = slug, 1
	while frappe.db.exists("Lumen Dashboard", {"route_slug": candidate}):
		n += 1
		candidate = f"{slug}-{n}"
	return candidate


@frappe.whitelist()
def save_ai_result(widgets, title: str | None = None, slug: str | None = None):
	"""Persist AI-built widgets: into a NEW dashboard (title) or appended to an
	existing one (slug). Frappe enforces create/write permissions on save."""
	widgets = frappe.parse_json(widgets)
	if not isinstance(widgets, list) or not widgets:
		frappe.throw(_("Nothing to save"))

	# conversationally accumulated boards can exceed one generation's cap
	max_save = 16
	prepared = []
	for w in widgets[:max_save]:
		prepared.append(
			{
				"widget_id": "ai" + frappe.generate_hash(length=6),
				"title": w.get("title") or "AI Report",
				"widget_type": w.get("widget_type"),
				"query": w.get("query") or {},
				"style": w.get("style") or {},
			}
		)
	# tint KPI cards in rotation so a KPI row doesn't come out all-blue —
	# but never override a tint the user picked in the preview
	untinted = [p for p in prepared if p["widget_type"] == "Number Card" and not p["style"].get("tint")]
	for i, w in enumerate(untinted):
		w["style"] = {**w["style"], "tint": KPI_TINTS[i % len(KPI_TINTS)]}

	if slug:
		name = frappe.db.get_value("Lumen Dashboard", {"route_slug": slug})
		if not name:
			frappe.throw(_("Dashboard {0} not found").format(slug), frappe.DoesNotExistError)
		doc = frappe.get_doc("Lumen Dashboard", name)
		if not doc.has_permission("write"):
			frappe.throw(_("Not permitted to edit this dashboard"), frappe.PermissionError)
		layout = frappe.parse_json(doc.layout_json or "[]")
		bottom = max((item.get("y", 0) + item.get("h", 0) for item in layout), default=0)
		layout += _auto_layout(prepared, start_y=bottom)
	else:
		doc = frappe.new_doc("Lumen Dashboard")
		doc.dashboard_title = (title or "AI Dashboard").strip()[:120]
		doc.route_slug = _unique_slug(doc.dashboard_title)
		doc.description = _("Created by Ask AI")
		doc.auto_refresh = 1
		doc.is_published = 0
		layout = _auto_layout(prepared)

	for w in prepared:
		doc.append(
			"widgets",
			{
				"widget_id": w["widget_id"],
				"title": w["title"],
				"widget_type": w["widget_type"],
				"query_json": json.dumps(w["query"]),
				"style_json": json.dumps(w["style"]),
				"linked_filters": json.dumps({}),
			},
		)
	doc.layout_json = json.dumps(layout)
	doc.save()
	return {"slug": doc.route_slug, "widgets_added": len(prepared)}
