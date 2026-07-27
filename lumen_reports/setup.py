# Copyright (c) 2026, Lumen Solutions
# Proprietary — see license.txt

"""Install/migrate hooks: the app's roles.

Three roles, mirroring how dashboard tools are actually used:

- Lumen Viewer   — opens the app, sees published dashboards (subject to each
                   dashboard's audience). Data inside widgets still follows the
                   viewer's own doctype permissions.
- Lumen Builder  — Viewer + creates dashboards and edits/deletes their OWN.
                   Can only report on doctypes their roles let them read — the
                   query engines enforce that on every single request.
- Lumen Manager  — full control of all dashboards without needing the very
                   broad System Manager role.

Created here (idempotently) rather than shipped as fixtures so a bare
`bench install-app` and every migrate self-heal missing roles.
"""

import frappe

LUMEN_ROLES = ("Lumen Viewer", "Lumen Builder", "Lumen Manager")


def ensure_roles():
	for name in LUMEN_ROLES:
		if not frappe.db.exists("Role", name):
			frappe.get_doc(
				{"doctype": "Role", "role_name": name, "desk_access": 0}
			).insert(ignore_permissions=True)
	frappe.db.commit()


def after_install():
	ensure_roles()


def after_migrate():
	ensure_roles()
