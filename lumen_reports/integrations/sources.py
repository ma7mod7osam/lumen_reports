# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.

"""Reports another app computes, served through Lumen Reports.

Some numbers cannot be written as a dashboard widget. The cost of goods sold
reads a stock ledger, expands a bundle into its parts and estimates what has not
been posted yet; a cash count compares a drawer against a shift. That knowledge
belongs to the app that owns the subject, not to a general reporting tool, and
this app runs no raw SQL by design.

So the owning app keeps the arithmetic and registers it here, and Lumen Reports
becomes the way it is reached: it holds the entry point, the licence state, the
role gate and the filter contract, and the owning app's own permission rule is
asked before its code runs. An app that registers nothing loses nothing, and
Lumen Reports never imports the other app.

Registering, from the other app's hooks.py:

    lumen_report_sources = ["lumenpos.reporting.sources"]

That path is a callable returning one definition or a list of them:

    {
        "key": "lumenpos.sales_summary",      # <app>.<report>
        "label": "Sales summary",
        "method": "lumenpos.api.reports.sales_summary",
        "filters": ["from_date", "to_date", "pos_profile", "outlet"],
        "capability": "lumenpos.api.reports.can_see_sales_reports",   # optional
        "roles": ["LumenPOS Manager", "LumenPOS Reports"],            # optional
    }

`method` and `capability` are dotted paths into the registering app, and must
start with the app the key names: a hook cannot reach into a third app, and no
path ever comes from the caller. Only the filters a definition declares are
forwarded, so a caller cannot smuggle an argument past the owning app.

`roles` names roles that stand in for a Lumen role FOR THAT REPORT ONLY. A shop
manager who runs the till should not have to be given a reporting role as well to
read the till's own numbers, which is what the owner decided on 2026-10-27. It
opens nothing else: not a dashboard, not the studio, not another app's report.
The owning app's `capability` still decides, and without `roles` a Lumen role is
required as before.

The licence is reported, never enforced: reads are not blocked here, the same way
they are not blocked anywhere else in this app.

Contract version 3. Refusals come back as a status and a message, never as an
exception, so the caller can show them as they are.
"""

import re

import frappe
from frappe import _

from lumen_reports import licensing
from lumen_reports.www.lumen import APP_ROLES

CONTRACT_VERSION = 3
HOOK = "lumen_report_sources"

KEY = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
FILTER_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
ROLE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9 _()./-]{0,58}$")
DOTTED = re.compile(r"^[a-z][a-z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+$")

MAX_FILTERS = 12
MAX_ROLES = 8
MAX_VALUE = 140
MAX_LABEL = 120


# ---------------------------------------------------------------- registry


def _owned_by(path: str, app: str) -> bool:
	"""A dotted path that lives inside the app the key names."""
	return bool(DOTTED.match(path)) and path.split(".")[0] == app


def _clean_source(raw, installed: set) -> dict | None:
	"""One definition, or None if it is not something worth calling.

	A malformed definition is dropped rather than thrown, so one bad entry in
	one app cannot take the whole registry down with it."""
	if not isinstance(raw, dict):
		return None

	key = str(raw.get("key") or "")
	if not KEY.match(key):
		return None
	app = key.split(".")[0]
	if app not in installed:
		return None

	method = str(raw.get("method") or "")
	if not _owned_by(method, app):
		return None

	capability = str(raw.get("capability") or "")
	if capability and not _owned_by(capability, app):
		return None

	names = raw.get("filters") or []
	if not isinstance(names, (list, tuple)):
		return None
	filters = [str(n) for n in names if FILTER_NAME.match(str(n))][:MAX_FILTERS]

	declared = raw.get("roles") or []
	if not isinstance(declared, (list, tuple)):
		return None
	# Guest never counts: nobody signed in is Guest, and naming it would read
	# like a way to publish a report, which this is not
	roles = [str(r).strip() for r in declared]
	roles = [r for r in roles if ROLE_NAME.match(r) and r != "Guest"][:MAX_ROLES]

	return {
		"key": key,
		"app": app,
		"label": str(raw.get("label") or key)[:MAX_LABEL],
		"method": method,
		"capability": capability,
		"filters": filters,
		"roles": roles,
	}


def _registry() -> dict:
	"""Every registered report, by key. Reads hooks, never the caller."""
	out = {}
	installed = set(frappe.get_installed_apps())
	for path in frappe.get_hooks(HOOK) or []:
		try:
			defs = frappe.get_attr(path)() or []
		except Exception:
			# one app's broken hook must not hide every other app's reports
			frappe.log_error(
				title="Lumen Reports: a report source could not be read",
				message=f"{HOOK}: {path}",
			)
			continue
		if isinstance(defs, dict):
			defs = [defs]
		if not isinstance(defs, (list, tuple)):
			continue
		for raw in defs:
			source = _clean_source(raw, installed)
			if source:
				out[source["key"]] = source
	return out


# ---------------------------------------------------------------- gates


def _require_login():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in"), frappe.PermissionError)


def _has_app_role() -> bool:
	user = frappe.session.user
	return user == "Administrator" or bool(APP_ROLES & set(frappe.get_roles(user)))


def _may_reach(source: dict) -> bool:
	"""Whether this person may reach this report at all.

	A Lumen role opens every registered report. A report may also name roles of
	its own app that stand in for one, and they count for that report and for
	nothing else: this is not a way into dashboards, the studio, or another
	app's reports."""
	if _has_app_role():
		return True
	if not source["roles"]:
		return False
	return bool(set(source["roles"]) & set(frappe.get_roles()))


def _allowed(source: dict) -> bool:
	"""The owning app's own permission rule. No rule means the app did not ask
	for one; a rule that cannot be read or that raises counts as a refusal."""
	if not source["capability"]:
		return True
	try:
		return bool(frappe.get_attr(source["capability"])())
	except Exception:
		return False


def _refusal(status: str, message: str) -> dict:
	return {"status": status, "contract": CONTRACT_VERSION, "message": message, "result": None}


# ---------------------------------------------------------------- filters


def _filters(source: dict, raw) -> dict:
	"""Only what the definition declares, flattened to plain values.

	Anything the owning app did not name is dropped, so the caller cannot reach
	an argument the app never meant to expose."""
	raw = frappe.parse_json(raw) if isinstance(raw, str) else (raw or {})
	if not isinstance(raw, dict):
		frappe.throw(_("Filters must be an object"))

	out = {}
	for name in source["filters"]:
		if name not in raw:
			continue
		value = raw[name]
		if value is None or value == "":
			continue
		if isinstance(value, bool) or isinstance(value, (int, float)):
			out[name] = value
		else:
			out[name] = str(value)[:MAX_VALUE]
	return out


# ---------------------------------------------------------------- contract


@frappe.whitelist(methods=["GET"])
def list_reports() -> dict:
	"""What is registered on this site, and what this person may run."""
	_require_login()
	has_role = _has_app_role()
	reports = [
		{
			"key": s["key"],
			"label": s["label"],
			"app": s["app"],
			"filters": s["filters"],
			"roles": s["roles"],
			"can_run": _may_reach(s) and _allowed(s),
		}
		for s in _registry().values()
	]
	reports.sort(key=lambda r: r["key"])
	return {
		"contract": CONTRACT_VERSION,
		"license": licensing.get_status().get("status"),
		"has_role": has_role,
		"reports": reports,
	}


@frappe.whitelist(methods=["GET", "POST"])
def run_report(key: str, filters=None) -> dict:
	"""Run one registered report and hand back what its app returned.

	The owning app's result is passed through untouched under `result`: this app
	does not know what the numbers mean and must not reshape them."""
	_require_login()

	# the report is resolved first: which roles open it is now the report's own
	# business, so there is nothing to check until we know which one it is
	source = _registry().get(str(key or ""))
	if not source:
		return _refusal("unknown_report", _("No report is registered as {0}.").format(str(key or "")[:60]))

	if not _may_reach(source):
		return _refusal(
			"needs_role",
			_("You need a Lumen Reports role to see this. Ask your administrator for Lumen Restricted Viewer."),
		)

	if not _allowed(source):
		return _refusal("not_permitted", _("You do not have permission to see this report."))

	try:
		method = frappe.get_attr(source["method"])
	except Exception:
		return _refusal(
			"not_available",
			_("{0} is registered but its code could not be loaded.").format(source["label"]),
		)

	values = _filters(source, filters)
	# the owning app raises its own errors, and they travel as they are: a
	# refusal it wrote is clearer than anything this app could invent
	result = method(**values)

	return {
		"status": "ok",
		"contract": CONTRACT_VERSION,
		"key": source["key"],
		"label": source["label"],
		"app": source["app"],
		"filters_used": values,
		"generated_at": frappe.utils.now(),
		"message": None,
		"result": result,
	}
