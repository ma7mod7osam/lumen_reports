# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

import hashlib
import json
import re

import frappe
from frappe import _

from lumen_reports import licensing, query_engine

CACHE_PREFIX = "lumen_res"
CACHE_TTL_SECONDS = 300

GROUPABLE_FIELDTYPES = {"Select", "Link", "Data", "Date", "Datetime", "Check", "Rating"}
NUMERIC_FIELDTYPES = {"Int", "Float", "Currency", "Percent", "Duration"}
DATE_FIELDTYPES = {"Date", "Datetime"}
COLUMN_FIELDTYPES_EXCLUDED = {
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
	"Button",
	"Fold",
	"Heading",
	"Table",
	"Table MultiSelect",
	"HTML Editor",
	"Text Editor",
	"Code",
	"Attach Image",
	"Attach",
	"Signature",
	"Geolocation",
	"JSON",
	"Password",
}


@frappe.whitelist()
def get_dashboards():
	"""List dashboards visible to the current user."""
	return {
		"dashboards": frappe.get_list(
			"Lumen Dashboard",
			fields=["name", "dashboard_title", "route_slug", "description", "is_published", "modified"],
			order_by="modified desc",
		),
		"can_create": frappe.has_permission("Lumen Dashboard", "create"),
	}


@frappe.whitelist()
def get_dashboard(slug: str):
	"""Full dashboard definition (widgets, layout, filters) for the viewer."""
	doc = _get_dashboard_doc(slug)
	return {
		"name": doc.name,
		"title": doc.dashboard_title,
		"slug": doc.route_slug,
		"description": doc.description,
		"auto_refresh": doc.auto_refresh,
		"is_published": doc.is_published,
		"visible_to_roles": [row.role for row in (doc.visible_to_roles or [])],
		"visible_to_users": [row.user for row in (doc.visible_to_users or [])],
		"can_edit": doc.has_permission("write"),
		"layout": frappe.parse_json(doc.layout_json or "[]"),
		"filters": frappe.parse_json(doc.filters_json or "[]"),
		"theme": frappe.parse_json(doc.theme_json or "{}"),
		"widgets": [
			{
				"widget_id": w.widget_id,
				"title": w.title,
				"widget_type": w.widget_type,
				"query": frappe.parse_json(w.query_json or "{}"),
				"style": frappe.parse_json(w.style_json or "{}"),
				"linked_filters": frappe.parse_json(w.linked_filters or "{}"),
			}
			for w in doc.widgets
		],
	}


@frappe.whitelist()
def run_widget(
	slug: str,
	widget_id: str,
	filter_values: str | dict | None = None,
	cross_filters: str | list | None = None,
):
	"""Execute a widget's saved query with the given dashboard filter values
	and any active cross-filter (a clicked chart segment on a sibling widget).

	The query always comes from the saved document, never from the client,
	so this endpoint cannot be used to run arbitrary queries. Results are
	cached in redis; the cache is invalidated by the same doc-event path
	that drives realtime updates.
	"""
	doc = _get_dashboard_doc(slug)
	widget = next((w for w in doc.widgets if w.widget_id == widget_id), None)
	if not widget:
		frappe.throw(_("Widget {0} not found on dashboard {1}").format(widget_id, slug))

	query = frappe.parse_json(widget.query_json or "{}")
	extra_filters = _build_filters_from_values(doc, widget, frappe.parse_json(filter_values or "{}"))
	extra_filters += _build_cross_filters(query, frappe.parse_json(cross_filters or "[]"))

	cache_key = _result_cache_key(query.get("doctype"), [query, extra_filters, frappe.session.user])
	cached = frappe.cache.get_value(cache_key, expires=True)
	if cached is not None:
		cached["widget_id"] = widget_id
		cached["from_cache"] = True
		return cached

	result = query_engine.execute(query, extra_filters)
	result["widget_id"] = widget_id
	result["generated_at"] = frappe.utils.now()
	frappe.cache.set_value(cache_key, result, expires_in_sec=CACHE_TTL_SECONDS)
	return result


def _result_cache_key(doctype: str, payload) -> str:
	digest = hashlib.sha1(
		json.dumps(payload, sort_keys=True, default=str).encode()
	).hexdigest()  # nosec - cache key, not security
	return f"{CACHE_PREFIX}|{doctype}|{digest}"


def _build_cross_filters(target_query: dict, cross_filters: list) -> list:
	"""Apply a clicked chart dimension to a *target* widget, bridging grains.

	The clicked segment carries where it came from (source base, its parent if
	line-grain, and any `via` join). Depending on the target widget's own grain
	we apply it directly, through an auto parent-join, or as a subquery to the
	invoices that involve it — so a brand click focuses the whole dashboard.
	"""
	if not cross_filters:
		return []
	target_base = target_query.get("doctype")
	target_parent = target_query.get("parent_doctype")
	out = []
	for cf in cross_filters:
		built = _resolve_cross_filter(cf, target_base, target_parent)
		if built:
			out.append(built)
	return out


def _resolve_cross_filter(cf: dict, target_base: str, target_parent: str | None):
	field = cf.get("field")
	value = cf.get("value")
	via = cf.get("via")
	src_base = cf.get("source_doctype")
	src_parent = cf.get("parent_doctype")
	if not field or value in (None, ""):
		return None

	# same grain as the source → apply the exact dimension (related or base)
	if target_base == src_base:
		return [{"field": field, "via": via}, "=", value] if via else [field, "=", value]

	# source is line-grain, target is its parent document → invoices involving it
	if src_parent and target_base == src_parent:
		if via:
			matching = frappe.get_all(via["doctype"], filters={field: value}, pluck="name")
			if not matching:
				return ["name", "in", ["__lumen_no_match__"]]
			parents = frappe.get_all(
				src_base,
				filters={"parenttype": src_parent, via["link_field"]: ["in", matching]},
				pluck="parent",
				distinct=True,
			)
		else:
			parents = frappe.get_all(
				src_base, filters={"parenttype": src_parent, field: value}, pluck="parent", distinct=True
			)
		return ["name", "in", parents or ["__lumen_no_match__"]]

	# source is document-grain (a parent field like territory), target is a
	# line-grain widget on that same document → auto parent-join handles it
	if not src_parent and target_parent == src_base:
		return [field, "=", value]

	return None


# ---------------------------------------------------------------- builder


def _require_builder():
	if not frappe.has_permission("Lumen Dashboard", "write"):
		frappe.throw(_("Not permitted to build dashboards"), frappe.PermissionError)


@frappe.whitelist()
def get_doctypes():
	"""Doctypes the wizard can build widgets on: readable, non-child, non-single."""
	_require_builder()
	readable = set(frappe.get_user().get_can_read())
	rows = frappe.get_all(
		"DocType",
		filters={"istable": 0, "issingle": 0},
		fields=["name", "module"],
		order_by="name",
		limit_page_length=0,
	)
	return [r for r in rows if r.name in readable]


@frappe.whitelist()
def get_doctype_fields(doctype: str, parent_doctype: str | None = None):
	"""Field metadata for the widget wizard, grouped by what they can do.

	`doctype` may be a line-item child table; pass its `parent_doctype` so
	parent fields are offered as related (one-hop) dimensions."""
	_require_builder()
	meta = frappe.get_meta(doctype)
	# child tables carry no direct read perm; this returns metadata only and is
	# builder-gated, and the query layer re-checks read perms on real data
	if not meta.istable and not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Not permitted to read {0}").format(doctype), frappe.PermissionError)

	fields = []
	for df in meta.fields:
		if df.fieldtype in COLUMN_FIELDTYPES_EXCLUDED:
			continue
		fields.append(
			{
				"fieldname": df.fieldname,
				"label": df.label or df.fieldname,
				"fieldtype": df.fieldtype,
				"options": df.options if df.fieldtype in ("Select", "Link") else None,
				"custom": 1 if df.get("is_custom_field") else 0,
			}
		)
	# standard fields are always available
	fields.extend(
		[
			{"fieldname": "name", "label": "ID", "fieldtype": "Data", "options": None},
			{"fieldname": "creation", "label": "Created On", "fieldtype": "Datetime", "options": None},
			{"fieldname": "modified", "label": "Last Modified", "fieldtype": "Datetime", "options": None},
			{"fieldname": "owner", "label": "Created By", "fieldtype": "Data", "options": None},
		]
	)
	return {
		"fields": fields,
		"numeric": [f for f in fields if f["fieldtype"] in NUMERIC_FIELDTYPES],
		"groupable": [f for f in fields if f["fieldtype"] in GROUPABLE_FIELDTYPES | DATE_FIELDTYPES],
		"date": [f for f in fields if f["fieldtype"] in DATE_FIELDTYPES],
		"filter_fields": _build_filter_fields(meta, doctype),
		"related_fields": _build_related_fields(meta, doctype, parent_doctype),
		"line_item_tables": _line_item_tables(meta) if not meta.istable else [],
		"parent_doctype": parent_doctype,
		"title_field": meta.title_field or "name",
	}


# dimension fieldtypes worth pulling from a linked/parent record for grouping
RELATED_DIMENSION_FIELDTYPES = {"Link", "Select", "Date", "Datetime", "Check"}
MAX_RELATED_FIELDS = 60
NOISE_FIELDS = {"naming_series", "amended_from", "letter_head", "select_print_heading"}


def _is_noise(df):
	return df.hidden or df.fieldname in NOISE_FIELDS or df.fieldname.endswith("_naming_series")


def _rank(df, title):
	"""Prefer the title, then fields flagged as list/filter dimensions."""
	score = 0
	if df.fieldname == title:
		score += 4
	if getattr(df, "in_list_view", 0):
		score += 2
	if getattr(df, "in_standard_filter", 0):
		score += 2
	return score


def _target_group_fields(meta, limit=10):
	"""Useful grouping dimensions on a linked doctype: its Link/Select fields
	plus its title field, most-relevant first."""
	title = meta.title_field
	candidates = [
		df
		for df in meta.fields
		if not _is_noise(df)
		and (df.fieldtype in ("Link", "Select") or (df.fieldname == title and df.fieldtype == "Data"))
	]
	candidates.sort(key=lambda df: -_rank(df, title))
	return candidates[:limit]


def _parent_group_fields(meta, limit=16):
	title = meta.title_field
	candidates = [
		df for df in meta.fields if not _is_noise(df) and df.fieldtype in RELATED_DIMENSION_FIELDTYPES
	]
	candidates.sort(key=lambda df: -_rank(df, title))
	return candidates[:limit]


def _build_related_fields(meta, doctype: str, parent_doctype: str | None) -> list:
	"""One-hop related dimensions: fields fetched through this doctype's Link
	fields (e.g. item_code -> Item.brand), plus parent fields for a child base.
	Parent fields come first — they're the most useful for line-item grouping."""
	out = []
	seen = set()

	def add(link_field, target_dt, df, suffix):
		key = f"{link_field}>{target_dt}.{df.fieldname}"
		if key in seen:
			return
		seen.add(key)
		out.append(
			{
				"key": key,
				"label": f"{df.label or df.fieldname} {suffix}",
				"source": "related",
				"field": df.fieldname,
				"fieldtype": df.fieldtype,
				"via": {"link_field": link_field, "doctype": target_dt},
				"link_doctype": df.options if df.fieldtype == "Link" else None,
			}
		)

	# parent fields first (for a child base)
	if meta.istable and parent_doctype:
		try:
			pmeta = frappe.get_meta(parent_doctype)
		except Exception:
			pmeta = None
		if pmeta:
			for df in _parent_group_fields(pmeta):
				add("parent", parent_doctype, df, f"(via {parent_doctype})")

	# then one hop through this doctype's own Link fields
	for lf in meta.fields:
		if lf.fieldtype == "Link" and lf.options and lf.fieldname != "parent" and not _is_noise(lf):
			try:
				tmeta = frappe.get_meta(lf.options)
			except Exception:
				continue
			for df in _target_group_fields(tmeta):
				add(lf.fieldname, lf.options, df, f"(via {lf.label or lf.fieldname})")
		if len(out) >= MAX_RELATED_FIELDS:
			break

	return out[:MAX_RELATED_FIELDS]


def _line_item_tables(meta) -> list:
	"""Child tables worth aggregating (have a numeric field) — offered as a
	line-item grain in the wizard."""
	out = []
	for df in meta.fields:
		if df.fieldtype != "Table" or not df.options:
			continue
		try:
			cmeta = frappe.get_meta(df.options)
		except Exception:
			continue
		if any(cf.fieldtype in NUMERIC_FIELDTYPES for cf in cmeta.fields):
			out.append(
				{
					"table_fieldname": df.fieldname,
					"child_doctype": df.options,
					"label": df.label or df.options,
				}
			)
	return out


# fieldtypes usable as a dashboard filter
FILTER_PARENT_FIELDTYPES = {"Link", "Select", "Check"}


def _build_filter_fields(meta, doctype: str) -> list:
	"""Fields on `doctype` (and its line-item child tables) that can drive a
	dashboard filter. Each entry is a self-contained descriptor the builder
	stores verbatim and the query layer reads back."""
	out = []

	# parent fields
	for df in meta.fields:
		if df.fieldtype not in FILTER_PARENT_FIELDTYPES:
			continue
		out.append(
			{
				"key": df.fieldname,
				"label": df.label or df.fieldname,
				"fieldtype": df.fieldtype,
				"source": "parent",
				"fieldname": df.fieldname,
				"base_doctype": doctype,
				"link_doctype": df.options if df.fieldtype == "Link" else None,
				"options": (df.options or "").split("\n") if df.fieldtype == "Select" else None,
			}
		)

	# line-item (child table) Link fields — e.g. Sales Invoice Item -> item_code,
	# item_group, brand, warehouse. Resolved via subquery at query time.
	for df in meta.fields:
		if df.fieldtype != "Table" or not df.options:
			continue
		try:
			child_meta = frappe.get_meta(df.options)
		except Exception:
			continue
		for cf in child_meta.fields:
			if cf.fieldtype != "Link":
				continue
			out.append(
				{
					"key": f"{df.options}::{cf.fieldname}",
					"label": f"{cf.label or cf.fieldname} (line item)",
					"fieldtype": "Link",
					"source": "child",
					"fieldname": cf.fieldname,
					"child_doctype": df.options,
					"parent_doctype": doctype,
					"base_doctype": doctype,
					"link_doctype": cf.options,
				}
			)

	return out


@frappe.whitelist()
def get_link_options(link_doctype: str, txt: str = "", page_length: int = 20):
	"""Search records of a linked doctype for a Link filter's value picker."""
	if not frappe.has_permission(link_doctype, "read"):
		frappe.throw(_("Not permitted to read {0}").format(link_doctype), frappe.PermissionError)

	meta = frappe.get_meta(link_doctype)
	title_field = meta.title_field or "name"
	fields = ["name"] if title_field == "name" else ["name", title_field]

	or_filters = []
	if txt:
		like = f"%{txt}%"
		or_filters.append(["name", "like", like])
		if title_field != "name":
			or_filters.append([title_field, "like", like])

	rows = frappe.get_list(
		link_doctype,
		or_filters=or_filters,
		fields=fields,
		limit_page_length=frappe.utils.cint(page_length) or 20,
		order_by="modified desc",
	)
	return [{"value": r["name"], "label": r.get(title_field) or r["name"]} for r in rows]


@frappe.whitelist()
def preview_query(query: str | dict):
	"""Run a query for the wizard's live preview. Builder permission required;
	the query engine still enforces read permissions on the target doctype."""
	_require_builder()
	result = query_engine.execute(frappe.parse_json(query))
	result["generated_at"] = frappe.utils.now()
	return result


@frappe.whitelist()
def save_dashboard(payload: str | dict):
	"""Create or update a dashboard from the builder.

	payload: {name?, title, slug, description, auto_refresh, is_published,
	          widgets: [{widget_id, title, widget_type, query, style, linked_filters}],
	          layout: [{widget_id, x, y, w, h}], filters: [...], theme: {...}}
	"""
	licensing.require_license()
	data = frappe.parse_json(payload)

	if data.get("name"):
		doc = frappe.get_doc("Lumen Dashboard", data["name"])
	else:
		doc = frappe.new_doc("Lumen Dashboard")
		slug = data.get("slug") or data.get("title") or ""
		slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
		# a title in Arabic has no Latin letters left after that, so it gets a
		# short neutral address instead of an encoded, unreadable one
		doc.route_slug = slug or "dashboard-" + frappe.generate_hash(length=5)

	doc.dashboard_title = data.get("title") or doc.dashboard_title
	doc.description = data.get("description") or ""
	doc.auto_refresh = 1 if data.get("auto_refresh", 1) else 0
	doc.is_published = 1 if data.get("is_published") else 0
	doc.layout_json = json.dumps(data.get("layout") or [])
	doc.filters_json = json.dumps(data.get("filters") or [])
	doc.theme_json = json.dumps(data.get("theme") or {})

	# audience: which roles / which specific people may see this once published
	doc.set("visible_to_roles", [])
	for role in data.get("visible_to_roles") or []:
		if isinstance(role, str) and role.strip():
			doc.append("visible_to_roles", {"role": role.strip()})
	doc.set("visible_to_users", [])
	for user in data.get("visible_to_users") or []:
		if isinstance(user, str) and user.strip():
			doc.append("visible_to_users", {"user": user.strip()})

	doc.set("widgets", [])
	for w in data.get("widgets") or []:
		doc.append(
			"widgets",
			{
				"widget_id": w.get("widget_id"),
				"title": w.get("title"),
				"widget_type": w.get("widget_type"),
				"query_json": json.dumps(w.get("query") or {}),
				"style_json": json.dumps(w.get("style") or {}),
				"linked_filters": json.dumps(w.get("linked_filters") or {}),
			},
		)

	doc.save()  # frappe enforces create/write permissions here
	return {"name": doc.name, "slug": doc.route_slug}


@frappe.whitelist()
def get_assignable_roles():
	"""Roles a builder can pick as a dashboard audience. Excludes the system
	plumbing roles that would be meaningless or dangerous as an audience."""
	if not frappe.has_permission("Lumen Dashboard", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	skip = {"Administrator", "Guest", "All", "Desk User"}
	return [
		r
		for r in frappe.get_all("Role", filters={"disabled": 0}, pluck="name", order_by="name")
		if r not in skip
	]


@frappe.whitelist()
def get_assignable_users(txt: str = ""):
	"""People a builder can share a dashboard with."""
	if not frappe.has_permission("Lumen Dashboard", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	filters = {"enabled": 1, "user_type": "System User"}
	users = frappe.get_all(
		"User",
		filters=filters,
		or_filters=(
			{"full_name": ("like", f"%{txt}%"), "name": ("like", f"%{txt}%")} if txt else None
		),
		fields=["name", "full_name"],
		order_by="full_name",
		limit_page_length=30,
	)
	return [u for u in users if u.name not in ("Administrator", "Guest")]


@frappe.whitelist()
def delete_dashboard(name: str):
	doc = frappe.get_doc("Lumen Dashboard", name)
	doc.delete()  # permission enforced by frappe
	return {"ok": True}


# ---------------------------------------------------------------- helpers


def _get_dashboard_doc(slug: str):
	name = frappe.db.get_value("Lumen Dashboard", {"route_slug": slug})
	if not name:
		frappe.throw(_("Dashboard {0} not found").format(slug), frappe.DoesNotExistError)
	doc = frappe.get_doc("Lumen Dashboard", name)
	doc.check_permission("read")
	return doc


def _build_filters_from_values(doc, widget, filter_values: dict) -> list:
	"""Translate dashboard filter values into query filters for one widget.

	Only filters declared in the dashboard's filters_json are accepted, and a
	widget only responds to filters listed in its linked_filters mapping.
	Each filter definition carries how to apply it (parent field, line-item
	field, checkbox), so we read the definition rather than trusting the client.
	"""
	if not filter_values:
		return []

	definitions = {f.get("name"): f for f in frappe.parse_json(doc.filters_json or "[]")}
	linked = frappe.parse_json(widget.linked_filters or "{}")
	widget_query = frappe.parse_json(widget.query_json or "{}")
	widget_doctype = widget_query.get("doctype")
	widget_parent = widget_query.get("parent_doctype")

	extra_filters = []
	for filter_name, value in filter_values.items():
		if filter_name not in definitions or filter_name not in linked:
			continue
		if value in (None, "", []):
			continue

		definition = definitions[filter_name]
		source = definition.get("source", "parent")
		# fieldname comes from the definition; fall back to the legacy
		# linked-mapping value (older dashboards stored the fieldname there)
		fieldname = definition.get("fieldname")
		if not fieldname:
			legacy = linked.get(filter_name)
			fieldname = legacy if isinstance(legacy, str) else filter_name

		if source == "child":
			built = _child_filter(widget_doctype, widget_parent, definition, fieldname, value)
			if built:
				extra_filters.append(built)
			continue

		if definition.get("fieldtype") == "Check":
			truthy = str(value).lower() in ("1", "true", "yes")
			extra_filters.append([fieldname, "=", 1 if truthy else 0])
		elif isinstance(value, (list, tuple)):
			if definition.get("fieldtype") in ("Date Range", "Datetime Range") and len(value) == 2:
				extra_filters.append([fieldname, "between", list(value)])
			else:
				extra_filters.append([fieldname, "in", list(value)])
		else:
			extra_filters.append([fieldname, "=", value])
	return extra_filters


def _child_filter(widget_doctype, widget_parent, definition, fieldname, value):
	"""Apply a line-item filter to a widget, whichever grain it is:

	- the widget *is* the line grain (base == the child) → filter the line directly;
	- the widget is the parent document → subquery to the parents that contain a
	  matching line, so parent aggregates filter without join fan-out;
	- otherwise it doesn't apply.
	"""
	child_doctype = definition.get("child_doctype")
	if not child_doctype:
		return None

	if widget_doctype == child_doctype:
		return [fieldname, "=", value]

	if definition.get("parent_doctype") == widget_doctype:
		parents = frappe.get_all(
			child_doctype,
			filters={"parenttype": widget_doctype, fieldname: value},
			pluck="parent",
			distinct=True,
		)
		# empty -> match nothing (a real "no results", not "no filter")
		return ["name", "in", parents or ["__lumen_no_match__"]]

	return None
