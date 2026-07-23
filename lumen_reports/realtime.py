# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

"""Realtime invalidation: when a document changes, tell open dashboards
that depend on its doctype to refresh their widgets.

A registry mapping doctype -> [dashboard slugs] is cached in redis and
rebuilt lazily whenever a Lumen Dashboard is saved or deleted."""

import frappe

REGISTRY_CACHE_KEY = "lumen_reports:doctype_registry"
EVENT_NAME = "lumen_reports:invalidate"

IGNORED_DOCTYPES = {
	"Version",
	"Comment",
	"Activity Log",
	"Access Log",
	"Error Log",
	"Scheduled Job Log",
	"Route History",
	"View Log",
	"Notification Log",
	"Email Queue",
	"DocField",
	"DocPerm",
}


def get_registry() -> dict:
	registry = frappe.cache.get_value(REGISTRY_CACHE_KEY)
	if registry is None:
		registry = _build_registry()
		frappe.cache.set_value(REGISTRY_CACHE_KEY, registry)
	return registry


def _build_registry() -> dict:
	registry = {}
	dashboards = frappe.get_all(
		"Lumen Dashboard", filters={"auto_refresh": 1}, fields=["name", "route_slug"]
	)
	for dashboard in dashboards:
		widgets = frappe.get_all(
			"Lumen Widget",
			filters={"parent": dashboard.name, "parenttype": "Lumen Dashboard"},
			fields=["query_json"],
		)
		for widget in widgets:
			query = frappe.parse_json(widget.query_json or "{}")
			doctype = query.get("doctype")
			if doctype:
				registry.setdefault(doctype, [])
				if dashboard.route_slug not in registry[doctype]:
					registry[doctype].append(dashboard.route_slug)
	return registry


def notify_doc_change(doc, method=None):
	"""doc_events hook on every doctype (on_change / after_delete)."""
	if doc.doctype in IGNORED_DOCTYPES or doc.doctype.startswith("Lumen "):
		return
	if frappe.flags.in_migrate or frappe.flags.in_install or frappe.flags.in_patch:
		return

	registry = get_registry()
	slugs = registry.get(doc.doctype)
	if not slugs:
		return

	# drop cached widget results for this doctype — same invalidation path
	# as the realtime refresh, so cache and liveness can't disagree
	frappe.cache.delete_keys(f"lumen_res|{doc.doctype}|")

	frappe.publish_realtime(
		EVENT_NAME,
		message={"doctype": doc.doctype, "dashboards": slugs},
		after_commit=True,
	)
