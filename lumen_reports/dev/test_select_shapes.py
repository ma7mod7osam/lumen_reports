# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
"""Every SELECT shape the query engine builds, on whichever Frappe is running.

Frappe v16 rebuilt get_list on the query builder and refuses a SQL function
written as a string in `fields`; v14 and v15 accept only that string form. This
runs the same assertions on either, so the two paths cannot drift apart, and it
asserts the permission filtering survives the path that does not go through a
get_list field list.

bench --site <site> execute lumen_reports.dev.test_select_shapes.run
bench --site <site> execute lumen_reports.dev.test_select_shapes.cleanup
"""

import json

import frappe

from lumen_reports import query_engine

OWNER = "shapes.owner@test.local"  # sees only the ToDos allocated to them
MARK = "__lumen_shapes__"
# a role of our own rather than a stock one: Blogger is not on every site,
# and its absence failed this check on the v16 bench long after it was written
OWN_ROLE = "Lumen Shapes Probe"

# two months, so a month grain has something to split; idx carries the numbers
SEEDS = [
	("2026-01-05", "Low", 1),
	("2026-01-19", "High", 2),
	("2026-01-27", "High", 3),
	("2026-02-04", "Low", 4),
	("2026-02-11", "Medium", 5),
	("2026-02-22", "High", 6),
]


def _seed():
	_drop()
	if not frappe.db.exists("Role", OWN_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": OWN_ROLE, "desk_access": 0}).insert(
			ignore_permissions=True
		)
	if not frappe.db.exists("User", OWNER):
		user = frappe.get_doc(
			{"doctype": "User", "email": OWNER, "first_name": "Shapes", "send_welcome_email": 0}
		)
		user.insert(ignore_permissions=True)
		user.add_roles(OWN_ROLE)

	for i, (date, priority, idx) in enumerate(SEEDS):
		doc = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": f"{MARK} {i}",
				"date": date,
				"priority": priority,
				# the last two belong to the limited user, so the permission
				# assertion has a number it can tell apart from the total
				"allocated_to": OWNER if i >= 4 else None,
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("ToDo", doc.name, "idx", idx, update_modified=False)
	frappe.db.commit()


def _drop():
	for name in frappe.get_all("ToDo", filters={"description": ["like", f"%{MARK}%"]}, pluck="name"):
		frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)


def _mine():
	return [["description", "like", f"%{MARK}%"]]


def run():
	# a label, not a check: it says which of the two shapes this Frappe took
	out = {
		"frappe": frappe.__version__,
		"select_shape": "dict" if query_engine._dict_selects() else "string",
	}
	_seed()

	def q(**kw):
		return query_engine.execute({"doctype": "ToDo", "filters": _mine(), **kw})

	# ---- a plain number, no grouping
	out["count"] = q(aggregate={"function": "count"})["value"] == 6
	out["sum"] = q(aggregate={"function": "sum", "field": "idx"})["value"] == 21
	out["avg"] = abs(float(q(aggregate={"function": "avg", "field": "idx"})["value"]) - 3.5) < 0.001
	out["min"] = q(aggregate={"function": "min", "field": "idx"})["value"] == 1
	out["max"] = q(aggregate={"function": "max", "field": "idx"})["value"] == 6

	# ---- grouped by a plain column, biggest first
	grouped = q(aggregate={"function": "count"}, group_by={"field": "priority"})
	out["group_labels"] = grouped["labels"][0] == "High"
	out["group_values"] = grouped["values"][0] == 3
	out["group_sorted_desc"] = grouped["values"] == sorted(grouped["values"], reverse=True)
	out["group_total"] = sum(grouped["values"]) == 6

	# ---- grouped by a formatted date: the shape v16 cannot express as a field
	months = q(aggregate={"function": "count"}, group_by={"field": "date", "time_grain": "month"})
	out["month_labels"] = months["labels"] == ["2026-01", "2026-02"]
	out["month_values"] = months["values"] == [3, 3]

	sums = q(aggregate={"function": "sum", "field": "idx"}, group_by={"field": "date", "time_grain": "month"})
	out["month_sums"] = [int(v) for v in sums["values"]] == [6, 15]

	days = q(aggregate={"function": "count"}, group_by={"field": "date", "time_grain": "day"})
	out["day_grain"] = len(days["labels"]) == 6 and days["labels"][0] == "2026-01-05"

	years = q(aggregate={"function": "count"}, group_by={"field": "date", "time_grain": "year"})
	out["year_grain"] = years["labels"] == ["2026"] and years["values"] == [6]

	# ---- table rows carry a total, which is its own count query
	rows = q(fields=["name", "priority"], limit=3)
	out["rows_returned"] = len(rows["rows"]) == 3
	out["rows_total"] = rows["total"] == 6

	# ---- the permission filtering has to survive every path above
	frappe.set_user(OWNER)
	try:
		out["perm_count"] = q(aggregate={"function": "count"})["value"] == 2
		mine = q(aggregate={"function": "count"}, group_by={"field": "date", "time_grain": "month"})
		out["perm_time_grain"] = mine["labels"] == ["2026-02"] and mine["values"] == [2]
		out["perm_group"] = sum(q(aggregate={"function": "count"}, group_by={"field": "priority"})["values"]) == 2
		out["perm_rows_total"] = q(fields=["name"], limit=10)["total"] == 2
	finally:
		frappe.set_user("Administrator")

	out["all_ok"] = all(v for v in out.values() if isinstance(v, bool))
	print(json.dumps(out, indent=1, default=str))


def cleanup():
	frappe.set_user("Administrator")
	_drop()
	if frappe.db.exists("User", OWNER):
		frappe.delete_doc("User", OWNER, force=True, ignore_permissions=True)
	if frappe.db.exists("Role", OWN_ROLE):
		frappe.delete_doc("Role", OWN_ROLE, force=True, ignore_permissions=True)
	frappe.db.commit()
	print("cleaned")
