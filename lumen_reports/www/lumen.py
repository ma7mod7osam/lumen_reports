import frappe

no_cache = 1

# roles that open the app at all — the first, coarsest permission layer
APP_ROLES = {"System Manager", "Lumen Manager", "Lumen Builder", "Lumen Viewer"}


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(frappe._("Please login to access Lumen Reports"), frappe.PermissionError)
	if frappe.session.user != "Administrator" and not (APP_ROLES & set(frappe.get_roles())):
		frappe.throw(
			frappe._(
				"You don't have access to Lumen Reports yet. Ask your administrator for "
				"one of these roles: Lumen Viewer, Lumen Builder or Lumen Manager."
			),
			frappe.PermissionError,
		)
	context.boot = {
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
		"socketio_port": frappe.conf.socketio_port or 9000,
	}
	frappe.db.commit()
