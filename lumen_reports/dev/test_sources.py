# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
"""The registered-report contract: what gets in, who may run it, what is forwarded.

The fake app here is lumen_reports itself, because the rules say a source must
live inside an installed app and the checks need both a good and a bad case.

bench --site <site> execute lumen_reports.dev.test_sources.run
bench --site <site> execute lumen_reports.dev.test_sources.cleanup
"""

import json
from unittest.mock import patch

import frappe

from lumen_reports.dev.test_perms import _user
from lumen_reports.integrations import sources

OUTSIDER = "sources.outsider@test.local"  # no role of any kind
VIEWER = "sources.viewer@test.local"  # a Lumen role, so every source opens
TILL = "sources.till@test.local"  # only the owning app's own role

OWN_ROLE = "Lumen Source Probe"  # stands in for a Lumen role, on one report

SEEN = {}
ALLOW = {"value": True}


# ---- the stand-in for another app's reporting module


def provider(**filters):
	SEEN.clear()
	SEEN.update(filters)
	return {"rows": [{"total": 42}], "got": sorted(filters)}


def capability():
	return ALLOW["value"]


def boom(**filters):
	frappe.throw("the owning app said no", frappe.PermissionError)


def definitions():
	return [
		{
			"key": "lumen_reports.probe",
			"label": "Probe",
			"method": "lumen_reports.dev.test_sources.provider",
			"filters": ["from_date", "to_date", "outlet"],
			"capability": "lumen_reports.dev.test_sources.capability",
		},
		{
			# the shape LumenPOS uses: the till's own role is enough, here only
			"key": "lumen_reports.own_role",
			"label": "Own role",
			"method": "lumen_reports.dev.test_sources.provider",
			"filters": [],
			"roles": [OWN_ROLE, "Guest"],
			"capability": "lumen_reports.dev.test_sources.capability",
		},
		{
			"key": "lumen_reports.raiser",
			"label": "Raiser",
			"method": "lumen_reports.dev.test_sources.boom",
			"filters": [],
		},
		# every one below must be refused at registration
		{"key": "no_dot", "method": "lumen_reports.dev.test_sources.provider"},
		{"key": "lumen_reports.foreign", "method": "erpnext.something.run"},
		{"key": "ghost_app.report", "method": "ghost_app.x.run"},
		{"key": "lumen_reports.nofilters", "method": "lumen_reports.dev.test_sources.provider", "filters": "all"},
		{"key": "lumen_reports.badroles", "method": "lumen_reports.dev.test_sources.provider", "roles": "everyone"},
		"not a dict",
	]


def broken():
	raise RuntimeError("this hook is broken on purpose")


def _hooks(*paths):
	"""Patch only our hook; everything else keeps its real value."""
	real = frappe.get_hooks

	def fake(hook=None, *args, **kwargs):
		if hook == sources.HOOK:
			return list(paths)
		return real(hook, *args, **kwargs)

	return patch.object(frappe, "get_hooks", side_effect=fake)


def _as(user, fn, *args, **kwargs):
	frappe.set_user(user)
	try:
		return fn(*args, **kwargs)
	finally:
		frappe.set_user("Administrator")


def run():
	out = {}
	if not frappe.db.exists("Role", OWN_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": OWN_ROLE, "desk_access": 0}).insert(
			ignore_permissions=True
		)
	_user(OUTSIDER, [])
	_user(VIEWER, ["Lumen Restricted Viewer"])
	_user(TILL, [OWN_ROLE])
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- fixtures must survive the deny paths below
	ALLOW["value"] = True

	with _hooks("lumen_reports.dev.test_sources.definitions"):
		registry = sources._registry()
		out["good_one_registers"] = "lumen_reports.probe" in registry
		out["raiser_registers"] = "lumen_reports.raiser" in registry
		out["key_needs_an_app"] = "no_dot" not in registry
		out["cannot_reach_another_app"] = "lumen_reports.foreign" not in registry
		out["uninstalled_app_refused"] = "ghost_app.report" not in registry
		# filters or roles written as a string is a mistake in the owning app.
		# Dropping the whole definition is safer than running it with neither,
		# which would quietly show a shop the wrong period or the wrong people
		out["bad_filters_refused"] = "lumen_reports.nofilters" not in registry
		out["bad_roles_refused"] = "lumen_reports.badroles" not in registry
		out["guest_never_counts"] = registry["lumen_reports.own_role"]["roles"] == [OWN_ROLE]
		out["registry_size"] = len(registry)

		# ---- only declared filters travel, and blanks are dropped
		answer = sources.run_report(
			"lumen_reports.probe",
			json.dumps({"from_date": "2026-01-01", "to_date": "", "outlet": "Main", "secret": "x"}),
		)
		out["runs"] = answer["status"] == "ok"
		out["result_passed_through"] = answer["result"]["rows"][0]["total"] == 42
		out["declared_filters_forwarded"] = SEEN == {"from_date": "2026-01-01", "outlet": "Main"}
		out["undeclared_filter_dropped"] = "secret" not in SEEN
		out["blank_filter_dropped"] = "to_date" not in SEEN
		out["filters_used_reported"] = answer["filters_used"] == {"from_date": "2026-01-01", "outlet": "Main"}
		out["names_the_owner"] = answer["app"] == "lumen_reports" and answer["contract"] == 3

		sources.run_report("lumen_reports.probe", {"outlet": "Second"})
		out["dict_filters_accepted"] = SEEN == {"outlet": "Second"}

		# ---- refusals are statuses, not exceptions
		out["unknown_key_refused"] = sources.run_report("lumen_reports.nothing")["status"] == "unknown_report"

		ALLOW["value"] = False
		refused = sources.run_report("lumen_reports.probe")
		out["capability_refuses"] = refused["status"] == "not_permitted" and refused["result"] is None
		ALLOW["value"] = True

		# ---- a Lumen role opens everything
		out["lumen_role_runs"] = _as(VIEWER, sources.run_report, "lumen_reports.probe")["status"] == "ok"
		out["no_role_refused"] = (
			_as(OUTSIDER, sources.run_report, "lumen_reports.probe")["status"] == "needs_role"
		)

		# ---- the owning app's own role opens ITS report, and only that one
		out["own_role_runs_its_report"] = (
			_as(TILL, sources.run_report, "lumen_reports.own_role")["status"] == "ok"
		)
		out["own_role_does_not_open_others"] = (
			_as(TILL, sources.run_report, "lumen_reports.probe")["status"] == "needs_role"
		)
		out["own_role_still_obeys_capability"] = True
		ALLOW["value"] = False
		out["own_role_still_obeys_capability"] = (
			_as(TILL, sources.run_report, "lumen_reports.own_role")["status"] == "not_permitted"
		)
		ALLOW["value"] = True
		# and it is not a way into anything else of ours
		out["own_role_is_not_a_lumen_role"] = not _as(TILL, sources._has_app_role)
		out["own_role_opens_no_dashboard"] = not _as(
			TILL, frappe.has_permission, "Lumen Dashboard", "read"
		)

		# ---- the owning app's own error is not swallowed
		try:
			sources.run_report("lumen_reports.raiser")
			out["provider_error_travels"] = False
		except frappe.PermissionError:
			frappe.clear_last_message()
			out["provider_error_travels"] = True

		# ---- discovery
		listed = sources.list_reports()
		keys = [r["key"] for r in listed["reports"]]
		out["lists_what_registered"] = keys == sorted(keys) and "lumen_reports.probe" in keys
		out["list_says_who_can_run"] = all(r["can_run"] for r in listed["reports"])
		out["list_reports_the_roles"] = [r for r in listed["reports"] if r["key"] == "lumen_reports.own_role"][
			0
		]["roles"] == [OWN_ROLE]

		till_list = {r["key"]: r["can_run"] for r in _as(TILL, sources.list_reports)["reports"]}
		out["list_follows_the_same_rule"] = (
			till_list["lumen_reports.own_role"] is True and till_list["lumen_reports.probe"] is False
		)
		out["outsider_told_they_cannot"] = not any(
			r["can_run"] for r in _as(OUTSIDER, sources.list_reports)["reports"]
		)

	# ---- a broken hook in one app must not hide the rest
	with _hooks("lumen_reports.dev.test_sources.broken", "lumen_reports.dev.test_sources.definitions"):
		out["broken_hook_survived"] = "lumen_reports.probe" in sources._registry()

	# ---- nothing registered is a quiet, empty answer
	with _hooks():
		out["empty_registry_is_fine"] = sources.list_reports()["reports"] == []
		out["empty_registry_refuses"] = sources.run_report("lumen_reports.probe")["status"] == "unknown_report"

	out["all_ok"] = all(v for v in out.values() if isinstance(v, bool))
	print(json.dumps(out, indent=1, default=str))


def cleanup():
	frappe.set_user("Administrator")
	for email in (OUTSIDER, VIEWER, TILL):
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
	if frappe.db.exists("Role", OWN_ROLE):
		frappe.delete_doc("Role", OWN_ROLE, force=True, ignore_permissions=True)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- dev cleanup run from bench execute
	print("cleaned")
