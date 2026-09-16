# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
"""PDF reports and scheduled delivery hide themselves where WeasyPrint is absent
(Frappe v14). This drives the False path, which cannot occur on this v15 bench,
by patching the capability check.

bench --site <site> execute lumen_reports.dev.test_reports_gate.run
"""

import json
from unittest.mock import patch

import frappe

from lumen_reports import report, schedules

MSG = "version 15 or newer"


def _throws(fn, *args, **kwargs):
	try:
		fn(*args, **kwargs)
		return ""
	except Exception as e:
		msg = frappe.utils.strip_html(str(e))
		frappe.clear_last_message()
		return msg


def run():
	out = {}

	# on this bench WeasyPrint is installed, so the real answer is True and the
	# features are live (proven by test_pdf and test_schedules)
	out["supported_here"] = report.reports_supported() is True

	# the whole gate turns on one boolean, so patch it to the v14 answer
	with patch.object(report, "reports_supported", return_value=False):
		out["download_refused"] = MSG in _throws(report.download, "retail-sales")
		out["save_schedule_refused"] = MSG in _throws(schedules.save_schedule, {"slug": "retail-sales"})
		out["send_test_refused"] = MSG in _throws(schedules.send_test, "retail-sales")

		# run_due must return before it ever queries for due rows
		with patch.object(frappe, "get_all", side_effect=AssertionError("run_due should short-circuit")):
			schedules.run_due()  # no raise = it returned at the guard
		out["run_due_short_circuits"] = True

	# and with the real (True) capability, the gate does not fire: download gets
	# past it to the permission check (a bad slug is a DoesNotExist, not the gate)
	out["gate_open_when_supported"] = MSG not in _throws(report.download, "__no_such_dashboard__")

	out["all_ok"] = all(v is True or (isinstance(v, bool) and v) for v in out.values())
	print(json.dumps(out, indent=1))
