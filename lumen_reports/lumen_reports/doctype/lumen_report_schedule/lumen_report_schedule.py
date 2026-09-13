# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.

import frappe
from frappe import _
from frappe.model.document import Document

from lumen_reports import schedules


class LumenReportSchedule(Document):
	def validate(self):
		# whoever sets up the schedule must be able to see the dashboard
		# themselves; each recipient is checked again at send time
		if not frappe.has_permission("Lumen Dashboard", "read", self.dashboard):
			frappe.throw(_("You cannot read this dashboard"), frappe.PermissionError)

		seen = set()
		for row in list(self.recipients or []):
			if row.user in seen:
				self.remove(row)
				continue
			seen.add(row.user)
			enabled, user_type = frappe.db.get_value("User", row.user, ["enabled", "user_type"]) or (0, None)
			if not enabled or user_type != "System User":
				frappe.throw(
					_("{0} cannot receive reports: only active users of this site can").format(row.user)
				)
		if not self.recipients:
			frappe.throw(_("Add at least one recipient"))

		if self.frequency == "Monthly":
			self.day_of_month = max(1, min(28, int(self.day_of_month or 1)))

		self.next_run = schedules.next_run(self) if self.enabled else None
