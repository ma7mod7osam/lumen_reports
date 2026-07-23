# Development helper: verify realtime registry + hook execution on save.
# Run with: bench --site <site> execute lumen_reports.dev_test_realtime.run

import frappe

from lumen_reports import realtime


def run():
	frappe.cache.delete_value(realtime.REGISTRY_CACHE_KEY)
	registry = realtime.get_registry()

	# saving a ToDo must run the on_change hook without raising
	todo = frappe.get_doc(
		{"doctype": "ToDo", "description": "realtime hook check", "status": "Open"}
	).insert(ignore_permissions=True)
	todo.delete(ignore_permissions=True)
	frappe.db.commit()

	return {"registry": registry, "hook_ran_ok": True}
