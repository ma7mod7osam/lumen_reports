# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

"""Visibility rules for Lumen Dashboard, layered on top of role permissions:

- System Managers see everything.
- Everyone else sees published dashboards, plus their own drafts.
- Writing always requires the doctype's role permissions (System Manager),
  or ownership of the document.
"""

import frappe


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return None
	return (
		f"(`tabLumen Dashboard`.`is_published` = 1 "
		f"or `tabLumen Dashboard`.`owner` = {frappe.db.escape(user)})"
	)


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True
	if ptype == "read":
		return bool(doc.is_published) or doc.owner == user
	return doc.owner == user
