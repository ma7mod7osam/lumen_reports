# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
"""Does a row restriction reach BOTH engines?

query_engine runs through frappe.get_list, which applies User Permissions and
permission query conditions. report_engine builds its own query with frappe.qb
and checks only `frappe.has_permission(doctype, "read")`. If a User Permission
narrows someone to one customer, a line-item widget must narrow with it, or the
listing's claim that nobody sees more than their role allows is not true.

bench --site <site> execute lumen_reports.dev.test_rowperms.run
bench --site <site> execute lumen_reports.dev.test_rowperms.cleanup
"""

import json

import frappe

from lumen_reports import query_engine, report_engine
from lumen_reports.dev.test_perms import _user

VIEWER = "rowperm.viewer@test.local"
PARENT = "Sales Invoice"
CHILD = "Sales Invoice Item"


def _pick_customer():
	rows = frappe.db.sql(
		"""select customer, count(name) as n from `tabSales Invoice`
		   where docstatus = 1 group by customer order by n desc limit 1""",
		as_dict=True,
	)
	return rows[0].customer if rows else None


def run():
	out = {}
	customer = _pick_customer()
	if not customer:
		print(json.dumps({"skipped": "no submitted Sales Invoices on this bench"}))
		return
	out["customer"] = customer

	_user(VIEWER, ["Lumen Viewer"])
	# the viewer must be able to read invoices at all, or both engines refuse
	for role in ("Accounts User",):
		if frappe.db.exists("Role", role):
			user = frappe.get_doc("User", VIEWER)
			user.add_roles(role)

	# restrict them to ONE customer
	frappe.db.delete("User Permission", {"user": VIEWER})
	frappe.get_doc(
		{"doctype": "User Permission", "user": VIEWER, "allow": "Customer", "for_value": customer}
	).insert(ignore_permissions=True)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- fixtures must survive the reads below

	totals = {}
	totals["all_invoices"] = frappe.db.count(PARENT, {"docstatus": 1})
	totals["their_invoices"] = frappe.db.count(PARENT, {"docstatus": 1, "customer": customer})
	out["totals"] = totals
	if totals["their_invoices"] >= totals["all_invoices"]:
		out["note"] = "only one customer has invoices, the test cannot tell the engines apart"

	frappe.set_user(VIEWER)
	try:
		# document grain, through get_list
		doc_level = query_engine.execute(
			{"doctype": PARENT, "aggregate": {"function": "count"}, "filters": [["docstatus", "=", 1]]}
		)["value"]
		# line grain, through report_engine
		line_level = report_engine.execute(
			{
				"doctype": CHILD,
				"parent_doctype": PARENT,
				"aggregate": {"function": "count"},
				"filters": [["docstatus", "=", 1]],
			}
		)["value"]
		# the same line grain reached through the public entry point
		via_engine = query_engine.execute(
			{
				"doctype": CHILD,
				"parent_doctype": PARENT,
				"aggregate": {"function": "count"},
				"filters": [["docstatus", "=", 1]],
			}
		)["value"]
	finally:
		frappe.set_user("Administrator")

	out["doc_grain_seen"] = doc_level
	out["line_grain_seen"] = line_level
	out["line_grain_via_query_engine"] = via_engine

	all_lines = frappe.db.sql(
		"""select count(c.name) as n from `tabSales Invoice Item` c
		   join `tabSales Invoice` p on p.name = c.parent where p.docstatus = 1""",
	)[0][0]
	their_lines = frappe.db.sql(
		"""select count(c.name) as n from `tabSales Invoice Item` c
		   join `tabSales Invoice` p on p.name = c.parent
		   where p.docstatus = 1 and p.customer = %(c)s""",
		{"c": customer},
	)[0][0]
	out["all_lines"] = all_lines
	out["their_lines"] = their_lines

	out["doc_grain_restricted"] = doc_level == totals["their_invoices"]
	out["line_grain_restricted"] = line_level == their_lines
	out["line_grain_via_engine_restricted"] = via_engine == their_lines
	out["no_leak"] = not (line_level == all_lines and all_lines != their_lines)
	# the check can only prove anything when more than one customer has invoices
	out["meaningful"] = their_lines < all_lines and totals["their_invoices"] < totals["all_invoices"]

	out["all_ok"] = all(v for v in out.values() if isinstance(v, bool))
	print(json.dumps(out, indent=1, default=str))


def cleanup():
	frappe.set_user("Administrator")
	frappe.db.delete("User Permission", {"user": VIEWER})
	if frappe.db.exists("User", VIEWER):
		frappe.delete_doc("User", VIEWER, force=True, ignore_permissions=True)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- dev cleanup run from bench execute
	print("cleaned")
