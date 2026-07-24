# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

"""Join-capable report engine.

Extends the single-doctype query engine with:
- a base that may be a child table (line-item grain), and
- one-hop related fields fetched through Link fields (e.g. Sales Invoice Item
  -> item_code -> Item.brand), or through the parent of a child base.

Built with frappe.qb (parameterised values, field names validated against meta),
so it is safe against injection. Read permission is enforced on the base doctype
and on every joined doctype.

A "related" field reference is `{"field": "brand", "via": {"link_field":
"item_code", "doctype": "Item"}}`. A plain string references a base column, and
for a child base a bare name that is not on the child auto-resolves to the parent.
"""

import re

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Avg, Count, Max, Min, Sum
from pypika import CustomFunction

DateFormat = CustomFunction("DATE_FORMAT", ["field", "format"])

AGG_FUNCTIONS = {"count": Count, "sum": Sum, "avg": Avg, "min": Min, "max": Max}

FIELDNAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")

TIME_GRAIN_FORMATS = {
	"hour": "%H:00",  # hour-of-day across all days — peak-hours analysis
	"day": "%Y-%m-%d",
	"week": "%x-W%v",
	"month": "%Y-%m",
	"year": "%Y",
}

STANDARD_FIELDS = {"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx"}

FILTER_OPERATORS = {"=", "!=", ">", "<", ">=", "<=", "like", "not like", "in", "not in", "between"}

DEFAULT_LIMIT = 100
MAX_LIMIT = 1000
MAX_GROUPS = 500


class _Resolver:
	"""Resolves field references to qb columns, registering joins as it goes."""

	def __init__(self, base_doctype, parent_doctype=None):
		self.base_doctype = base_doctype
		self.base_meta = frappe.get_meta(base_doctype)
		self.parent_doctype = parent_doctype
		self.base = frappe.qb.DocType(base_doctype)
		self.joins = {}  # (link_field, target_doctype) -> {"table":, "on":}
		self._checked_perms = set()

	# -------------------------------------------------------------- helpers

	def _validate_field(self, meta, doctype, fieldname):
		if not isinstance(fieldname, str) or not FIELDNAME_PATTERN.match(fieldname):
			frappe.throw(_("Invalid field name: {0}").format(str(fieldname)[:50]))
		if fieldname in STANDARD_FIELDS:
			return
		if not meta.get_field(fieldname):
			frappe.throw(_("Field {0} does not exist on {1}").format(fieldname, doctype))

	def _check_perm(self, doctype):
		if doctype in self._checked_perms:
			return
		if not frappe.has_permission(doctype, "read"):
			frappe.throw(_("Not permitted to read {0}").format(doctype), frappe.PermissionError)
		self._checked_perms.add(doctype)

	def _join_table(self, link_field, target_doctype):
		key = (link_field, target_doctype)
		if key in self.joins:
			return self.joins[key]["table"]

		# validate the join is legitimate: either the parent link of a child
		# base, or a real Link field on the base pointing at target_doctype
		if link_field == "parent":
			if not self.base_meta.istable or target_doctype != self.parent_doctype:
				frappe.throw(_("Invalid parent join"))
			on_key = "name"
		else:
			df = self.base_meta.get_field(link_field)
			if not df or df.fieldtype not in ("Link", "Dynamic Link") or df.options != target_doctype:
				frappe.throw(_("Invalid related field via {0}").format(link_field))
			on_key = "name"

		self._check_perm(target_doctype)
		alias = f"via_{link_field}"
		table = frappe.qb.DocType(target_doctype).as_(alias)
		self.joins[key] = {
			"table": table,
			"on": self.base[link_field] == table[on_key],
		}
		return table

	# -------------------------------------------------------------- resolve

	def column(self, ref):
		"""ref: str (base or auto parent) | {"field":..., "via":{link_field, doctype}}."""
		if isinstance(ref, str):
			field = ref
			via = None
		elif isinstance(ref, dict):
			field = ref.get("field")
			via = ref.get("via")
		else:
			frappe.throw(_("Invalid field reference"))

		if via:
			target_doctype = via.get("doctype")
			link_field = via.get("link_field")
			if not target_doctype or not link_field:
				frappe.throw(_("Related field needs link_field and doctype"))
			table = self._join_table(link_field, target_doctype)
			self._validate_field(frappe.get_meta(target_doctype), target_doctype, field)
			return table[field]

		# bare name: base column, or auto parent field for a child base
		if self.base_meta.get_field(field) or field in STANDARD_FIELDS:
			self._validate_field(self.base_meta, self.base_doctype, field)
			return self.base[field]

		if self.base_meta.istable and self.parent_doctype:
			parent_meta = frappe.get_meta(self.parent_doctype)
			if parent_meta.get_field(field) or field in STANDARD_FIELDS:
				table = self._join_table("parent", self.parent_doctype)
				return table[field]

		frappe.throw(_("Field {0} not found on {1}").format(field, self.base_doctype))

	def label_for(self, ref):
		if isinstance(ref, str):
			df = self.base_meta.get_field(ref)
			return _(df.label) if df and df.label else _(ref.replace("_", " ").title())
		field = ref.get("field")
		doctype = ref.get("via", {}).get("doctype", self.base_doctype)
		df = frappe.get_meta(doctype).get_field(field)
		return _(df.label) if df and df.label else _(field.replace("_", " ").title())

	def fieldtype_for(self, ref):
		if isinstance(ref, str):
			df = self.base_meta.get_field(ref)
			return df.fieldtype if df else "Data"
		field = ref.get("field")
		doctype = ref.get("via", {}).get("doctype", self.base_doctype)
		df = frappe.get_meta(doctype).get_field(field)
		return df.fieldtype if df else "Data"


def _slot_ref(slot: dict):
	"""A group_by/aggregate/sort slot names a field and may carry a `via` join
	spec beside it: {"field": "brand", "via": {...}}. Return the field
	reference the resolver understands (string for base, dict for related)."""
	if not slot:
		return None
	if slot.get("via"):
		return {"field": slot.get("field"), "via": slot.get("via")}
	return slot.get("field")


def execute(query: dict, extra_filters: list | None = None) -> dict:
	if not isinstance(query, dict):
		frappe.throw(_("Query must be an object"))

	base_doctype = query.get("doctype")
	if not base_doctype:
		frappe.throw(_("Query must specify a doctype"))

	base_meta = frappe.get_meta(base_doctype)
	parent_doctype = query.get("parent_doctype")
	if base_meta.istable and not parent_doctype:
		frappe.throw(_("Line-item queries must specify parent_doctype"))

	# permission on the perm-carrying doctype (parent for a child base)
	perm_doctype = parent_doctype if base_meta.istable else base_doctype
	if not frappe.has_permission(perm_doctype, "read"):
		frappe.throw(_("Not permitted to read {0}").format(perm_doctype), frappe.PermissionError)

	resolver = _Resolver(base_doctype, parent_doctype)

	# collect filters (query.filters + base scoping + dashboard extra_filters)
	raw_filters = list(query.get("filters") or [])
	if extra_filters:
		raw_filters += list(extra_filters)

	if query.get("aggregate"):
		return _aggregate(resolver, query, raw_filters)
	return _rows(resolver, query, raw_filters)


# ---------------------------------------------------------------- builders


def _resolve_filters(resolver, raw_filters):
	"""Resolve filter refs to columns FIRST (registering any joins they need),
	so every join is known before the FROM clause is built."""
	resolved = []
	for f in raw_filters:
		if not isinstance(f, (list, tuple)) or len(f) != 3:
			frappe.throw(_("Each filter must be [field, operator, value]"))
		ref, operator, value = f
		operator = str(operator).lower()
		if operator not in FILTER_OPERATORS:
			frappe.throw(_("Unsupported operator: {0}").format(operator[:20]))
		resolved.append((resolver.column(ref), operator, value))
	return resolved


def _apply_filters(resolver, q, resolved):
	# child base: constrain to the intended parent doctype
	if resolver.base_meta.istable:
		q = q.where(resolver.base.parenttype == resolver.parent_doctype)
	for col, operator, value in resolved:
		q = q.where(_apply_operator(col, operator, value))
	return q


def _apply_operator(col, operator, value):
	if operator == "=":
		return col == value
	if operator == "!=":
		return col != value
	if operator == ">":
		return col > value
	if operator == "<":
		return col < value
	if operator == ">=":
		return col >= value
	if operator == "<=":
		return col <= value
	if operator == "like":
		return col.like(value)
	if operator == "not like":
		return col.not_like(value)
	if operator == "in":
		return col.isin(list(value) if isinstance(value, (list, tuple)) else [value])
	if operator == "not in":
		return col.notin(list(value) if isinstance(value, (list, tuple)) else [value])
	if operator == "between" and isinstance(value, (list, tuple)) and len(value) == 2:
		return col[value[0] : value[1]]
	frappe.throw(_("Unsupported operator: {0}").format(operator[:20]))


def _from_with_joins(resolver):
	q = frappe.qb.from_(resolver.base)
	for spec in resolver.joins.values():
		q = q.left_join(spec["table"]).on(spec["on"])
	return q


def _aggregate(resolver, query, raw_filters):
	aggregate = query.get("aggregate") or {}
	function = str(aggregate.get("function") or "count").lower()
	if function not in AGG_FUNCTIONS:
		frappe.throw(_("Unsupported aggregate function: {0}").format(function[:20]))
	agg_fn = AGG_FUNCTIONS[function]

	if function == "count":
		value_expr = Count(resolver.base.name)
	else:
		value_col = resolver.column(_slot_ref(aggregate))
		value_expr = agg_fn(value_col)

	group_by = query.get("group_by") or {}

	# resolve every ref first so all joins are registered before we build FROM
	label_col = None
	time_grain = None
	if group_by:
		base_label_col = resolver.column(_slot_ref(group_by))
		time_grain = group_by.get("time_grain")
		if time_grain:
			if time_grain not in TIME_GRAIN_FORMATS:
				frappe.throw(_("Unsupported time grain: {0}").format(str(time_grain)[:20]))
			label_col = DateFormat(base_label_col, TIME_GRAIN_FORMATS[time_grain])
		else:
			label_col = base_label_col

	resolved_filters = _resolve_filters(resolver, raw_filters)

	q = _from_with_joins(resolver)
	q = _apply_filters(resolver, q, resolved_filters)

	if not group_by:
		q = q.select(value_expr.as_("value"))
		rows = q.run(as_dict=True)
		value = rows[0].get("value") if rows else 0
		return {"result_type": "number", "value": value or 0}

	q = q.select(label_col.as_("label"), value_expr.as_("value")).groupby(label_col)
	# order by the expressions themselves (aliases aren't resolvable in ORDER BY here)
	if time_grain:
		q = q.orderby(label_col, order=Order.asc)
	else:
		q = q.orderby(value_expr, order=Order.desc)
	q = q.limit(MAX_GROUPS)

	rows = q.run(as_dict=True)
	return {
		"result_type": "series",
		"labels": [r.get("label") for r in rows],
		"values": [r.get("value") or 0 for r in rows],
	}


def _rows(resolver, query, raw_filters):
	requested = query.get("fields") or ["name"]
	if not isinstance(requested, list):
		frappe.throw(_("fields must be a list"))
	refs = requested[:40]

	cols = [resolver.column(ref) for ref in refs]

	sort = query.get("sort") or {}
	order_ref = _slot_ref(sort)
	order_dir = str(sort.get("order", "asc")).lower()
	order_col = resolver.column(order_ref) if order_ref else None

	limit = min(frappe.utils.cint(query.get("limit")) or DEFAULT_LIMIT, MAX_LIMIT)
	start = max(frappe.utils.cint(query.get("start")), 0)

	resolved_filters = _resolve_filters(resolver, raw_filters)

	q = _from_with_joins(resolver)
	q = _apply_filters(resolver, q, resolved_filters)
	for i, col in enumerate(cols):
		q = q.select(col.as_(f"c{i}"))
	if order_col is not None:
		q = q.orderby(order_col, order=Order.desc if order_dir == "desc" else Order.asc)
	q = q.limit(limit).offset(start)

	raw = q.run(as_dict=True)

	columns = []
	for i, ref in enumerate(refs):
		columns.append(
			{
				"fieldname": f"c{i}",
				"label": resolver.label_for(ref),
				"fieldtype": resolver.fieldtype_for(ref),
			}
		)
	rows = [{f"c{i}": r.get(f"c{i}") for i in range(len(refs))} for r in raw]

	# total (respect the same scope/filters)
	cq = _from_with_joins(resolver)
	cq = _apply_filters(resolver, cq, resolved_filters)
	cq = cq.select(Count(resolver.base.name).as_("total"))
	total = cq.run(as_dict=True)[0].get("total")

	return {
		"result_type": "rows",
		"columns": columns,
		"rows": rows,
		"total": total,
		"start": start,
		"limit": limit,
	}
