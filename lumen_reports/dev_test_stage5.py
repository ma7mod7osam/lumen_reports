# Development helper: verify stage 5 backend — caching, invalidation,
# cross-filters, publish-visibility permissions.
# Run with: bench --site <site> execute lumen_reports.dev_test_stage5.run

import frappe

from lumen_reports import api

TEST_USER = "viewer@lumen.test"


def run():
	out = {}

	# --- caching ---
	frappe.cache.delete_keys("lumen_res|ToDo|")
	first = api.run_widget("demo", "by_status")
	second = api.run_widget("demo", "by_status")
	out["first_from_cache"] = bool(first.get("from_cache"))
	out["second_from_cache"] = bool(second.get("from_cache"))

	# --- invalidation via doc change ---
	todo = frappe.get_doc({"doctype": "ToDo", "description": "cache invalidation probe"}).insert(
		ignore_permissions=True
	)
	third = api.run_widget("demo", "by_status")
	out["after_change_from_cache"] = bool(third.get("from_cache"))
	todo.delete(ignore_permissions=True)

	# --- cross filters ---
	crossed = api.run_widget(
		"demo", "by_status", cross_filters=[{"fieldname": "priority", "value": "High"}]
	)
	out["cross_filtered_values"] = crossed["values"]
	ignored = api.run_widget(
		"demo", "by_status", cross_filters=[{"fieldname": "no_such_field", "value": "x"}]
	)
	out["unknown_field_ignored"] = ignored["values"] == api.run_widget("demo", "by_status")["values"]

	# --- publish visibility ---
	if not frappe.db.exists("User", TEST_USER):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": TEST_USER,
				"first_name": "Viewer",
				"send_welcome_email": 0,
				"roles": [{"role": "Desk User"}],
			}
		).insert(ignore_permissions=True)
	frappe.db.set_value("Lumen Dashboard", {"route_slug": "team-tasks"}, "is_published", 0)
	frappe.db.commit()
	frappe.clear_cache()

	frappe.set_user(TEST_USER)
	try:
		visible = [d.route_slug for d in api.get_dashboards()["dashboards"]]
		out["viewer_sees"] = visible
		out["unpublished_hidden"] = "team-tasks" not in visible and "demo" in visible
		try:
			api.get_dashboard("team-tasks")
			out["direct_access_blocked"] = False
		except frappe.PermissionError:
			out["direct_access_blocked"] = True
		out["viewer_can_edit_demo"] = api.get_dashboard("demo")["can_edit"]
	finally:
		frappe.set_user("Administrator")

	frappe.db.commit()
	return out
