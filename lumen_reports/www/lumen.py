# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
import frappe

from lumen_reports import report

no_cache = 1

# roles that open the app at all — the first, coarsest permission layer
APP_ROLES = {
	"System Manager",
	"Lumen Manager",
	"Lumen Builder",
	"Lumen Viewer",
	"Lumen Restricted Viewer",
}


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
		# v15+ serves a socket.io namespace per site; v14 serves only the default
		# namespace and carries the site in the room names, so the client must not
		# append the site namespace there (it is refused as "Invalid namespace")
		"socketio_site_namespace": _frappe_major() >= 15,
		# the app opens in the person's Frappe language until they pick one.
		# frappe.lang is a request-local proxy; tojson needs the plain string
		"lumen_lang": str(frappe.local.lang or "en"),
		# PDF reports and schedules need WeasyPrint, absent on v14; the SPA hides
		# their entry points when this is false
		"reports_enabled": report.reports_supported(),
	}


def _frappe_major() -> int:
	try:
		return int(str(frappe.__version__).split(".")[0])
	except (ValueError, IndexError):
		return 15  # unknown: assume the modern per-site namespace
