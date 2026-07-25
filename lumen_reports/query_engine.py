# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

"""Permission-aware query engine.

Takes a JSON query definition and executes it through frappe.get_list so that
role permissions, user permissions and permission query conditions all apply.
Every SQL expression is constructed here from validated components — user
supplied strings are never interpolated into SQL.

Query definition shape:
{
    "doctype": "Sales Invoice",
    "aggregate": {"function": "sum", "field": "grand_total"},   # omit for table queries
    "group_by": {"field": "posting_date", "time_grain": "month"},  # optional
    "fields": ["name", "customer", "grand_total"],              # table queries only
    "filters": [["status", "=", "Paid"], ...],
    "sort": {"field": "grand_total", "order": "desc"},          # optional
    "limit": 100                                                # optional
}
"""

import re

import frappe
from frappe import _

AGGREGATE_FUNCTIONS = {"count", "sum", "avg", "min", "max"}

FILTER_OPERATORS = {
	"=",
	"!=",
	">",
	"<",
	">=",
	"<=",
	"like",
	"not like",
	"in",
	"not in",
	"between",
	"is",
	"descendants of",
	"ancestors of",
}

STANDARD_FIELDS = {
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
}

# DATE_FORMAT patterns per time grain (constructed server-side, never from input)
TIME_GRAIN_FORMATS = {
	"hour": "%H:00",  # hour-of-day across all days — peak-hours analysis
	"weekday": "%a",  # Mon..Sun across all weeks
	"day": "%Y-%m-%d",
	"week": "%x-W%v",
	"month": "%Y-%m",
	"year": "%Y",
}

FIELDNAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")

DEFAULT_LIMIT = 100
MAX_LIMIT = 1000
MAX_GROUPS = 500

NO_VALUE_FIELDTYPES = {
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
	"Button",
	"Fold",
	"Heading",
	"Table",
	"Table MultiSelect",
}


def execute(query: dict, extra_filters: list | None = None) -> dict:
	"""Execute a validated query definition and return rows.

	Delegates to report_engine (frappe.qb joins) when the query needs a
	line-item base or one-hop related fields; otherwise uses the simple,
	fully permission-aware frappe.get_list path below.
	"""
	if not isinstance(query, dict):
		frappe.throw(_("Query must be an object"))

	doctype = query.get("doctype")
	if not doctype or not isinstance(doctype, str):
		frappe.throw(_("Query must specify a doctype"))

	meta = frappe.get_meta(doctype)  # raises DoesNotExistError for unknown doctypes

	needs_expr = (query.get("aggregate") or {}).get("expr") is not None
	needs_matrix = bool(query.get("group_by2"))
	if meta.istable or query.get("parent_doctype") or needs_expr or needs_matrix or _uses_related_fields(query):
		from lumen_reports import report_engine

		return report_engine.execute(query, extra_filters)

	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Not permitted to read {0}").format(doctype), frappe.PermissionError)

	filters = _validate_filters(meta, doctype, list(query.get("filters") or []))
	if extra_filters:
		filters += _validate_filters(meta, doctype, list(extra_filters))

	if query.get("aggregate"):
		return _execute_aggregate(meta, doctype, query, filters)
	return _execute_rows(meta, doctype, query, filters)


def _uses_related_fields(query: dict) -> bool:
	"""True if any field reference in the query fetches through a Link (has a
	`via` spec) — those require the join-capable report engine."""

	def is_related(ref):
		return isinstance(ref, dict) and ref.get("via")

	agg = query.get("aggregate") or {}
	if is_related(agg.get("field")):
		return True
	if is_related((query.get("group_by") or {}).get("field")):
		return True
	if is_related((query.get("sort") or {}).get("field")):
		return True
	for ref in query.get("fields") or []:
		if is_related(ref):
			return True
	for f in query.get("filters") or []:
		if isinstance(f, (list, tuple)) and f and is_related(f[0]):
			return True
	return False


# ---------------------------------------------------------------- validation


def _validate_fieldname(meta, doctype: str, fieldname) -> str:
	if not isinstance(fieldname, str) or not FIELDNAME_PATTERN.match(fieldname):
		frappe.throw(_("Invalid field name: {0}").format(frappe.bold(str(fieldname)[:50])))
	if fieldname in STANDARD_FIELDS:
		return fieldname
	df = meta.get_field(fieldname)
	if not df or df.fieldtype in NO_VALUE_FIELDTYPES:
		frappe.throw(_("Field {0} does not exist on {1}").format(fieldname, doctype))
	return fieldname


def _validate_filters(meta, doctype: str, filters: list) -> list:
	validated = []
	for f in filters:
		if not isinstance(f, (list, tuple)) or len(f) != 3:
			frappe.throw(_("Each filter must be [field, operator, value]"))
		fieldname, operator, value = f
		fieldname = _validate_fieldname(meta, doctype, fieldname)
		if not isinstance(operator, str) or operator.lower() not in FILTER_OPERATORS:
			frappe.throw(_("Unsupported filter operator: {0}").format(str(operator)[:20]))
		operator = operator.lower()
		# strict value shapes: a malformed filter must fail loudly, not silently
		# match nothing (this also lets the AI self-repair loop catch it)
		if operator == "between" and not (isinstance(value, (list, tuple)) and len(value) == 2):
			frappe.throw(_("'between' needs a two-element list, e.g. [\"2026-01-01\", \"2026-12-31\"]"))
		if operator in ("in", "not in") and not isinstance(value, (list, tuple)):
			frappe.throw(_("'{0}' needs a list of values").format(operator))
		validated.append([doctype, fieldname, operator, value])
	return validated


def _qualified(doctype: str, fieldname: str) -> str:
	return f"`tab{doctype}`.`{fieldname}`"


# ---------------------------------------------------------------- aggregates


def _execute_aggregate(meta, doctype: str, query: dict, filters: list) -> dict:
	aggregate = query.get("aggregate") or {}
	function = str(aggregate.get("function") or "count").lower()
	if function not in AGGREGATE_FUNCTIONS:
		frappe.throw(_("Unsupported aggregate function: {0}").format(function[:20]))

	if function == "count":
		agg_field = "name"
	else:
		agg_field = _validate_fieldname(meta, doctype, aggregate.get("field"))

	value_expr = f"{function}({_qualified(doctype, agg_field)}) as value"

	group_by = query.get("group_by") or {}
	if not group_by:
		rows = frappe.get_list(doctype, filters=filters, fields=[value_expr])
		value = rows[0].value if rows else 0
		return {"result_type": "number", "value": value or 0}

	group_field = _validate_fieldname(meta, doctype, group_by.get("field"))
	time_grain = group_by.get("time_grain")

	if time_grain:
		if time_grain not in TIME_GRAIN_FORMATS:
			frappe.throw(_("Unsupported time grain: {0}").format(str(time_grain)[:20]))
		date_format = TIME_GRAIN_FORMATS[time_grain]
		# unqualified column: db_query's table-extraction regex chokes on
		# `tabX` appearing inside a function call
		label_expr = f"DATE_FORMAT(`{group_field}`, '{date_format}') as label"
		order_by = "label asc"
	else:
		label_expr = f"{_qualified(doctype, group_field)} as label"
		order_by = "value desc"

	rows = frappe.get_list(
		doctype,
		filters=filters,
		fields=[label_expr, value_expr],
		group_by="label",
		order_by=order_by,
		limit_page_length=MAX_GROUPS,
	)
	return {
		"result_type": "series",
		"labels": [r.label for r in rows],
		"values": [r.value or 0 for r in rows],
	}


# ---------------------------------------------------------------- table rows


def _execute_rows(meta, doctype: str, query: dict, filters: list) -> dict:
	requested = query.get("fields") or ["name"]
	if not isinstance(requested, list):
		frappe.throw(_("fields must be a list"))
	fieldnames = [_validate_fieldname(meta, doctype, fn) for fn in requested[:40]]

	order_by = None
	sort = query.get("sort") or {}
	if sort:
		sort_field = _validate_fieldname(meta, doctype, sort.get("field"))
		sort_order = "desc" if str(sort.get("order", "asc")).lower() == "desc" else "asc"
		order_by = f"{_qualified(doctype, sort_field)} {sort_order}"

	limit = min(frappe.utils.cint(query.get("limit")) or DEFAULT_LIMIT, MAX_LIMIT)
	start = max(frappe.utils.cint(query.get("start")), 0)

	rows = frappe.get_list(
		doctype,
		filters=filters,
		fields=[_qualified(doctype, fn) for fn in fieldnames],
		order_by=order_by,
		limit_start=start,
		limit_page_length=limit,
	)
	total = frappe.get_list(
		doctype, filters=filters, fields=[f"count({_qualified(doctype, 'name')}) as total"]
	)[0].total

	columns = []
	for fn in fieldnames:
		df = meta.get_field(fn)
		columns.append(
			{
				"fieldname": fn,
				"label": _(df.label) if df and df.label else _(fn.replace("_", " ").title()),
				"fieldtype": df.fieldtype if df else "Data",
			}
		)
	return {
		"result_type": "rows",
		"columns": columns,
		"rows": rows,
		"total": total,
		"start": start,
		"limit": limit,
	}
