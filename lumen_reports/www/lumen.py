import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(frappe._("Please login to access Lumen Reports"), frappe.PermissionError)
	context.boot = {
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
		"socketio_port": frappe.conf.socketio_port or 9000,
	}
	frappe.db.commit()
