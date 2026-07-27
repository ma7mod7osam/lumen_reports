# Role/permission tests with real users.
# bench --site <site> execute lumen_reports.dev.dev_test_perms.run

import json
import traceback

import frappe

from lumen_reports import api

VIEWER = "lumen.viewer@test.local"
BUILDER = "lumen.builder@test.local"
BUILDER2 = "lumen.builder2@test.local"

SLUG_DRAFT = "perm-test-draft"
SLUG_SALES_ONLY = "perm-test-sales-only"
SLUG_BUILDER_OWN = "perm-test-builder-own"


def _user(email, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	doc = frappe.get_doc("User", email)
	doc.set("roles", [])
	for role in roles:
		doc.append("roles", {"role": role})
	doc.save(ignore_permissions=True)
	return email


def _dashboard(slug, title, published, roles=None, owner="Administrator"):
	if frappe.db.exists("Lumen Dashboard", slug):
		frappe.delete_doc("Lumen Dashboard", slug, force=True, ignore_permissions=True)
	doc = frappe.new_doc("Lumen Dashboard")
	doc.route_slug = slug
	doc.dashboard_title = title
	doc.is_published = 1 if published else 0
	for role in roles or []:
		doc.append("visible_to_roles", {"role": role})
	doc.append(
		"widgets",
		{
			"widget_id": "w0",
			"title": "Invoice count",
			"widget_type": "Number Card",
			"query_json": json.dumps({"doctype": "Sales Invoice", "aggregate": {"function": "count"}}),
			"style_json": "{}",
		},
	)
	doc.insert(ignore_permissions=True)
	if owner != "Administrator":
		frappe.db.set_value("Lumen Dashboard", doc.name, "owner", owner)
	return doc.name


def _visible_slugs():
	return {d.route_slug for d in api.get_dashboards()["dashboards"]}


def _try(fn, *args, **kwargs):
	"""Run an API call and report 'allowed' or the exception class."""
	try:
		fn(*args, **kwargs)
		return "allowed"
	except Exception as e:
		frappe.db.rollback()
		return type(e).__name__


def run():
	frappe.set_user("Administrator")
	out = {}
	try:
		from lumen_reports.setup import ensure_roles

		ensure_roles()
		_user(VIEWER, ["Lumen Viewer"])
		_user(BUILDER, ["Lumen Builder", "Sales User", "Accounts User"])
		_user(BUILDER2, ["Lumen Builder"])

		_dashboard(SLUG_DRAFT, "Draft (admin's)", published=False)
		_dashboard(SLUG_SALES_ONLY, "Sales eyes only", published=True, roles=["Sales User"])
		public = _dashboard("perm-test-public", "Public", published=True)
		# the deny-path rollbacks below must not be able to undo the fixtures
		frappe.db.commit()

		# ---- viewer: sees public, not drafts, not the Sales-only board
		frappe.set_user(VIEWER)
		seen = _visible_slugs()
		out["viewer_sees_public"] = "perm-test-public" in seen
		out["viewer_blocked_from_draft"] = SLUG_DRAFT not in seen
		out["viewer_blocked_from_sales_only"] = SLUG_SALES_ONLY not in seen
		out["viewer_can_create"] = api.get_dashboards()["can_create"]  # expect False
		out["viewer_save_attempt"] = _try(
			api.save_dashboard,
			json.dumps({"title": "Viewer sneaky", "slug": "viewer-sneaky", "widgets": []}),
		)
		# widget data still runs through DOCTYPE perms: viewer has no Sales role
		out["viewer_widget_data"] = _try(
			api.run_widget, "perm-test-public", "w0"
		)  # expect PermissionError — no read on Sales Invoice

		# ---- builder: creates own, edits own, can't touch admin's
		frappe.set_user(BUILDER)
		out["builder_can_create"] = api.get_dashboards()["can_create"]  # expect True
		out["builder_sees_sales_only"] = SLUG_SALES_ONLY in _visible_slugs()  # has Sales User
		created = api.save_dashboard(
			json.dumps(
				{
					"title": "Builder Own",
					"slug": SLUG_BUILDER_OWN,
					"is_published": False,
					"widgets": [
						{
							"widget_id": "w0",
							"title": "My invoices",
							"widget_type": "Number Card",
							"query": {"doctype": "Sales Invoice", "aggregate": {"function": "count"}},
						}
					],
					"layout": [{"widget_id": "w0", "x": 0, "y": 0, "w": 3, "h": 2}],
				}
			)
		)
		out["builder_created_own"] = bool(created.get("name"))
		frappe.db.commit()  # protect from the deny-path rollbacks that follow
		out["builder_edit_own"] = _try(
			api.save_dashboard,
			json.dumps({"name": created["name"], "title": "Builder Own v2", "widgets": [], "layout": []}),
		)
		out["builder_edit_admins"] = _try(
			api.save_dashboard,
			json.dumps({"name": "perm-test-public", "title": "Hijacked", "widgets": [], "layout": []}),
		)
		out["builder_delete_admins"] = _try(api.delete_dashboard, "perm-test-public")
		# builder only reports on what THEIR roles can read
		out["builder_query_hr_doctype"] = _try(
			api.preview_query, {"doctype": "Leave Application", "aggregate": {"function": "count"}}
		)

		# ---- second builder can't see or edit the first builder's draft
		frappe.set_user(BUILDER2)
		out["builder2_blocked_from_builders_draft"] = SLUG_BUILDER_OWN not in _visible_slugs()
		out["builder2_edit_builders"] = _try(
			api.save_dashboard,
			json.dumps({"name": SLUG_BUILDER_OWN, "title": "Steal", "widgets": [], "layout": []}),
		)
	except Exception:
		out["traceback"] = traceback.format_exc()[-1200:]
	finally:
		frappe.set_user("Administrator")
		for slug in (SLUG_DRAFT, SLUG_SALES_ONLY, "perm-test-public", SLUG_BUILDER_OWN):
			if frappe.db.exists("Lumen Dashboard", slug):
				frappe.delete_doc("Lumen Dashboard", slug, force=True, ignore_permissions=True)
		frappe.db.commit()
	return out
