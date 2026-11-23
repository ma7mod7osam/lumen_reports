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

	# v14 guard: the attribute form `frappe.cache.<attr>` raises AttributeError on
	# v14 (there frappe.cache is a function). Every use must be the call form
	# `frappe.cache().<attr>`. A dashboard controller slipped through the first pass
	# and broke on a real v14 bench, so this scans the source to keep it from
	# returning.
	stray = bare_cache_uses()
	out["no_bare_cache"] = stray == []
	out["bare_cache"] = stray

	# Every server method the SPA calls must accept POST, because frappe-ui's
	# call() always sends POST. A method whitelisted GET-only is refused by
	# Frappe with a bare "Not permitted", which reads to the person exactly like
	# a missing role. audit.options was GET-only, so the audit trail refused
	# every visitor, auditor or not, Administrator included.
	wrong = spa_calls_refusing_post()
	out["spa_calls_accept_post"] = wrong == []
	out["spa_calls_refusing_post"] = wrong

	out["all_ok"] = all(v for k, v in out.items() if isinstance(v, bool))
	print(json.dumps(out, indent=1))


def bare_cache_uses():
	"""Every `frappe.cache.<attr>` in the shipped package (not `frappe.cache()`,
	not `frappe.local.cache`). Must be empty for v14."""
	import os
	import re

	root = frappe.get_app_path("lumen_reports")
	pattern = re.compile(r"frappe\.cache\.\w")
	hits = []
	for base, _dirs, files in os.walk(root):
		if "__pycache__" in base:
			continue
		for name in files:
			if not name.endswith(".py"):
				continue
			path = os.path.join(base, name)
			for i, line in enumerate(open(path, encoding="utf-8"), 1):
				if pattern.search(line) and "frappe.local.cache" not in line:
					hits.append(f"{os.path.relpath(path, root)}:{i}")
	return hits


def spa_calls_refusing_post() -> list:
	"""The methods the SPA calls that a POST cannot reach.

	frappe-ui's call() hardcodes POST (node_modules/frappe-ui/src/utils/call.js),
	whatever the method reads or writes, so an endpoint declared
	methods=["GET"] is rejected by frappe.handler.is_valid_http_method before it
	runs. The message is "Not permitted", indistinguishable from a permission
	refusal, which is how a GET-only audit.options turned into a role error on
	the page and sent an auditor who held the role to his administrator."""
	import os
	import re

	root = os.path.join(frappe.get_app_path("lumen_reports"), "..", "frontend", "src")
	if not os.path.isdir(root):
		return ["frontend/src is not on this bench, so nothing was scanned"]

	called = set()
	for base, _dirs, names in os.walk(root):
		for name in names:
			if not name.endswith((".vue", ".js")):
				continue
			with open(os.path.join(base, name), encoding="utf-8") as f:
				called |= set(re.findall(r"""call\(\s*['\"]([\w.]+)['\"]""", f.read()))

	wrong = []
	for path in sorted(called):
		if not path.startswith("lumen_reports."):
			continue
		try:
			fn = frappe.get_attr(path)
		except Exception:
			wrong.append(f"{path} does not resolve")
			continue
		allowed = frappe.allowed_http_methods_for_whitelisted_func.get(fn)
		if allowed is None:
			wrong.append(f"{path} is not whitelisted")
		elif "POST" not in allowed:
			wrong.append(f"{path} allows only {allowed}")
	return wrong
