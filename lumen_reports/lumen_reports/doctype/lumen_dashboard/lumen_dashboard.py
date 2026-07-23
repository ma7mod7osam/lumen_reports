# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class LumenDashboard(Document):
	def validate(self):
		self.validate_slug()
		self.validate_widget_ids()
		self.validate_json_fields()

	def validate_slug(self):
		if not self.route_slug:
			self.route_slug = frappe.scrub(self.dashboard_title).replace("_", "-")
		if not SLUG_PATTERN.match(self.route_slug):
			frappe.throw(_("Slug must contain only lowercase letters, numbers and hyphens"))

	def validate_widget_ids(self):
		seen = set()
		for row in self.widgets:
			if row.widget_id in seen:
				frappe.throw(_("Duplicate widget ID: {0}").format(row.widget_id))
			seen.add(row.widget_id)

	def validate_json_fields(self):
		for fieldname in ("layout_json", "filters_json"):
			value = self.get(fieldname)
			if value and isinstance(value, str):
				try:
					json.loads(value)
				except ValueError:
					frappe.throw(_("Invalid JSON in field {0}").format(fieldname))

	def on_update(self):
		# widget queries may have changed; rebuild the doctype -> dashboard registry
		frappe.cache.delete_value("lumen_reports:doctype_registry")

	def on_trash(self):
		frappe.cache.delete_value("lumen_reports:doctype_registry")
