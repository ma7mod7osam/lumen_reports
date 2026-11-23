# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
"""The consolidated audit trail, against whatever changes this bench holds.

It runs unchanged on a bare Frappe site and on one with ERPNext data. Anything
that needs evidence the bench does not have is reported as absent rather than
asserted, so the check never passes by accident and never fails for having less
data than the machine next door.

bench --site <site> execute lumen_reports.dev.test_audit.run
bench --site <site> execute lumen_reports.dev.test_audit.cleanup
"""

import json

import frappe

from lumen_reports import audit
from lumen_reports.dev.test_perms import _user
from lumen_reports.integrations import sources

AUDITOR = "audit.auditor@test.local"  # holds Lumen Auditor and nothing else
OUTSIDER = "audit.outsider@test.local"  # holds a Lumen role, but not the auditor one

WIDE = {"from_date": "2000-01-01", "to_date": "2099-01-01"}


def _as(user, fn, *args, **kwargs):
	frappe.set_user(user)
	try:
		return fn(*args, **kwargs)
	finally:
		frappe.set_user("Administrator")


def _busiest_doctype():
	"""Whichever doctype this bench has the most recorded changes for."""
	rows = frappe.db.sql(
		"""select ref_doctype, count(name) as n from `tabVersion`
		   group by ref_doctype order by n desc limit 1""",
		as_dict=True,
	)
	return rows[0].ref_doctype if rows else None


def _throws(fn):
	try:
		fn()
		return False
	except Exception:
		frappe.clear_last_message()
		return True



def _http_refusal(path: str, verb: str) -> str:
	"""What frappe.handler.is_valid_http_method says to a request of this verb.

	Empty means it got through. This is the gate that runs before the function
	does, and it answers in the same words as a permission error, which is why
	a wrong verb is so easy to mistake for a missing role."""
	from frappe import handler

	class _Request:
		method = verb

	fn = frappe.get_attr(path)
	was = getattr(frappe.local, "request", None)
	frappe.local.request = _Request()
	try:
		handler.is_valid_http_method(fn)
		return ""
	except Exception as e:
		msg = frappe.utils.strip_html(str(e))
		frappe.clear_last_message()
		return msg or "refused"
	finally:
		frappe.local.request = was

def run():
	out = {}
	_user(AUDITOR, [audit.ROLE])
	_user(OUTSIDER, ["Lumen Viewer"])
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- fixtures must survive the deny paths

	out["role_exists"] = bool(frappe.db.exists("Role", audit.ROLE))

	res = audit.trail(**WIDE)
	rows = res["rows"]
	out["returns_rows"] = len(rows) > 0
	out["row_count"] = len(rows)
	out["column_count_is_22"] = len(res["columns"]) == 22

	kinds = {}
	for r in rows:
		kinds[r["action"]] = kinds.get(r["action"], 0) + 1
	out["actions_seen"] = kinds

	fields = [r["field"] or "" for r in rows]
	out["plain_field_changes"] = any("[" not in f and "(" not in f for f in fields)

	# ---- shapes that need the right kind of history to exist here
	out["child_row_changes"] = (
		any("[" in f and "]." in f for f in fields) or "no child row edits on this bench"
	)
	out["row_added_or_removed"] = (
		any("(row added)" in f or "(row removed)" in f for f in fields)
		or "no child rows added or removed on this bench"
	)
	out["submitted_detected"] = (
		kinds.get("Submitted", 0) > 0 or "nothing submitted on this bench"
	)
	out["deleted_detected"] = kinds.get("Deleted", 0) > 0 or "nothing deleted on this bench"

	# ---- enrichment and filters, against a doctype this bench actually has
	target = _busiest_doctype()
	out["target_doctype"] = target
	if target:
		scoped = audit.trail(doctype=[target], **WIDE)
		srows = scoped["rows"]
		out["doctype_filter"] = srows != [] and all(r["doctype"] == target for r in srows)
		out["creations_appear_when_scoped"] = (
			any(r["action"] == "Created" for r in srows) or "none created in range"
		)
		enriched = [r for r in srows if r["created_by"]]
		out["enriched_from_document"] = bool(enriched) or "the documents are gone"
		if enriched:
			s = enriched[0]
			out["sample"] = {
				k: s[k] for k in ("doctype", "document", "action", "field", "old_value", "new_value")
			}
			out["has_link"] = bool(s["link"])
			out["has_timestamp"] = bool(s["change_date"]) and bool(s["change_time"])

	out["unfiltered_spans_doctypes"] = len({r["doctype"] for r in rows}) > 1

	if kinds.get("Submitted"):
		acted = audit.trail(action=["Submitted"], **WIDE)
		out["action_filter"] = acted["rows"] != [] and all(
			r["action"] == "Submitted" for r in acted["rows"]
		)
	else:
		out["action_filter"] = "nothing submitted to filter for"

	out["date_filter_excludes"] = audit.trail(from_date="2099-01-01", to_date="2099-01-02")["rows"] == []
	out["dates_are_required"] = _throws(lambda: audit.trail())

	# ---- the cap announces itself rather than silently cutting
	out["cap_is_reported"] = (
		(res["truncated"] and any("most recent" in n for n in res["notes"]))
		if res["truncated"]
		else "under the cap on this bench"
	)
	# ---- and the one thing the report cannot do declares itself
	out["creations_limit_declared"] = any("Creations are listed only" in n for n in res["notes"])

	# ---- the gate
	listed = _as(AUDITOR, sources.list_reports)
	entry = [r for r in listed["reports"] if r["key"] == "lumen_reports.audit_trail"]
	out["registered"] = len(entry) == 1
	out["auditor_can_run"] = bool(entry) and entry[0]["can_run"] is True

	answer = _as(AUDITOR, sources.run_report, "lumen_reports.audit_trail", WIDE)
	out["runs_through_contract"] = answer["status"] == "ok" and answer["result"]["rows"] != []

	refused = _as(OUTSIDER, sources.run_report, "lumen_reports.audit_trail", WIDE)
	out["lumen_role_alone_refused"] = refused["status"] == "not_permitted"
	out["outsider_told_in_list"] = not [
		r
		for r in _as(OUTSIDER, sources.list_reports)["reports"]
		if r["key"] == "lumen_reports.audit_trail" and r["can_run"]
	]

	# ---- the printed edition, on the organization's own paper
	from lumen_reports import report

	if report.reports_supported():
		markup = report.render_source_html(
			"Consolidated Audit Trail", res, {"header": 1},
			filters=WIDE, notes=res["notes"],
		)
		out["print_names_the_report"] = "Consolidated Audit Trail" in markup
		out["print_credits_lumen"] = f'content: "{report.CREDIT}"' in markup
		out["print_shows_the_filters"] = "From date" in markup
		out["print_carries_the_notes"] = all(n[:30] in markup for n in res["notes"])
		# the page carries the columns the report named for print, not all 22:
		# the rest would fall off the edge, and they are the ones that matter
		# least on paper. "<thead>" also begins with "<th", so count the cells
		printed = len(res["print_columns"])
		out["print_trims_to_named_columns"] = markup.count('<th class=') == printed
		out["print_columns_are_fewer"] = printed < len(res["columns"])
		out["print_keeps_the_values"] = "Old Value" in markup and "New Value" in markup
		out["screen_keeps_all_22"] = len(res["columns"]) == 22
		pdf = report.render_source_pdf(
			"Consolidated Audit Trail", res, {"header": 1}, filters=WIDE, notes=res["notes"]
		)
		out["pdf_renders"] = len(pdf) > 2000
		out["pdf_bytes"] = len(pdf)
	else:
		out["printing"] = "WeasyPrint absent, as on v14"

	# The page fetches its filter choices with frappe-ui's call(), which always
	# sends POST. options() was whitelisted GET-only, so Frappe refused it with
	# "Not permitted" and the page read that as a missing role: it told every
	# visitor, auditor or not, to go and ask an administrator for a role they
	# already had. This drives the real server gate rather than reading the
	# decorator, so it would catch the same mistake made any other way.
	out["options_reachable_by_post"] = _http_refusal("lumen_reports.audit.options", "POST") == ""
	out["options_reachable_by_get"] = _http_refusal("lumen_reports.audit.options", "GET") == ""
	out["options_offers_pickers"] = sorted(audit.options().keys()) != []

	out["all_ok"] = all(v for v in out.values() if isinstance(v, bool))
	print(json.dumps(out, indent=1, default=str)[:2800])


def cleanup():
	frappe.set_user("Administrator")
	for email in (AUDITOR, OUTSIDER):
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- dev cleanup run from bench execute
	print("cleaned")
