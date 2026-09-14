# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.

"""LumenPOS Insights: what LumenPOS may call at runtime.

LumenPOS is a separate app under a different licence, so the two apps meet only
here: two whitelisted calls and one documented URL. Nothing in this app imports
LumenPOS, and LumenPOS copies nothing from this one.

Contract version 1
- get_status (GET) reads state and changes nothing, so the POS can decide what
  to show: a request for a role, a setup button, or the dashboard itself.
- ensure_dashboard (POST) creates the POS sales dashboard once and never
  overwrites it afterwards, because people customise dashboards they own.
- The dashboard is embedded at /lumen/embed/<slug> in a same-origin iframe,
  with optional ?lang=en|ar and ?theme=light|dark.

Access follows the ordinary Lumen rules. The viewer needs a Lumen role (Lumen
Restricted Viewer is enough, and shows only dashboards that name one of their
roles), and every number still runs through the permission-checked engines.
Refusals come back as a status and a message, never as an exception, so the POS
can show them as they are.
"""

import json

import frappe
from frappe import _

from lumen_reports import licensing, starters
from lumen_reports.www.lumen import APP_ROLES

CONTRACT_VERSION = 1
SLUG = "lumenpos-sales"
AUDIENCE_ROLE = "LumenPOS Manager"

# POS Invoice only. Closing a register consolidates POS Invoices into Sales
# Invoices and both stay submitted, so reading both would count every sale twice.
SOURCE = "POS Invoice"
LINES = "POS Invoice Item"
PAYMENTS = "Sales Invoice Payment"  # shared with Sales Invoice; the engine keeps parenttype = POS Invoice

DESCRIPTION = "Takings, outlets, payment methods, items and busy hours from LumenPOS."

FILTERS = [
	{
		"name": "posting_date",
		"label": "Date",
		"fieldtype": "Date Range",
		"source": "parent",
		"fieldname": "posting_date",
		"base_doctype": SOURCE,
		"default": "this_month",
	},
	{
		"name": "pos_profile",
		"label": "Outlet",
		"fieldtype": "Link",
		"source": "parent",
		"fieldname": "pos_profile",
		"base_doctype": SOURCE,
		"link_doctype": "POS Profile",
	},
	{
		"name": "customer",
		"label": "Customer",
		"fieldtype": "Link",
		"source": "parent",
		"fieldname": "customer",
		"base_doctype": SOURCE,
		"link_doctype": "Customer",
	},
	{
		"name": f"{PAYMENTS}::mode_of_payment",
		"label": "Payment method",
		"fieldtype": "Link",
		"source": "child",
		"fieldname": "mode_of_payment",
		"child_doctype": PAYMENTS,
		"parent_doctype": SOURCE,
		"base_doctype": SOURCE,
		"link_doctype": "Mode of Payment",
	},
	{
		"name": f"{LINES}::item_code",
		"label": "Item",
		"fieldtype": "Link",
		"source": "child",
		"fieldname": "item_code",
		"child_doctype": LINES,
		"parent_doctype": SOURCE,
		"base_doctype": SOURCE,
		"link_doctype": "Item",
	},
]


def _linked(*names):
	fieldnames = {f["name"]: f["fieldname"] for f in FILTERS}
	return {name: fieldnames[name] for name in names}


# a line-item widget answers to the document filters plus its own line filter.
# A filter on a different child table (payments on an items chart) has nothing
# to match there, so it is not linked rather than silently ignored
ON_INVOICES = _linked(*(f["name"] for f in FILTERS))
ON_LINES = _linked("posting_date", "pos_profile", "customer", f"{LINES}::item_code")
ON_PAYMENTS = _linked("posting_date", "pos_profile", "customer", f"{PAYMENTS}::mode_of_payment")

SALES = {"function": "sum", "field": "grand_total"}  # returns are negative, so this nets them
NOT_RETURN = ["is_return", "=", 0]
RETURN = ["is_return", "=", 1]


def _invoices(**query):
	filters = [["docstatus", "=", 1], *query.pop("filters", [])]
	return {"doctype": SOURCE, "filters": filters, **query}


def _children(doctype, **query):
	filters = [["docstatus", "=", 1], *query.pop("filters", [])]
	return {"doctype": doctype, "parent_doctype": SOURCE, "filters": filters, **query}


# (widget_id, title, type, query, style, linked filters, layout x y w h)
WIDGETS = [
	("net_sales", "Net Sales", "Number Card", _invoices(aggregate=SALES), {"tint": "blue"}, ON_INVOICES, (0, 0, 3, 2)),
	(
		"invoices",
		"Invoices",
		"Number Card",
		_invoices(aggregate={"function": "count"}, filters=[NOT_RETURN]),
		{"tint": "green"},
		ON_INVOICES,
		(3, 0, 3, 2),
	),
	(
		"avg_basket",
		"Average Basket",
		"Number Card",
		_invoices(aggregate={"function": "avg", "field": "grand_total"}, filters=[NOT_RETURN]),
		{"tint": "violet"},
		ON_INVOICES,
		(6, 0, 3, 2),
	),
	(
		"returns",
		"Returns",
		"Number Card",
		_invoices(aggregate=SALES, filters=[RETURN]),
		{"tint": "amber"},
		ON_INVOICES,
		(9, 0, 3, 2),
	),
	(
		"sales_by_day",
		"Sales by Day",
		"Line Chart",
		_invoices(aggregate=SALES, group_by={"field": "posting_date", "time_grain": "day"}),
		{},
		ON_INVOICES,
		(0, 2, 8, 5),
	),
	(
		"by_outlet",
		"Sales by Outlet",
		"Horizontal Bar",
		_invoices(aggregate=SALES, group_by={"field": "pos_profile"}),
		{},
		ON_INVOICES,
		(8, 2, 4, 5),
	),
	(
		"payment_mix",
		"Payment Mix",
		"Donut Chart",
		_children(PAYMENTS, aggregate={"function": "sum", "field": "amount"}, group_by={"field": "mode_of_payment"}),
		{},
		ON_PAYMENTS,
		(0, 7, 4, 5),
	),
	(
		"top_items",
		"Top Items",
		"Horizontal Bar",
		_children(LINES, aggregate={"function": "sum", "field": "amount"}, group_by={"field": "item_code"}),
		{},
		ON_LINES,
		(4, 7, 8, 5),
	),
	(
		"by_cashier",
		"Sales by Cashier",
		"Horizontal Bar",
		_invoices(aggregate=SALES, group_by={"field": "owner"}),
		{},
		ON_INVOICES,
		(0, 12, 4, 5),
	),
	(
		"busy_hours",
		"Busy Hours",
		"Heatmap",
		_invoices(
			aggregate={"function": "count"},
			group_by={"field": "creation", "time_grain": "weekday"},
			group_by2={"field": "creation", "time_grain": "hour"},
		),
		{},
		ON_INVOICES,
		(4, 12, 8, 5),
	),
]

# new translations written for this product, pending review like the rest of
# the Arabic interface
AR = {
	"POS Sales": "مبيعات نقاط البيع",
	DESCRIPTION: "المبيعات ونقاط البيع وطرق الدفع والأصناف وأوقات الذروة من LumenPOS.",
	"Net Sales": "صافي المبيعات",
	"Invoices": "الفواتير",
	"Average Basket": "متوسط قيمة السلة",
	"Returns": "المرتجعات",
	"Sales by Day": "المبيعات حسب اليوم",
	"Sales by Outlet": "المبيعات حسب نقطة البيع",
	"Payment Mix": "توزيع طرق الدفع",
	"Top Items": "أبرز الأصناف",
	"Sales by Cashier": "المبيعات حسب أمين الصندوق",
	"Busy Hours": "أوقات الذروة",
	"Date": "التاريخ",
	"Outlet": "نقطة البيع",
	"Customer": "العميل",
	"Payment method": "طريقة الدفع",
	"Item": "الصنف",
}


# ---------------------------------------------------------------- helpers


def _dashboard_name():
	return frappe.db.get_value("Lumen Dashboard", {"route_slug": SLUG})


def _has_app_role() -> bool:
	user = frappe.session.user
	return user == "Administrator" or bool(APP_ROLES & set(frappe.get_roles(user)))


def _links() -> dict:
	return {
		"contract": CONTRACT_VERSION,
		"slug": SLUG,
		"url": f"/lumen/dashboard/{SLUG}",
		"embed_url": f"/lumen/embed/{SLUG}",
	}


def _ready(created: bool, dropped=None) -> dict:
	return {"status": "ready", "created": created, "dropped": dropped or [], "message": None, **_links()}


def _refusal(status: str, message: str) -> dict:
	return {"status": status, "created": False, "dropped": [], "message": message, **_links()}


def _require_login():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in"), frappe.PermissionError)


def _create(lang):
	tr = (lambda text: AR.get(text, text)) if lang == "ar" else (lambda text: text)

	kept, dropped = starters.validate_widgets(
		{
			"id": "lumenpos",
			"widgets": [{"title": w[1], "widget_type": w[2], "query": w[3], "style": w[4]} for w in WIDGETS],
		}
	)
	kept_titles = {w["title"] for w in kept}
	if not kept_titles:
		return None, dropped

	doc = frappe.new_doc("Lumen Dashboard")
	doc.dashboard_title = tr("POS Sales")
	doc.route_slug = SLUG
	doc.description = tr(DESCRIPTION)
	doc.auto_refresh = 1
	doc.is_published = 1
	# only when LumenPOS has installed its role; otherwise the dashboard is simply
	# published, and managers see everything whatever the audience
	if frappe.db.exists("Role", AUDIENCE_ROLE):
		doc.append("visible_to_roles", {"role": AUDIENCE_ROLE})

	layout = []
	for widget_id, title, widget_type, query, style, linked, (x, y, w, h) in WIDGETS:
		if title not in kept_titles:
			continue
		doc.append(
			"widgets",
			{
				"widget_id": widget_id,
				"title": tr(title),
				"widget_type": widget_type,
				"query_json": json.dumps(query),
				"style_json": json.dumps(style),
				"linked_filters": json.dumps(linked),
			},
		)
		layout.append({"widget_id": widget_id, "x": x, "y": y, "w": w, "h": h})
	doc.layout_json = json.dumps(layout)
	doc.filters_json = json.dumps([{**f, "label": tr(f["label"])} for f in FILTERS])
	doc.insert()  # frappe enforces the create permission again here
	return doc.name, dropped


# ---------------------------------------------------------------- contract


@frappe.whitelist(methods=["GET"])
def get_status():
	"""Which Insights state the POS should show. Changes nothing."""
	_require_login()
	name = _dashboard_name()
	has_source = bool(frappe.db.exists("DocType", SOURCE))
	has_role = _has_app_role()
	can_view = False
	if name and has_role and frappe.has_permission("Lumen Dashboard", "read", doc=name):
		can_view = True
	can_create = False
	if has_source and frappe.has_permission("Lumen Dashboard", "create"):
		can_create = True

	if not has_source:
		reason = "needs_erpnext"
	elif not name:
		reason = "not_set_up"
	elif not has_role:
		reason = "needs_role"
	elif not can_view:
		reason = "not_in_audience"
	else:
		reason = None

	return {
		**_links(),
		"license": licensing.get_status().get("status"),
		"dashboard_exists": bool(name),
		"can_view": can_view,
		"can_create": can_create,
		"reason": reason,
	}


@frappe.whitelist(methods=["POST"])
def ensure_dashboard(lang: str | None = None):
	"""Create the POS sales dashboard if it is missing. Safe to call repeatedly,
	and never changes a dashboard that already exists."""
	_require_login()

	if not frappe.db.exists("DocType", SOURCE):
		return _refusal(
			"needs_erpnext",
			_("Insights reads POS Invoice, which comes with ERPNext. Install ERPNext first."),
		)
	if _dashboard_name():
		return _ready(created=False)

	# the same rule as every other write in the app: only a lapsed subscription
	# blocks, and a developer's own bench never does
	expired = licensing.get_status().get("status") == licensing.STATUS_EXPIRED
	if expired and not frappe.conf.get("developer_mode"):
		return _refusal(
			"license_expired",
			_("The Lumen Reports subscription on this site has lapsed. Renew it to set up Insights."),
		)
	if not frappe.has_permission("Lumen Dashboard", "create"):
		return _refusal(
			"not_permitted",
			_(
				"Setting up Insights needs Lumen Builder, Lumen Manager or System Manager. "
				"Ask an administrator to open Insights once."
			),
		)

	try:
		name, dropped = _create(lang)
	except frappe.DuplicateEntryError:
		# another administrator set it up in the same moment
		frappe.clear_last_message()
		return _ready(created=False)

	if not name:
		return _refusal("not_available", _("None of the Insights charts can read the data on this site."))
	return _ready(created=True, dropped=dropped)
