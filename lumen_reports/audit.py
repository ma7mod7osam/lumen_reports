# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.

"""The consolidated audit trail: one row per change, across the whole site.

Asked for by an auditor, so it reads other people's documents by design. That is
the opposite of every other read in this app, and it is why it sits behind a role
of its own, Lumen Auditor, closed by default. Granting that role is a decision
about who may see everything, and the design note says so out loud.

Where the facts come from, each checked against real rows rather than the docs:

- `Version` holds one record per save of a tracked document: who in `owner`, when
  in `creation`, and the changes as JSON in `data`. Track Changes is on for about
  400 doctypes on a stock ERPNext site, so in practice this covers the ledger.
- That JSON holds FOUR kinds of change, not one. Roughly half the entries on a
  real site are child table edits, which is exactly what an auditor looks for on
  an invoice, so all four are flattened into the same row shape here.
- `docstatus` moving 0 to 1 is a submission and 1 to 2 a cancellation, so those
  two actions are evidence, not inference.
- `Deleted Document` holds deletions.
- A creation leaves no Version, so those rows come from the documents themselves.

Two columns the customer asked for have no source anywhere and are not invented:
an IP address is never stored against a document change (Activity Log keeps one
for sign-ins, which cannot be tied to an edit), and nothing ever asks a user why
they made a change.
"""

import json

import frappe
from frappe import _

ROLE = "Lumen Auditor"

ACTIONS = ("Created", "Modified", "Submitted", "Cancelled", "Amended", "Deleted")
STATUSES = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

# an auditor asking for a year of a busy site would otherwise pull the whole
# table into memory; the page says plainly when it stopped short
MAX_VERSIONS = 5000
MAX_ROWS = 2000
MAX_AMEND_DEPTH = 20


# ---------------------------------------------------------------- helpers


def _meta(doctype, cache):
	if doctype not in cache:
		try:
			cache[doctype] = frappe.get_meta(doctype)
		except Exception:
			cache[doctype] = None
	return cache[doctype]


def _label(doctype, parentfield, fieldname, cache):
	"""The human label for a field, following a child table when there is one."""
	meta = _meta(doctype, cache)
	if not meta:
		return fieldname
	if parentfield:
		df = meta.get_field(parentfield)
		child = _meta(df.options, cache) if df and df.options else None
		if child:
			target = child.get_field(fieldname)
			return target.label if target and target.label else fieldname
		return fieldname
	target = meta.get_field(fieldname)
	return target.label if target and target.label else fieldname


def _row_summary(row):
	"""A whole child row, short enough to read in a cell.

	An auditor needs to see what the row WAS, not every system field it carried,
	so the bookkeeping columns are left out."""
	if not isinstance(row, dict):
		return str(row)[:140]
	skip = {
		"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx",
		"parent", "parentfield", "parenttype", "doctype",
	}
	parts = [f"{k}={v}" for k, v in row.items() if k not in skip and v not in (None, "", 0)]
	return ", ".join(parts)[:140]


def _clean(values, allowed):
	"""A multi-select filter, reduced to the values we recognise."""
	if not values:
		return []
	if isinstance(values, str):
		values = frappe.parse_json(values) if values.strip().startswith("[") else [values]
	if not isinstance(values, (list, tuple)):
		values = [values]
	out = [str(v).strip() for v in values if str(v).strip()]
	return [v for v in out if v in allowed] if allowed else out


# ---------------------------------------------------------------- scope


def _allowed_companies():
	"""Companies this auditor is scoped to, empty when they are scoped to none.

	A group with one auditor per company sets a User Permission on Company, and
	the trail has to respect it even though the role itself is broad."""
	if not frappe.db.exists("DocType", "Company"):
		return []
	perms = frappe.permissions.get_user_permissions(frappe.session.user) or {}
	rows = perms.get("Company") or []
	return [r.get("doc") for r in rows if r.get("doc")]


def _doctypes_in_scope(modules, doctypes, cache):
	"""Which doctypes the trail should look at, and which of them are untracked."""
	if doctypes:
		names = doctypes
	elif modules:
		names = frappe.get_all(
			"DocType", filters={"module": ["in", modules], "istable": 0}, pluck="name",
			limit_page_length=0,
		)
	else:
		names = None  # every tracked doctype

	if names is None:
		return None, []

	tracked, untracked = [], []
	for name in names:
		meta = _meta(name, cache)
		if meta and meta.track_changes:
			tracked.append(name)
		elif meta:
			untracked.append(name)
	return tracked, untracked


# ---------------------------------------------------------------- the report


def trail(
	from_date=None,
	to_date=None,
	company=None,
	module=None,
	doctype=None,
	document=None,
	user=None,
	action=None,
	field=None,
	status=None,
	branch=None,
	cost_center=None,
):
	"""One row per field level change in the period. See the module docstring."""
	if not from_date or not to_date:
		frappe.throw(_("The audit trail needs a start and an end date."))

	cache = {}
	modules = _clean(module, None)
	doctypes = _clean(doctype, None)
	companies = _clean(company, None)
	users = _clean(user, None)
	actions = _clean(action, set(ACTIONS))
	statuses = _clean(status, set(STATUSES))

	scoped = _allowed_companies()
	if scoped:
		companies = [c for c in companies if c in scoped] if companies else scoped

	in_scope, untracked = _doctypes_in_scope(modules, doctypes, cache)

	rows = []
	notes = []
	if untracked:
		notes.append(
			_("Not tracked, so nothing is recorded for them: {0}").format(", ".join(sorted(untracked)[:12]))
		)

	rows += _version_rows(from_date, to_date, in_scope, document, users, actions, field, cache)
	if not actions or "Deleted" in actions:
		rows += _deleted_rows(from_date, to_date, in_scope, document, users, cache)
	if not actions or "Created" in actions:
		if in_scope is None:
			# a creation leaves no Version, so the only way to find one is to read
			# the documents themselves, and with no doctype chosen that is every
			# doctype on the site. Say so rather than quietly listing none.
			notes.append(
				_("Creations are listed only when you choose a module or a doctype. Everything else in the period is listed.")
			)
		else:
			rows += _created_rows(from_date, to_date, in_scope, document, users, cache)

	rows = _enrich(rows, companies, statuses, branch, cost_center, cache)
	rows.sort(key=lambda r: (r.get("change_on") or ""), reverse=True)

	truncated = len(rows) > MAX_ROWS
	if truncated:
		rows = rows[:MAX_ROWS]
		notes.append(
			_("Showing the {0} most recent changes. Narrow the dates or the doctype to see the rest.").format(MAX_ROWS)
		)

	return {
		"result_type": "rows",
		"columns": _columns(),
		"rows": rows,
		"total": len(rows),
		"truncated": truncated,
		"notes": notes,
	}


def _columns():
	return [
		{"fieldname": "company", "label": _("Company")},
		{"fieldname": "module", "label": _("Module")},
		{"fieldname": "doctype", "label": _("DocType")},
		{"fieldname": "document", "label": _("Document No.")},
		{"fieldname": "document_status", "label": _("Document Status")},
		{"fieldname": "action", "label": _("Action")},
		{"fieldname": "field", "label": _("Changed Field")},
		{"fieldname": "field_label", "label": _("Field Label")},
		{"fieldname": "old_value", "label": _("Old Value")},
		{"fieldname": "new_value", "label": _("New Value")},
		{"fieldname": "changed_by", "label": _("Changed By")},
		{"fieldname": "changed_by_name", "label": _("User Full Name")},
		{"fieldname": "change_date", "label": _("Change Date")},
		{"fieldname": "change_time", "label": _("Change Time")},
		{"fieldname": "created_on", "label": _("Created On")},
		{"fieldname": "created_by", "label": _("Created By")},
		{"fieldname": "modified_on", "label": _("Last Modified")},
		{"fieldname": "modified_by", "label": _("Last Modified By")},
		{"fieldname": "amended_from", "label": _("Amended From")},
		{"fieldname": "amendment_no", "label": _("Amendment No.")},
		{"fieldname": "version_id", "label": _("Audit Record")},
		{"fieldname": "link", "label": _("Document Link")},
	]


def _base(ref_doctype, docname, changed_by, changed_on, version_id, action, cache):
	meta = _meta(ref_doctype, cache)
	stamp = str(changed_on or "")
	return {
		"company": None,
		"module": meta.module if meta else None,
		"doctype": ref_doctype,
		"document": docname,
		"document_status": None,
		"action": action,
		"field": None,
		"field_label": None,
		"old_value": None,
		"new_value": None,
		"changed_by": changed_by,
		"changed_by_name": None,
		"change_date": stamp[:10],
		"change_time": stamp[11:],
		"change_on": stamp,
		"created_on": None,
		"created_by": None,
		"modified_on": None,
		"modified_by": None,
		"amended_from": None,
		"amendment_no": None,
		"version_id": version_id,
		"link": f"/app/{frappe.scrub(ref_doctype).replace('_', '-')}/{docname}" if docname else None,
	}


def _version_rows(from_date, to_date, in_scope, document, users, actions, field, cache):
	"""Every change recorded in Version, flattened to one row each."""
	filters = {"creation": ["between", [from_date, to_date]]}
	if in_scope is not None:
		if not in_scope:
			return []
		filters["ref_doctype"] = ["in", in_scope]
	if document:
		filters["docname"] = document
	if users:
		filters["owner"] = ["in", users]

	versions = frappe.get_all(
		"Version",
		filters=filters,
		fields=["name", "ref_doctype", "docname", "owner", "creation", "data"],
		order_by="creation desc",
		limit_page_length=MAX_VERSIONS,
		ignore_permissions=True,
	)

	wanted_field = (field or "").strip().lower()
	out = []
	for v in versions:
		data = frappe.parse_json(v.data or "{}") or {}

		for entry in data.get("changed") or []:
			if not isinstance(entry, (list, tuple)) or len(entry) < 3:
				continue
			name, old, new = entry[0], entry[1], entry[2]
			act = _docstatus_action(name, old, new)
			row = _base(v.ref_doctype, v.docname, v.owner, v.creation, v.name, act, cache)
			row["field"] = name
			row["field_label"] = _label(v.ref_doctype, None, name, cache)
			row["old_value"] = _value(old)
			row["new_value"] = _value(new)
			out.append(row)

		for entry in data.get("row_changed") or []:
			if not isinstance(entry, (list, tuple)) or len(entry) < 4:
				continue
			parentfield, index, _rowname, changes = entry[0], entry[1], entry[2], entry[3]
			for change in changes or []:
				if not isinstance(change, (list, tuple)) or len(change) < 3:
					continue
				name = f"{parentfield}[{index}].{change[0]}"
				row = _base(v.ref_doctype, v.docname, v.owner, v.creation, v.name, "Modified", cache)
				row["field"] = name
				row["field_label"] = _label(v.ref_doctype, parentfield, change[0], cache)
				row["old_value"] = _value(change[1])
				row["new_value"] = _value(change[2])
				out.append(row)

		for kind, key in (("row added", "added"), ("row removed", "removed")):
			for entry in data.get(key) or []:
				if not isinstance(entry, (list, tuple)) or len(entry) < 2:
					continue
				parentfield, rowdata = entry[0], entry[1]
				row = _base(v.ref_doctype, v.docname, v.owner, v.creation, v.name, "Modified", cache)
				row["field"] = f"{parentfield} ({kind})"
				row["field_label"] = _label(v.ref_doctype, None, parentfield, cache)
				summary = _row_summary(rowdata)
				if key == "added":
					row["new_value"] = summary
				else:
					row["old_value"] = summary
				out.append(row)

	if wanted_field:
		out = [r for r in out if wanted_field in (r["field"] or "").lower()]
	if actions:
		out = [r for r in out if r["action"] in actions]
	return out


def _docstatus_action(fieldname, old, new):
	"""A docstatus move is the only evidence of a submission or a cancellation."""
	if fieldname != "docstatus":
		return "Modified"
	try:
		old_i, new_i = int(old), int(new)
	except (TypeError, ValueError):
		return "Modified"
	if old_i == 0 and new_i == 1:
		return "Submitted"
	if old_i == 1 and new_i == 2:
		return "Cancelled"
	return "Modified"


def _value(value):
	if value is None:
		return None
	if isinstance(value, (dict, list)):
		return json.dumps(value, default=str)[:140]
	return str(value)[:140]


def _deleted_rows(from_date, to_date, in_scope, document, users, cache):
	if not frappe.db.exists("DocType", "Deleted Document"):
		return []
	filters = {"creation": ["between", [from_date, to_date]]}
	if in_scope is not None:
		if not in_scope:
			return []
		filters["deleted_doctype"] = ["in", in_scope]
	if document:
		filters["deleted_name"] = document
	if users:
		filters["owner"] = ["in", users]

	out = []
	for d in frappe.get_all(
		"Deleted Document",
		filters=filters,
		fields=["name", "deleted_doctype", "deleted_name", "owner", "creation"],
		order_by="creation desc",
		limit_page_length=MAX_VERSIONS,
		ignore_permissions=True,
	):
		row = _base(d.deleted_doctype, d.deleted_name, d.owner, d.creation, d.name, "Deleted", cache)
		row["field"] = "(whole document)"
		out.append(row)
	return out


def _created_rows(from_date, to_date, in_scope, document, users, cache):
	"""A creation leaves no Version, so it is read off the documents themselves."""
	if in_scope is None:
		return []  # every tracked doctype would mean a query per doctype on the site
	out = []
	for dt in in_scope:
		filters = {"creation": ["between", [from_date, to_date]]}
		if document:
			filters["name"] = document
		if users:
			filters["owner"] = ["in", users]
		try:
			docs = frappe.get_all(
				dt, filters=filters, fields=["name", "owner", "creation"],
				order_by="creation desc", limit_page_length=MAX_VERSIONS, ignore_permissions=True,
			)
		except Exception:
			continue
		for d in docs:
			row = _base(dt, d.name, d.owner, d.creation, None, "Created", cache)
			row["field"] = "(whole document)"
			out.append(row)
	return out


# ---------------------------------------------------------------- enrichment


def _enrich(rows, companies, statuses, branch, cost_center, cache):
	"""Fill the columns that live on the document, one query per doctype."""
	wanted = {}
	for row in rows:
		wanted.setdefault(row["doctype"], set()).add(row["document"])

	docs = {}
	for dt, names in wanted.items():
		meta = _meta(dt, cache)
		if not meta:
			continue
		fields = ["name", "owner", "creation", "modified", "modified_by"]
		for optional in ("docstatus", "company", "amended_from", "branch", "cost_center"):
			if optional == "docstatus" or meta.get_field(optional):
				fields.append(optional)
		try:
			found = frappe.get_all(
				dt, filters={"name": ["in", list(names)]}, fields=fields,
				limit_page_length=0, ignore_permissions=True,
			)
		except Exception:
			continue
		for d in found:
			docs[(dt, d.name)] = d

	names = {r["changed_by"] for r in rows if r["changed_by"]}
	full_names = {}
	if names:
		for u in frappe.get_all(
			"User", filters={"name": ["in", list(names)]}, fields=["name", "full_name"],
			limit_page_length=0, ignore_permissions=True,
		):
			full_names[u.name] = u.full_name

	status_by_value = {v: k for k, v in STATUSES.items()}
	wanted_status = {STATUSES[s] for s in statuses} if statuses else None

	out = []
	for row in rows:
		doc = docs.get((row["doctype"], row["document"]))
		row["changed_by_name"] = full_names.get(row["changed_by"])
		if doc:
			row["company"] = doc.get("company")
			row["created_on"] = str(doc.get("creation") or "")
			row["created_by"] = doc.get("owner")
			row["modified_on"] = str(doc.get("modified") or "")
			row["modified_by"] = doc.get("modified_by")
			row["amended_from"] = doc.get("amended_from")
			row["document_status"] = status_by_value.get(doc.get("docstatus"))
			if doc.get("amended_from"):
				row["amendment_no"] = _amendment_no(row["doctype"], row["document"])

		if companies and row["company"] not in companies:
			continue
		if wanted_status is not None and doc and doc.get("docstatus") not in wanted_status:
			continue
		if branch and doc and doc.get("branch") != branch:
			continue
		if cost_center and doc and doc.get("cost_center") != cost_center:
			continue
		out.append(row)
	return out


def _amendment_no(doctype, name, _cache={}):
	"""How many times this document has been amended, by walking the chain."""
	key = (doctype, name)
	if key in _cache:
		return _cache[key]
	count, current, seen = 0, name, set()
	while current and count < MAX_AMEND_DEPTH:
		if current in seen:
			break
		seen.add(current)
		parent = frappe.db.get_value(doctype, current, "amended_from")
		if not parent:
			break
		count += 1
		current = parent
	_cache[key] = count or None
	return _cache[key]


# ---------------------------------------------------------------- pickers


@frappe.whitelist(methods=["GET"])
def options():
	"""What the filters on the page should offer.

	Drawn from the trail itself rather than from the site's own lists. An auditor
	often holds nothing but the audit role, so asking for every User or every
	Company would be refused for want of read permission, and it would offer
	values that appear nowhere in the history anyway."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in"), frappe.PermissionError)
	if not can_see():
		frappe.throw(_("You need the {0} role to read the audit trail.").format(ROLE), frappe.PermissionError)

	seen = frappe.db.sql(
		"""select ref_doctype as name, count(name) as n from `tabVersion`
		   group by ref_doctype order by n desc limit 200""",
		as_dict=True,
	)
	doctypes = [r.name for r in seen]
	if frappe.db.exists("DocType", "Deleted Document"):
		for r in frappe.db.sql(
			"""select distinct deleted_doctype as name from `tabDeleted Document` limit 200""",
			as_dict=True,
		):
			if r.name and r.name not in doctypes:
				doctypes.append(r.name)

	modules = sorted(
		{
			m
			for m in frappe.get_all(
				"DocType", filters={"name": ["in", doctypes]}, pluck="module",
				limit_page_length=0, ignore_permissions=True,
			)
			if m
		}
	)

	users = [
		r.name
		for r in frappe.db.sql(
			"""select distinct owner as name from `tabVersion` order by owner limit 200""",
			as_dict=True,
		)
		if r.name
	]

	companies = _allowed_companies()
	if not companies and frappe.db.exists("DocType", "Company"):
		companies = frappe.get_all(
			"Company", pluck="name", limit_page_length=0, ignore_permissions=True
		)

	return {
		"doctypes": sorted(doctypes),
		"modules": modules,
		"users": users,
		"companies": sorted(companies or []),
		"actions": list(ACTIONS),
		"statuses": list(STATUSES),
		"max_rows": MAX_ROWS,
	}


# ---------------------------------------------------------------- registration


def sources():
	"""Registered through this app's own reports contract, so it gets the filter
	rules, the refusal states and, from phase two, PDF and scheduled delivery."""
	return [
		{
			"key": "lumen_reports.audit_trail",
			"label": "Consolidated Audit Trail",
			"method": "lumen_reports.audit.trail",
			"filters": [
				"from_date", "to_date", "company", "module", "doctype", "document",
				"user", "action", "field", "status", "branch", "cost_center",
			],
			"roles": [ROLE],
			"capability": "lumen_reports.audit.can_see",
		}
	]


def can_see():
	user = frappe.session.user
	return user == "Administrator" or ROLE in frappe.get_roles(user)
