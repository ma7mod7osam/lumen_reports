# Copyright (c) 2026, Lumen Solutions
# Proprietary — see license.txt

"""Visibility rules for Lumen Dashboard, layered on top of role permissions.

Role permissions (in the doctype) decide what a user may DO:
- Lumen Viewer            reads
- Lumen Restricted Viewer reads
- Lumen Builder           reads, creates, writes/deletes own (if_owner)
- Lumen Manager / System Manager  everything

These hooks decide what a user may SEE:
- Managers see everything.
- Full-access users (Viewer/Builder) see their own dashboards plus published
  ones — restricted to the audience when a dashboard names one (roles and/or
  specific users).
- RESTRICTED viewers get no "published = everyone" default at all: they see
  only dashboards that name them, personally or through an audience role.
  That is how you give somebody exactly one dashboard.

Data inside widgets is a separate, third layer: every query runs through the
permission-checked engines, so two users can open the same dashboard and
correctly see different numbers.
"""

import frappe

MANAGER_ROLES = {"System Manager", "Lumen Manager"}
FULL_ACCESS_ROLES = {"Lumen Viewer", "Lumen Builder"}


def _is_manager(user) -> bool:
	return user == "Administrator" or bool(MANAGER_ROLES & set(frappe.get_roles(user)))


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if _is_manager(user):
		return None

	roles = set(frappe.get_roles(user))
	role_list = ", ".join(frappe.db.escape(r) for r in roles)
	escaped_user = frappe.db.escape(user)

	own = f"`tabLumen Dashboard`.`owner` = {escaped_user}"
	role_match = (
		"exists (select 1 from `tabLumen Dashboard Role` ldr "
		f"where ldr.parent = `tabLumen Dashboard`.`name` and ldr.role in ({role_list}))"
	)
	user_match = (
		"exists (select 1 from `tabLumen Dashboard User` ldu "
		f"where ldu.parent = `tabLumen Dashboard`.`name` and ldu.user = {escaped_user})"
	)

	if FULL_ACCESS_ROLES & roles:
		# published with no audience at all -> everyone with Lumen access
		no_audience = (
			"not exists (select 1 from `tabLumen Dashboard Role` ldr "
			"where ldr.parent = `tabLumen Dashboard`.`name`) "
			"and not exists (select 1 from `tabLumen Dashboard User` ldu "
			"where ldu.parent = `tabLumen Dashboard`.`name`)"
		)
		published = (
			f"(`tabLumen Dashboard`.`is_published` = 1 "
			f"and (({no_audience}) or {role_match} or {user_match}))"
		)
	else:
		# restricted viewer: only what names them — no default visibility
		published = (
			f"(`tabLumen Dashboard`.`is_published` = 1 and ({role_match} or {user_match}))"
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

	roles = set(frappe.get_roles(user))
	audience_roles = {row.role for row in (doc.visible_to_roles or [])}
	audience_users = {row.user for row in (doc.visible_to_users or [])}
	named = bool(audience_roles & roles) or user in audience_users

	if FULL_ACCESS_ROLES & roles:
		return named or not (audience_roles or audience_users)
	# restricted viewer: being named is the only way in
	return named
