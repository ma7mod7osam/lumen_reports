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
from pypika.terms import Function as PkFunction
from pypika.terms import LiteralValue, NullValue

DateFormat = CustomFunction("DATE_FORMAT", ["field", "format"])
TimeToSec = CustomFunction("TIME_TO_SEC", ["field"])
TimeOf = CustomFunction("TIME", ["field"])
DateDiff = CustomFunction("DATEDIFF", ["b", "a"])
NullIf = CustomFunction("NULLIF", ["a", "b"])

AGG_FUNCTIONS = {"count": Count, "sum": Sum, "avg": Avg, "min": Min, "max": Max}

FIELDNAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")

TIME_GRAIN_FORMATS = {
	"hour": "%H:00",  # hour-of-day across all days — peak-hours analysis
	"weekday": "%a",  # Mon..Sun across all weeks (client orders them)
	"day": "%Y-%m-%d",
	"week": "%x-W%v",
	"month": "%Y-%m",
	"year": "%Y",
}

MAX_MATRIX_ROWS = 24
MAX_MATRIX_COLS = 31
MAX_POINTS = 200
MAX_TREE_CHILDREN = 20

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


# ---------------------------------------------------------------- expressions

# whitelisted computed-metric operations — each compiles to a fixed SQL shape;
# fields are meta-validated, numbers are parameter-safe, nothing else is allowed
EXPR_OPS = {"clock", "diff_hours", "diff_minutes", "diff_days", "add", "sub", "mul", "div"}
EXPR_MAX_DEPTH = 5
RESULT_FORMATS = {"clock", "hours", "minutes", "days", "percent"}


def _timestampdiff_seconds(a, b):
	# TIMESTAMPDIFF's unit is a keyword, not a string literal
	return PkFunction("TIMESTAMPDIFF", LiteralValue("SECOND"), a, b)


def _resolve_expr(resolver, node, depth=0):
	"""Compile a computed-metric expression node to a query-builder term.

	node: field name (str) | number | {"op": ..., "args": [node, ...]}
	e.g. average office hours: {"op": "diff_hours", "args": ["in_time", "out_time"]}
	     average check-in time: {"op": "clock", "args": ["in_time"]}
	"""
	if depth > EXPR_MAX_DEPTH:
		frappe.throw(_("Expression too deeply nested"))
	if isinstance(node, (int, float)) and not isinstance(node, bool):
		return node
	if isinstance(node, str):
		return resolver.column(node)
	if isinstance(node, dict) and node.get("via"):
		return resolver.column(node)  # related field reference
	if not isinstance(node, dict):
		frappe.throw(_("Invalid expression node"))

	op = node.get("op")
	if op not in EXPR_OPS:
		frappe.throw(_("Unsupported expression op: {0}").format(str(op)[:20]))
	args = node.get("args") or []
	if not (1 <= len(args) <= 4):
		frappe.throw(_("Expression op {0} needs 1-4 arguments").format(op))
	terms = [_resolve_expr(resolver, a, depth + 1) for a in args]

	if op == "clock":
		# time-of-day as fractional hours since midnight (works for Datetime and Time)
		return TimeToSec(TimeOf(terms[0])) / 3600.0
	if op == "diff_hours":
		return _timestampdiff_seconds(terms[0], terms[1]) / 3600.0
	if op == "diff_minutes":
		return _timestampdiff_seconds(terms[0], terms[1]) / 60.0
	if op == "diff_days":
		return DateDiff(terms[1], terms[0])  # b - a in days
	if op == "add":
		return terms[0] + terms[1]
	if op == "sub":
		return terms[0] - terms[1]
	if op == "mul":
		return terms[0] * terms[1]
	if op == "div":
		return terms[0] / NullIf(terms[1], 0)  # never divide by zero
	return NullValue()


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


def _value_expression(resolver, aggregate: dict):
	"""Build the SQL expression + display format for one measure slot."""
	function = str(aggregate.get("function") or "count").lower()
	if function not in AGG_FUNCTIONS:
		frappe.throw(_("Unsupported aggregate function: {0}").format(function[:20]))
	agg_fn = AGG_FUNCTIONS[function]

	if aggregate.get("expr") is not None:
		# computed metric (office hours, check-in time, margins, ...)
		expr = agg_fn(_resolve_expr(resolver, aggregate["expr"]))
	elif function == "count":
		expr = Count(resolver.base.name)
	else:
		expr = agg_fn(resolver.column(_slot_ref(aggregate)))

	result_format = aggregate.get("format")
	return expr, (result_format if result_format in RESULT_FORMATS else None)


def _measure_label(aggregate: dict) -> str:
	"""Human-ish axis name for a measure slot (style.x_label overrides it)."""
	function = str(aggregate.get("function") or "count").lower()
	if function == "count" or aggregate.get("expr") is not None:
		return function
	field = aggregate.get("field")
	if isinstance(field, dict):
		field = field.get("field")
	return f"{function} {field}" if field else function


def _aggregate(resolver, query, raw_filters):
	aggregate = query.get("aggregate") or {}
	value_expr, result_format = _value_expression(resolver, aggregate)

	# a second measure turns the result into scatter points (x = first, y = second);
	# a third sizes the bubbles
	raw_y = query.get("aggregate_y") or {}
	raw_size = query.get("aggregate_size") or {}
	y_expr = y_format = size_expr = None
	if raw_y:
		y_expr, y_format = _value_expression(resolver, raw_y)
	elif raw_size:
		frappe.throw(_("aggregate_size needs aggregate_y (bubble size is a scatter option)"))
	if raw_size:
		size_expr, _size_format = _value_expression(resolver, raw_size)

	group_by = query.get("group_by") or {}
	group_by2 = query.get("group_by2") or {}

	# resolve every ref first so all joins are registered before we build FROM
	label_col = None
	time_grain = None
	if group_by:
		label_col, time_grain = _label_column(resolver, group_by)
	label2_col = None
	if group_by2:
		if not group_by:
			frappe.throw(_("group_by2 requires group_by"))
		if y_expr is not None:
			frappe.throw(_("a scatter query (aggregate_y) cannot also use group_by2"))
		label2_col, _grain2 = _label_column(resolver, group_by2)
	group_by3 = query.get("group_by3") or {}
	label3_col = None
	if group_by3:
		if not group_by2:
			frappe.throw(_("group_by3 requires group_by2"))
		label3_col, _grain3 = _label_column(resolver, group_by3)

	resolved_filters = _resolve_filters(resolver, raw_filters)

	q = _from_with_joins(resolver)
	q = _apply_filters(resolver, q, resolved_filters)

	# an explicit tree turns the group_by chain into nesting levels instead of
	# a second axis (category -> brand -> item, with totals rolled up)
	if str(query.get("shape") or "") == "tree":
		if not group_by:
			frappe.throw(_("a tree report needs at least one group_by level"))
		levels = [c for c in (label_col, label2_col, label3_col) if c is not None]
		names = [_slot_name(s) for s in (group_by, group_by2, group_by3) if s]
		return _tree(q, levels, names, value_expr, result_format)

	if not group_by:
		if y_expr is not None:
			frappe.throw(_("a scatter query needs group_by — one point per record or category"))
		q = q.select(value_expr.as_("value"))
		rows = q.run(as_dict=True)
		value = rows[0].get("value") if rows else 0
		out = {"result_type": "number", "value": value or 0}
		if result_format:
			out["format"] = result_format
		return out

	if y_expr is not None:
		return _points(
			q,
			label_col,
			(value_expr, result_format, _measure_label(aggregate)),
			(y_expr, y_format, _measure_label(raw_y)),
			size_expr,
		)

	if label2_col is not None:
		return _matrix(q, label_col, label2_col, value_expr, result_format)

	q = q.select(label_col.as_("label"), value_expr.as_("value")).groupby(label_col)
	# order by the expressions themselves (aliases aren't resolvable in ORDER BY here)
	if time_grain:
		q = q.orderby(label_col, order=Order.asc)
	else:
		q = q.orderby(value_expr, order=Order.desc)
	q = q.limit(MAX_GROUPS)

	rows = q.run(as_dict=True)
	out = {
		"result_type": "series",
		"labels": [r.get("label") for r in rows],
		"values": [r.get("value") or 0 for r in rows],
	}
	if result_format:
		out["format"] = result_format
	return out


def _label_column(resolver, slot: dict):
	"""Build the (possibly time-bucketed) label column for a group_by slot."""
	base_col = resolver.column(_slot_ref(slot))
	time_grain = slot.get("time_grain")
	if time_grain:
		if time_grain not in TIME_GRAIN_FORMATS:
			frappe.throw(_("Unsupported time grain: {0}").format(str(time_grain)[:20]))
		return DateFormat(base_col, TIME_GRAIN_FORMATS[time_grain]), time_grain
	return base_col, None


def _slot_name(slot: dict) -> str:
	"""Human level name for a group_by slot ("item_group" -> "Item Group")."""
	field = slot.get("field")
	if isinstance(field, dict):
		field = field.get("field")
	return str(field or "").replace("_", " ").title()


def _tree(q, level_cols, level_names, value_expr, result_format):
	"""Nested roll-up: one branch per level, totals summed up the tree."""
	for i, col in enumerate(level_cols):
		q = q.select(col.as_(f"l{i}"))
	q = q.select(value_expr.as_("value")).groupby(*level_cols).limit(5000)

	root, total = {}, 0
	for entry in q.run(as_dict=True):
		value = entry.get("value") or 0
		total += value
		cursor = root
		for i in range(len(level_cols)):
			key = entry.get(f"l{i}")
			key = "—" if key in (None, "") else str(key)
			bucket = cursor.setdefault(key, {"value": 0, "children": {}})
			bucket["value"] += value
			cursor = bucket["children"]

	def build(children, depth):
		ranked = sorted(children.items(), key=lambda kv: -kv[1]["value"])[:MAX_TREE_CHILDREN]
		nodes = []
		for label, data in ranked:
			node = {
				"label": label,
				"level": depth,
				"level_name": level_names[depth] if depth < len(level_names) else "",
				"value": data["value"],
				"share": (data["value"] / total) if total else 0,
			}
			kids = build(data["children"], depth + 1)
			if kids:
				node["children"] = kids
			nodes.append(node)
		return nodes

	out = {
		"result_type": "tree",
		"levels": level_names,
		"total": total,
		"nodes": build(root, 0),
	}
	if result_format:
		out["format"] = result_format
	return out


def _points(q, label_col, x_slot, y_slot, size_expr):
	"""Two measures per category -> scatter/bubble points (price vs volume...).
	x_slot/y_slot are (expression, format, axis label) triples."""
	x_expr, x_format, x_label = x_slot
	y_expr, y_format, y_label = y_slot

	q = q.select(label_col.as_("label"), x_expr.as_("x"), y_expr.as_("y"))
	if size_expr is not None:
		q = q.select(size_expr.as_("size"))
	# keep the strongest points when a category explodes past the cap
	q = q.groupby(label_col).orderby(y_expr, order=Order.desc).limit(MAX_POINTS)

	points = []
	for entry in q.run(as_dict=True):
		point = {"label": entry.get("label"), "x": entry.get("x") or 0, "y": entry.get("y") or 0}
		if size_expr is not None:
			point["size"] = entry.get("size") or 0
		points.append(point)

	out = {"result_type": "points", "points": points, "x_label": x_label, "y_label": y_label}
	if x_format:
		out["x_format"] = x_format
	if y_format:
		out["y_format"] = y_format
	return out


def _matrix(q, row_col, col_col, value_expr, result_format):
	"""Two-dimensional grouping -> heatmap-shaped result
	{rows, cols, values[row][col]} (e.g. weekday x hour peak analysis)."""
	q = (
		q.select(row_col.as_("r"), col_col.as_("c"), value_expr.as_("value"))
		.groupby(row_col, col_col)
		.limit(2000)
	)
	raw = q.run(as_dict=True)

	# rank rows/cols by total so the caps keep the strongest slices...
	row_totals, col_totals, cells = {}, {}, {}
	for entry in raw:
		r, c, v = entry.get("r"), entry.get("c"), entry.get("value") or 0
		row_totals[r] = row_totals.get(r, 0) + v
		col_totals[c] = col_totals.get(c, 0) + v
		cells[(r, c)] = v
	rows = sorted(row_totals, key=lambda k: -row_totals[k])[:MAX_MATRIX_ROWS]
	cols = sorted(col_totals, key=lambda k: -col_totals[k])[:MAX_MATRIX_COLS]
	# ...then display them in natural label order (client fixes weekday order)
	rows = sorted(rows, key=lambda x: (x is None, str(x)))
	cols = sorted(cols, key=lambda x: (x is None, str(x)))

	out = {
		"result_type": "matrix",
		"rows": rows,
		"cols": cols,
		"values": [[cells.get((r, c), 0) for c in cols] for r in rows],
	}
	if result_format:
		out["format"] = result_format
	return out


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
