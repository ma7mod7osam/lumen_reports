# Copyright (c) 2026, Lumen and contributors
# Development helper: seed demo data and a demo dashboard.
# Run with: bench --site <site> execute lumen_reports.dev.seed.run

import json
import random

import frappe
from frappe.utils import add_days, nowdate

STATUSES = ["Open", "Closed", "Cancelled"]
PRIORITIES = ["Low", "Medium", "High"]


def run():
	frappe.flags.in_import = True  # skip notifications etc.
	random.seed(42)
	_seed_todos()
	_seed_dashboard()
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — dev/test helper run by hand via bench execute; commits fixtures so the assertions that follow (which roll back on denial) cannot undo them
	return {
		"todos": frappe.db.count("ToDo"),
		"dashboards": frappe.get_all("Lumen Dashboard", pluck="route_slug"),
	}


def _seed_todos():
	if frappe.db.count("ToDo") >= 200:
		return
	for i in range(200):
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": f"Demo task #{i + 1}",
				"status": random.choices(STATUSES, weights=[5, 4, 1])[0],
				"priority": random.choice(PRIORITIES),
				"date": add_days(nowdate(), -random.randint(0, 180)),
			}
		).insert(ignore_permissions=True)


def _seed_dashboard():
	slug = "demo"
	if frappe.db.exists("Lumen Dashboard", {"route_slug": slug}):
		return

	widgets = [
		{
			"widget_id": "total_tasks",
			"title": "Total Tasks",
			"widget_type": "Number Card",
			"query_json": json.dumps({"doctype": "ToDo", "aggregate": {"function": "count"}}),
			"linked_filters": json.dumps({"status": "status", "priority": "priority"}),
		},
		{
			"widget_id": "open_tasks",
			"title": "Open Tasks",
			"widget_type": "Number Card",
			"query_json": json.dumps(
				{
					"doctype": "ToDo",
					"aggregate": {"function": "count"},
					"filters": [["status", "=", "Open"]],
				}
			),
			"linked_filters": json.dumps({"priority": "priority"}),
		},
		{
			"widget_id": "by_status",
			"title": "Tasks by Status",
			"widget_type": "Donut Chart",
			"query_json": json.dumps(
				{
					"doctype": "ToDo",
					"aggregate": {"function": "count"},
					"group_by": {"field": "status"},
				}
			),
			"linked_filters": json.dumps({"priority": "priority"}),
		},
		{
			"widget_id": "by_priority",
			"title": "Tasks by Priority",
			"widget_type": "Bar Chart",
			"query_json": json.dumps(
				{
					"doctype": "ToDo",
					"aggregate": {"function": "count"},
					"group_by": {"field": "priority"},
				}
			),
			"linked_filters": json.dumps({"status": "status"}),
		},
		{
			"widget_id": "over_time",
			"title": "Tasks Over Time",
			"widget_type": "Line Chart",
			"query_json": json.dumps(
				{
					"doctype": "ToDo",
					"aggregate": {"function": "count"},
					"group_by": {"field": "date", "time_grain": "month"},
				}
			),
			"linked_filters": json.dumps({"status": "status", "priority": "priority"}),
		},
		{
			"widget_id": "recent_tasks",
			"title": "Recent Tasks",
			"widget_type": "Table",
			"query_json": json.dumps(
				{
					"doctype": "ToDo",
					"fields": ["name", "description", "status", "priority", "date"],
					"sort": {"field": "date", "order": "desc"},
					"limit": 10,
				}
			),
			"linked_filters": json.dumps({"status": "status", "priority": "priority"}),
		},
	]

	layout = [
		{"widget_id": "total_tasks", "x": 0, "y": 0, "w": 3, "h": 2},
		{"widget_id": "open_tasks", "x": 3, "y": 0, "w": 3, "h": 2},
		{"widget_id": "by_status", "x": 6, "y": 0, "w": 6, "h": 5},
		{"widget_id": "by_priority", "x": 0, "y": 2, "w": 6, "h": 3},
		{"widget_id": "over_time", "x": 0, "y": 5, "w": 12, "h": 4},
		{"widget_id": "recent_tasks", "x": 0, "y": 9, "w": 12, "h": 5},
	]

	filters = [
		{
			"name": "status",
			"label": "Status",
			"fieldtype": "Select",
			"options": STATUSES,
		},
		{
			"name": "priority",
			"label": "Priority",
			"fieldtype": "Select",
			"options": PRIORITIES,
		},
	]

	frappe.get_doc(
		{
			"doctype": "Lumen Dashboard",
			"dashboard_title": "Demo Dashboard",
			"route_slug": slug,
			"description": "Auto-generated demo dashboard over ToDo",
			"auto_refresh": 1,
			"is_published": 1,
			"widgets": widgets,
			"layout_json": json.dumps(layout),
			"filters_json": json.dumps(filters),
		}
	).insert(ignore_permissions=True)
