# Copyright (c) 2026, Lumen and contributors
# Development helper: seed a retail Lumen dashboard over the ERPNext demo
# Sales Invoice data.
# Run with: bench --site <site> execute lumen_reports.retail_dashboard.run

import json

import frappe

SLUG = "retail-sales"
COMPANY = "Lumen Retail (Demo)"

# every widget is scoped to submitted invoices of the demo retail company
BASE_FILTERS = [["docstatus", "=", 1], ["company", "=", COMPANY]]

STATUS_OPTIONS = ["Paid", "Unpaid", "Overdue", "Partly Paid", "Return"]

# dashboard-level filters (new schema: each definition is self-describing)
FILTERS = [
	{
		"name": "status",
		"label": "Status",
		"fieldtype": "Select",
		"source": "parent",
		"fieldname": "status",
		"base_doctype": "Sales Invoice",
		"options": STATUS_OPTIONS,
	},
	{
		"name": "customer",
		"label": "Customer",
		"fieldtype": "Link",
		"source": "parent",
		"fieldname": "customer",
		"base_doctype": "Sales Invoice",
		"link_doctype": "Customer",
	},
	{
		"name": "territory",
		"label": "Territory",
		"fieldtype": "Link",
		"source": "parent",
		"fieldname": "territory",
		"base_doctype": "Sales Invoice",
		"link_doctype": "Territory",
	},
	{
		"name": "Sales Invoice Item::item_code",
		"label": "Item",
		"fieldtype": "Link",
		"source": "child",
		"fieldname": "item_code",
		"child_doctype": "Sales Invoice Item",
		"parent_doctype": "Sales Invoice",
		"base_doctype": "Sales Invoice",
		"link_doctype": "Item",
	},
	{
		"name": "is_return",
		"label": "Sales / Return",
		"fieldtype": "Check",
		"source": "parent",
		"fieldname": "is_return",
		"base_doctype": "Sales Invoice",
	},
]

# every widget is built on Sales Invoice, so it responds to all of these
LINKED = {f["name"]: f["fieldname"] for f in FILTERS}


def _q(**kwargs):
	q = {"doctype": "Sales Invoice", "filters": list(BASE_FILTERS)}
	q.update(kwargs)
	return q


# line-item-grain base (Sales Invoice Item), joined live to Sales Invoice (parent)
# and Item for related fields like brand / item_group
LINE_FILTERS = [
	["docstatus", "=", 1],
	[{"field": "company", "via": {"link_field": "parent", "doctype": "Sales Invoice"}}, "=", COMPANY],
]

ITEM_VIA = {"link_field": "item_code", "doctype": "Item"}


def _li(**kwargs):
	q = {
		"doctype": "Sales Invoice Item",
		"parent_doctype": "Sales Invoice",
		"filters": list(LINE_FILTERS),
	}
	q.update(kwargs)
	return q


def run():
	frappe.flags.in_import = True

	if frappe.db.exists("Lumen Dashboard", {"route_slug": SLUG}):
		frappe.delete_doc("Lumen Dashboard", frappe.db.get_value("Lumen Dashboard", {"route_slug": SLUG}))

	widgets = [
		{
			"widget_id": "revenue",
			"title": "Total Revenue",
			"widget_type": "Number Card",
			"query_json": json.dumps(_q(aggregate={"function": "sum", "field": "grand_total"})),
			"style_json": json.dumps({"tint": "blue"}),
			"linked_filters": json.dumps(LINKED),
		},
		{
			"widget_id": "invoices",
			"title": "Invoices",
			"widget_type": "Number Card",
			"query_json": json.dumps(_q(aggregate={"function": "count"})),
			"style_json": json.dumps({"tint": "green"}),
			"linked_filters": json.dumps(LINKED),
		},
		{
			"widget_id": "outstanding",
			"title": "Outstanding",
			"widget_type": "Number Card",
			"query_json": json.dumps(_q(aggregate={"function": "sum", "field": "outstanding_amount"})),
			"style_json": json.dumps({"tint": "amber"}),
			"linked_filters": json.dumps(LINKED),
		},
		{
			"widget_id": "avg_order",
			"title": "Avg Order Value",
			"widget_type": "Number Card",
			"query_json": json.dumps(_q(aggregate={"function": "avg", "field": "grand_total"})),
			"style_json": json.dumps({"tint": "violet"}),
			"linked_filters": json.dumps(LINKED),
		},
		{
			"widget_id": "revenue_trend",
			"title": "Revenue Over Time",
			"widget_type": "Area Chart",
			"query_json": json.dumps(
				_q(
					aggregate={"function": "sum", "field": "grand_total"},
					group_by={"field": "posting_date", "time_grain": "month"},
				)
			),
			"style_json": json.dumps({"subtitle": "Monthly, submitted invoices"}),
			"linked_filters": json.dumps(LINKED),
		},
		{
			"widget_id": "by_territory",
			"title": "Revenue by Territory",
			"widget_type": "Donut Chart",
			"query_json": json.dumps(
				_q(
					aggregate={"function": "sum", "field": "grand_total"},
					group_by={"field": "territory"},
				)
			),
			"style_json": json.dumps({}),
			"linked_filters": json.dumps(LINKED),
		},
		{
			"widget_id": "by_status",
			"title": "Revenue by Status",
			"widget_type": "Bar Chart",
			"query_json": json.dumps(
				_q(aggregate={"function": "sum", "field": "grand_total"}, group_by={"field": "status"})
			),
			"style_json": json.dumps({}),
			"linked_filters": json.dumps(LINKED),
		},
		{
			"widget_id": "top_customers",
			"title": "Top Customers",
			"widget_type": "Bar Chart",
			"query_json": json.dumps(
				_q(
					aggregate={"function": "sum", "field": "grand_total"},
					group_by={"field": "customer_name"},
				)
			),
			"style_json": json.dumps({"subtitle": "By revenue"}),
			"linked_filters": json.dumps(LINKED),
		},
		{
			"widget_id": "by_brand",
			"title": "Revenue by Brand",
			"widget_type": "Bar Chart",
			"query_json": json.dumps(
				_li(
					aggregate={"function": "sum", "field": "amount"},
					group_by={"field": "brand", "via": ITEM_VIA},
				)
			),
			"style_json": json.dumps({"subtitle": "Line items · joined from Item"}),
			"linked_filters": json.dumps(LINKED),
		},
		{
			"widget_id": "by_item_group",
			"title": "Revenue by Item Group",
			"widget_type": "Donut Chart",
			"query_json": json.dumps(
				_li(
					aggregate={"function": "sum", "field": "amount"},
					group_by={"field": "item_group", "via": ITEM_VIA},
				)
			),
			"style_json": json.dumps({"subtitle": "Line items · joined from Item"}),
			"linked_filters": json.dumps(LINKED),
		},
		{
			"widget_id": "recent",
			"title": "Recent Invoices",
			"widget_type": "Table",
			"query_json": json.dumps(
				_q(
					fields=["name", "customer_name", "posting_date", "grand_total", "status"],
					sort={"field": "posting_date", "order": "desc"},
					limit=12,
				)
			),
			"style_json": json.dumps({}),
			"linked_filters": json.dumps(LINKED),
		},
	]

	layout = [
		{"widget_id": "revenue", "x": 0, "y": 0, "w": 3, "h": 2},
		{"widget_id": "invoices", "x": 3, "y": 0, "w": 3, "h": 2},
		{"widget_id": "outstanding", "x": 6, "y": 0, "w": 3, "h": 2},
		{"widget_id": "avg_order", "x": 9, "y": 0, "w": 3, "h": 2},
		# donut rows are taller so the ring + legend breathe
		{"widget_id": "revenue_trend", "x": 0, "y": 2, "w": 8, "h": 5},
		{"widget_id": "by_territory", "x": 8, "y": 2, "w": 4, "h": 5},
		{"widget_id": "by_status", "x": 0, "y": 7, "w": 4, "h": 4},
		{"widget_id": "top_customers", "x": 4, "y": 7, "w": 8, "h": 4},
		{"widget_id": "by_brand", "x": 0, "y": 11, "w": 8, "h": 5},
		{"widget_id": "by_item_group", "x": 8, "y": 11, "w": 4, "h": 5},
		{"widget_id": "recent", "x": 0, "y": 16, "w": 12, "h": 5},
	]

	frappe.get_doc(
		{
			"doctype": "Lumen Dashboard",
			"dashboard_title": "Retail Sales",
			"route_slug": SLUG,
			"description": "Sales performance for Lumen Retail (Demo) — ERPNext demo data",
			"auto_refresh": 1,
			"is_published": 1,
			"widgets": widgets,
			"layout_json": json.dumps(layout),
			"filters_json": json.dumps(FILTERS),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — CLI demo seeder (bench execute), not a request: it inserts hundreds of docs and commits in batches so a late failure keeps the earlier work

	return {"slug": SLUG, "widgets": len(widgets)}
