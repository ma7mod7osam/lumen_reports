# Copyright (c) 2026, Lumen Solutions
# Proprietary — see license.txt

"""Visibility rules for Lumen Dashboard, layered on top of role permissions.

Role permissions (in the doctype) decide what a user may DO:
- Lumen Viewer   reads
- Lumen Builder  reads, creates, writes/deletes own (if_owner)
- Lumen Manager / System Manager  everything

These hooks decide what a user may SEE:
- Managers see everything.
- Everyone else sees their own dashboards, plus published ones — and when a
  published dashboard names an audience (visible_to_roles), only members of
  those roles see it.

Data inside widgets is a separate, third layer: every query runs through the
permission-checked engines, so two users can open the same dashboard and
correctly see different numbers.
"""

import frappe

MANAGER_ROLES = {"System Manager", "Lumen Manager"}


def _is_manager(user) -> bool:
	return user == "Administrator" or bool(MANAGER_ROLES & set(frappe.get_roles(user)))


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if _is_manager(user):
		return None
	roles = ", ".join(frappe.db.escape(r) for r in frappe.get_roles(user))
	own = f"`tabLumen Dashboard`.`owner` = {frappe.db.escape(user)}"
	published = (
		"(`tabLumen Dashboard`.`is_published` = 1 and ("
		# no audience set -> visible to everyone with Lumen access
		"not exists (select 1 from `tabLumen Dashboard Role` ldr "
		"where ldr.parent = `tabLumen Dashboard`.`name`) "
		# audience set -> user must hold one of the named roles
		"or exists (select 1 from `tabLumen Dashboard Role` ldr "
		f"where ldr.parent = `tabLumen Dashboard`.`name` and ldr.role in ({roles}))))"
	)
	return f"({own} or {published})"


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if _is_manager(user):
		return True
	if doc.owner == user:
		return True
	if ptype != "read":
		# non-owners never write; role perms would block this anyway (if_owner)
		return False
	if not doc.is_published:
		return False
	audience = [row.role for row in (doc.visible_to_roles or [])]
	return not audience or bool(set(audience) & set(frappe.get_roles(user)))
