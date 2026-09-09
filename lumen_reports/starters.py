# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

"""Starter dashboards.

A starter is a ready-made board written against doctypes a Frappe site is
likely to have. Before one is offered we check the doctype exists and the
person can read it, and before one is created every widget is executed
through the query engine and quietly dropped if it does not fit this site's
fields. So a starter either opens as a working dashboard or opens smaller,
never broken.

Starters are drafts. Nothing is published until the person says so.
"""

import json

import frappe
from frappe import _

from lumen_reports import ai, licensing, query_engine

SUBMITTED = ["docstatus", "=", 1]
ITEM_VIA = {"link_field": "item_code", "doctype": "Item"}


def _si(**kwargs):
	q = {"doctype": "Sales Invoice", "filters": [list(SUBMITTED)]}
	q.update(kwargs)
	return q


def _line(**kwargs):
	q = {
		"doctype": "Sales Invoice Item",
		"parent_doctype": "Sales Invoice",
		"filters": [list(SUBMITTED)],
	}
	q.update(kwargs)
	return q


def _pi(**kwargs):
	q = {"doctype": "Purchase Invoice", "filters": [list(SUBMITTED)]}
	q.update(kwargs)
	return q


def _heading(text, subtext=None, level=1):
	style = {"text": text, "level": level, "align": "left"}
	if subtext:
		style["subtext"] = subtext
	return {"title": text, "widget_type": "Heading", "query": {}, "style": style}


def _divider(text=""):
	return {"title": "Divider", "widget_type": "Divider", "query": {}, "style": {"text": text}}


STARTERS = [
	{
		"id": "executive",
		"name": "Executive Overview",
		"description": "The numbers a manager asks for first: revenue, volume, trend, who buys.",
		"doctype": "Sales Invoice",
		"widgets": [
			_heading("Executive overview", "Sales performance at a glance"),
			{
				"title": "Revenue",
				"widget_type": "Number Card",
				"query": _si(aggregate={"function": "sum", "field": "grand_total"}),
				"style": {"tint": "blue"},
			},
			{
				"title": "Invoices",
				"widget_type": "Number Card",
				"query": _si(aggregate={"function": "count"}),
				"style": {"tint": "green"},
			},
			{
				"title": "Average Invoice",
				"widget_type": "Number Card",
				"query": _si(aggregate={"function": "avg", "field": "grand_total"}),
				"style": {"tint": "violet"},
			},
			{
				"title": "Outstanding",
				"widget_type": "Number Card",
				"query": _si(aggregate={"function": "sum", "field": "outstanding_amount"}),
				"style": {"tint": "amber"},
			},
			{
				"title": "Revenue by Month",
				"widget_type": "Line Chart",
				"query": _si(
					aggregate={"function": "sum", "field": "grand_total"},
					group_by={"field": "posting_date", "time_grain": "month"},
				),
				"style": {},
			},
			{
				"title": "Top Customers",
				"widget_type": "Horizontal Bar",
				"query": _si(
					aggregate={"function": "sum", "field": "grand_total"},
					group_by={"field": "customer"},
				),
				"style": {},
			},
			{
				"title": "Invoices by Status",
				"widget_type": "Donut Chart",
				"query": _si(aggregate={"function": "count"}, group_by={"field": "status"}),
				"style": {},
			},
			{
				"title": "Latest Invoices",
				"widget_type": "Table",
				"query": _si(
					fields=["name", "customer", "posting_date", "status", "grand_total"],
					sort={"field": "posting_date", "order": "desc"},
					limit=10,
				),
				"style": {},
			},
		],
	},
	{
		"id": "retail",
		"name": "Products and Retail",
		"description": "What actually sells: products, groups, brands and the hours people buy in.",
		"doctype": "Sales Invoice Item",
		"widgets": [
			_heading("Products and retail", "Sales broken down to the line item"),
			{
				"title": "Units Sold",
				"widget_type": "Number Card",
				"query": _line(aggregate={"function": "sum", "field": "qty"}),
				"style": {"tint": "blue"},
			},
			{
				"title": "Line Revenue",
				"widget_type": "Number Card",
				"query": _line(aggregate={"function": "sum", "field": "amount"}),
				"style": {"tint": "green"},
			},
			{
				"title": "Revenue by Item Group",
				"widget_type": "Bar Chart",
				"query": _line(
					aggregate={"function": "sum", "field": "amount"},
					group_by={"field": "item_group", "via": ITEM_VIA},
				),
				"style": {},
			},
			{
				"title": "Revenue by Brand",
				"widget_type": "Donut Chart",
				"query": _line(
					aggregate={"function": "sum", "field": "amount"},
					group_by={"field": "brand", "via": ITEM_VIA},
				),
				"style": {},
			},
			{
				"title": "Top Items",
				"widget_type": "Horizontal Bar",
				"query": _line(
					aggregate={"function": "sum", "field": "amount"},
					group_by={"field": "item_code"},
				),
				"style": {},
			},
			_divider("When people buy"),
			{
				"title": "Sales by Day and Hour",
				"widget_type": "Heatmap",
				"query": _si(
					aggregate={"function": "sum", "field": "grand_total"},
					group_by={"field": "creation", "time_grain": "weekday"},
					group_by2={"field": "creation", "time_grain": "hour"},
				),
				"style": {},
			},
		],
	},
	{
		"id": "receivables",
		"name": "Receivables",
		"description": "Who owes what, how old it is, and which invoices to chase first.",
		"doctype": "Sales Invoice",
		"widgets": [
			_heading("Receivables", "Money invoiced and not yet collected"),
			{
				"title": "Outstanding",
				"widget_type": "Number Card",
				"query": _si(aggregate={"function": "sum", "field": "outstanding_amount"}),
				"style": {"tint": "amber"},
			},
			{
				"title": "Invoiced",
				"widget_type": "Number Card",
				"query": _si(aggregate={"function": "sum", "field": "grand_total"}),
				"style": {"tint": "blue"},
			},
			{
				"title": "Open Invoices",
				"widget_type": "Number Card",
				"query": _si(
					aggregate={"function": "count"},
					filters=[list(SUBMITTED), ["outstanding_amount", ">", 0]],
				),
				"style": {"tint": "violet"},
			},
			{
				"title": "Outstanding by Customer",
				"widget_type": "Horizontal Bar",
				"query": _si(
					aggregate={"function": "sum", "field": "outstanding_amount"},
					group_by={"field": "customer"},
					filters=[list(SUBMITTED), ["outstanding_amount", ">", 0]],
				),
				"style": {},
			},
			{
				"title": "Outstanding by Status",
				"widget_type": "Bar Chart",
				"query": _si(
					aggregate={"function": "sum", "field": "outstanding_amount"},
					group_by={"field": "status"},
				),
				"style": {},
			},
			{
				"title": "Oldest Open Invoices",
				"widget_type": "Table",
				"query": _si(
					fields=["name", "customer", "due_date", "status", "outstanding_amount"],
					filters=[list(SUBMITTED), ["outstanding_amount", ">", 0]],
					sort={"field": "due_date", "order": "asc"},
					limit=12,
				),
				"style": {},
			},
		],
	},
	{
		"id": "purchasing",
		"name": "Purchasing",
		"description": "Spend by supplier and month, and what is still payable.",
		"doctype": "Purchase Invoice",
		"widgets": [
			_heading("Purchasing", "What the business spends, and with whom"),
			{
				"title": "Total Spend",
				"widget_type": "Number Card",
				"query": _pi(aggregate={"function": "sum", "field": "grand_total"}),
				"style": {"tint": "blue"},
			},
			{
				"title": "Payable",
				"widget_type": "Number Card",
				"query": _pi(aggregate={"function": "sum", "field": "outstanding_amount"}),
				"style": {"tint": "amber"},
			},
			{
				"title": "Bills",
				"widget_type": "Number Card",
				"query": _pi(aggregate={"function": "count"}),
				"style": {"tint": "green"},
			},
			{
				"title": "Spend by Month",
				"widget_type": "Area Chart",
				"query": _pi(
					aggregate={"function": "sum", "field": "grand_total"},
					group_by={"field": "posting_date", "time_grain": "month"},
				),
				"style": {},
			},
			{
				"title": "Spend by Supplier",
				"widget_type": "Horizontal Bar",
				"query": _pi(
					aggregate={"function": "sum", "field": "grand_total"},
					group_by={"field": "supplier"},
				),
				"style": {},
			},
		],
	},
	{
		"id": "work",
		"name": "Team Workload",
		"description": "Open work by person, priority and status. Works on any Frappe site.",
		"doctype": "ToDo",
		"widgets": [
			_heading("Team workload", "Who is carrying what right now"),
			{
				"title": "Open Items",
				"widget_type": "Number Card",
				"query": {
					"doctype": "ToDo",
					"filters": [["status", "=", "Open"]],
					"aggregate": {"function": "count"},
				},
				"style": {"tint": "blue"},
			},
			{
				"title": "By Owner",
				"widget_type": "Horizontal Bar",
				"query": {
					"doctype": "ToDo",
					"filters": [["status", "=", "Open"]],
					"aggregate": {"function": "count"},
					"group_by": {"field": "allocated_to"},
				},
				"style": {},
			},
			{
				"title": "By Priority",
				"widget_type": "Donut Chart",
				"query": {
					"doctype": "ToDo",
					"filters": [["status", "=", "Open"]],
					"aggregate": {"function": "count"},
					"group_by": {"field": "priority"},
				},
				"style": {},
			},
			{
				"title": "Opened by Month",
				"widget_type": "Bar Chart",
				"query": {
					"doctype": "ToDo",
					"aggregate": {"function": "count"},
					"group_by": {"field": "creation", "time_grain": "month"},
				},
				"style": {},
			},
		],
	},
]


def _find(starter_id: str):
	for s in STARTERS:
		if s["id"] == starter_id:
			return s
	frappe.throw(_("Unknown template {0}").format(starter_id), frappe.DoesNotExistError)


def _readable(starter) -> bool:
	"""A starter is only offered when its data actually exists here and the
	person is allowed to read it."""
	doctype = starter["doctype"]
	if not frappe.db.exists("DocType", doctype):
		return False
	# a line-item starter reads through its parent as well
	if doctype.endswith(" Item") and not frappe.db.exists("DocType", "Sales Invoice"):
		return False
	try:
		return bool(frappe.has_permission(doctype, "read"))
	except Exception:
		return False


def _data_widgets(starter):
	return [w for w in starter["widgets"] if w["query"]]


@frappe.whitelist()
def list_starters():
	"""Templates this site can actually build."""
	out = []
	for s in STARTERS:
		if not _readable(s):
			continue
		out.append(
			{
				"id": s["id"],
				"name": s["name"],
				"description": s["description"],
				"doctype": s["doctype"],
				"widget_count": len(_data_widgets(s)),
				"widget_types": [w["widget_type"] for w in s["widgets"]],
			}
		)
	return out


def validate_widgets(starter):
	"""Run every widget once. Anything this site's fields cannot answer is
	dropped rather than saved as a broken tile."""
	kept, dropped = [], []
	for w in starter["widgets"]:
		if not w["query"]:
			kept.append(w)  # a heading or a rule has nothing to run
			continue
		try:
			query_engine.execute(w["query"])
			kept.append(w)
		except Exception:
			# the field does not exist here, or is not readable — say so by
			# leaving it out, and log for the site owner
			frappe.log_error(
				title=f"Lumen starter '{starter['id']}': dropped {w['title']}",
				message=frappe.get_traceback(),
			)
			dropped.append(w["title"])
	return kept, dropped


@frappe.whitelist()
def create_from_starter(starter_id: str, title: str | None = None):
	"""Build a draft dashboard from a template and hand back its slug."""
	licensing.require_license()
	if not frappe.has_permission("Lumen Dashboard", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	starter = _find(starter_id)
	if not _readable(starter):
		frappe.throw(_("This template needs {0}, which you cannot read here").format(starter["doctype"]))

	kept, dropped = validate_widgets(starter)
	if not [w for w in kept if w["query"]]:
		frappe.throw(_("None of this template's widgets fit the data on this site"))

	prepared = [
		{
			"widget_id": "t" + frappe.generate_hash(length=6),
			"title": w["title"],
			"widget_type": w["widget_type"],
			"query": w["query"],
			"style": w["style"],
		}
		for w in kept
	]

	doc = frappe.new_doc("Lumen Dashboard")
	doc.dashboard_title = (title or starter["name"]).strip()[:120]
	doc.route_slug = ai._unique_slug(doc.dashboard_title)
	doc.description = starter["description"]
	doc.auto_refresh = 1
	doc.is_published = 0
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
	doc.layout_json = json.dumps(ai._auto_layout(prepared))
	doc.save()  # frappe enforces the create permission here

	return {
		"name": doc.name,
		"slug": doc.route_slug,
		"widgets": len(prepared),
		"dropped": dropped,
	}
