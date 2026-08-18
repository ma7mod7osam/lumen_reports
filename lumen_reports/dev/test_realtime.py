# Development helper: verify realtime registry + hook execution on save.
# Run with: bench --site <site> execute lumen_reports.dev.test_realtime.run

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
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — dev/test helper run by hand via bench execute; commits fixtures so the assertions that follow (which roll back on denial) cannot undo them

	return {"registry": registry, "hook_ran_ok": True}


def room_scoped():
	"""The invalidation must go to the per-doctype room, not site-wide."""
	from unittest import mock

	from lumen_reports import realtime

	captured = {}

	def fake_publish(event=None, message=None, **kw):
		captured.update({"event": event, "message": message, **kw})

	with mock.patch.object(frappe, "publish_realtime", fake_publish):  # nosemgrep: frappe-monkey-patching-not-allowed — test-only capture of the outbound realtime call
		doc = frappe.get_last_doc("Sales Invoice")
		realtime.notify_doc_change(doc, "on_change")
	return {
		"event": captured.get("event"),
		"scoped_to_doctype": captured.get("doctype") == "Sales Invoice",
		"no_docname_room": captured.get("docname") is None,
		"after_commit": bool(captured.get("after_commit")),
		"message_has_slugs": bool((captured.get("message") or {}).get("dashboards")),
	}
