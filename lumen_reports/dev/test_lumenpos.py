# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
"""LumenPOS Insights contract checks, with real users.

bench --site <site> execute lumen_reports.dev.test_lumenpos.run
bench --site <site> execute lumen_reports.dev.test_lumenpos.cleanup
"""

import json

import frappe

from lumen_reports import api, licensing, query_engine
from lumen_reports.dev.test_perms import _user
from lumen_reports.integrations import lumenpos

VIEWER = "lumenpos.viewer@test.local"  # Lumen Viewer, no POS role
POS_MANAGER = "lumenpos.manager@test.local"  # Lumen Restricted Viewer + LumenPOS Manager
OTHER_RESTRICTED = "lumenpos.other@test.local"  # Lumen Restricted Viewer only
POS_ONLY = "lumenpos.nolumen@test.local"  # LumenPOS Manager only

ROLE_FLAG = "lumenpos_test_created_role"


def _as(user, fn, *args, **kwargs):
	frappe.set_user(user)
	try:
		return fn(*args, **kwargs)
	finally:
		frappe.set_user("Administrator")


def _drop_dashboard():
	if lumenpos._dashboard_name():
		frappe.delete_doc("Lumen Dashboard", lumenpos.SLUG, force=True, ignore_permissions=True)


def run():
	out = {}
	role = lumenpos.AUDIENCE_ROLE
	if not frappe.db.exists("Role", role):
		frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
		frappe.cache.set_value(ROLE_FLAG, 1)

	_user(VIEWER, ["Lumen Viewer"])
	_user(POS_MANAGER, ["Lumen Restricted Viewer", role])
	_user(OTHER_RESTRICTED, ["Lumen Restricted Viewer"])
	_user(POS_ONLY, [role])
	_drop_dashboard()

	before = lumenpos.get_status()
	out["status_before_setup"] = before["reason"] == "not_set_up" and before["can_create"] is True

	# a lapsed subscription blocks setup outside developer mode
	real_status, dev_mode = licensing.get_status, frappe.conf.get("developer_mode")
	licensing.get_status = lambda force=False: {"status": licensing.STATUS_EXPIRED}
	frappe.conf.developer_mode = 0
	try:
		out["expired_refused"] = lumenpos.ensure_dashboard()["status"] == "license_expired"
	finally:
		licensing.get_status = real_status
		frappe.conf.developer_mode = dev_mode
	out["nothing_created_when_refused"] = not lumenpos._dashboard_name()

	out["viewer_cannot_set_up"] = _as(VIEWER, lumenpos.ensure_dashboard)["status"] == "not_permitted"

	first = lumenpos.ensure_dashboard()
	out["created"] = first["status"] == "ready" and first["created"] is True
	out["dropped"] = first["dropped"]
	second = lumenpos.ensure_dashboard()
	out["idempotent"] = second["status"] == "ready" and second["created"] is False

	doc = frappe.get_doc("Lumen Dashboard", lumenpos.SLUG)
	out["published_for_pos_role_only"] = bool(doc.is_published) and [r.role for r in doc.visible_to_roles] == [role]
	out["widget_count"] = len(doc.widgets)
	out["filters"] = [f["name"] for f in json.loads(doc.filters_json)]

	# edits a person makes are kept: ensure never rewrites
	doc.dashboard_title = "POS Sales (edited)"
	doc.save(ignore_permissions=True)
	lumenpos.ensure_dashboard()
	out["edits_survive_ensure"] = frappe.db.get_value("Lumen Dashboard", lumenpos.SLUG, "dashboard_title") == "POS Sales (edited)"

	manager = _as(POS_MANAGER, lumenpos.get_status)
	out["pos_manager_can_view"] = manager["can_view"] is True and manager["reason"] is None
	other = _as(OTHER_RESTRICTED, lumenpos.get_status)
	out["other_restricted_blocked"] = other["can_view"] is False and other["reason"] == "not_in_audience"
	pos_only = _as(POS_ONLY, lumenpos.get_status)
	out["no_lumen_role_asked_for_one"] = pos_only["can_view"] is False and pos_only["reason"] == "needs_role"
	# seeing the dashboard is not reading the data. On this bench the POS role has
	# no read on POS Invoice, so the numbers must still be refused
	try:
		_as(POS_MANAGER, api.run_widget, lumenpos.SLUG, "net_sales")
		out["data_layer_still_applies"] = False
	except frappe.PermissionError:
		frappe.clear_last_message()
		out["data_layer_still_applies"] = True
	out["admin_reads_widget"] = api.run_widget(lumenpos.SLUG, "net_sales") is not None

	# every widget runs with each filter it is linked to
	values = {
		"posting_date": ["2026-01-01", "2026-12-31"],
		"pos_profile": "__lumen_test__",
		"customer": "__lumen_test__",
		f"{lumenpos.PAYMENTS}::mode_of_payment": "Cash",
		f"{lumenpos.LINES}::item_code": "__lumen_test__",
	}
	errors = {}
	runs = 0
	for w in doc.widgets:
		for name in json.loads(w.linked_filters):
			runs += 1
			try:
				api.run_widget(lumenpos.SLUG, w.widget_id, filter_values=json.dumps({name: values[name]}))
			except Exception as e:
				errors[f"{w.widget_id} + {name}"] = str(e)[:200]
				frappe.clear_last_message()
	out["widget_filter_runs"] = runs
	out["widget_filter_errors"] = errors

	# the date range really narrows, checked on the Sales Invoice demo data
	class _Dash:
		filters_json = json.dumps(
			[{"name": "d", "fieldtype": "Date Range", "source": "parent", "fieldname": "posting_date"}]
		)

	class _Widget:
		linked_filters = json.dumps({"d": "posting_date"})
		query_json = json.dumps({"doctype": "Sales Invoice"})

	built = api._build_filters_from_values(_Dash, _Widget, {"d": ["2000-01-01", "2000-01-02"]})
	count = {"doctype": "Sales Invoice", "aggregate": {"function": "count"}}
	everything = query_engine.execute(count).get("value") or 0
	narrowed = query_engine.execute({**count, "filters": built}).get("value") or 0
	out["range_filter_built"] = built == [["posting_date", "between", ["2000-01-01", "2000-01-02"]]]
	out["range_filter_narrows"] = everything > 0 and narrowed == 0

	# the PDF header names a date range in words, in both languages
	from lumen_reports import report

	picked = {"posting_date": ["2026-09-01", "2026-09-14"], "customer": "Walk-in"}
	out["pdf_filters_line_en"] = report._filters_line(doc, picked, "en") == "Date: 2026-09-01 to 2026-09-14 · Customer: Walk-in"
	out["pdf_filters_line_ar"] = "من 2026-09-01 إلى 2026-09-14" in report._filters_line(doc, picked, "ar")

	checks = [v for k, v in out.items() if isinstance(v, bool)]
	out["all_ok"] = all(checks) and not errors
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- dev check run from bench execute, keeps the dashboard for a browser look
	print(json.dumps(out, indent=1, default=str))


def cleanup():
	_drop_dashboard()
	for email in (VIEWER, POS_MANAGER, OTHER_RESTRICTED, POS_ONLY):
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
	if frappe.cache.get_value(ROLE_FLAG) and frappe.db.exists("Role", lumenpos.AUDIENCE_ROLE):
		frappe.delete_doc("Role", lumenpos.AUDIENCE_ROLE, force=True, ignore_permissions=True)
		frappe.cache.delete_value(ROLE_FLAG)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- dev cleanup run from bench execute
	print("cleaned")
