# Copyright (c) 2026, Lumen and contributors
# For license information, please see license.txt

"""Scheduled report delivery.

A schedule names a dashboard, a cadence and a list of people on the site.
When it comes due, every recipient gets their own PDF, rendered while the
job runs as that person, so the permission rules that decide what they see
on screen decide what is printed for them. Someone who cannot open the
dashboard is skipped, not sent a copy made with someone else's access.

Recipients are limited to active users of the site for the same reason: an
outside address has no permissions to apply.
"""

import datetime

import frappe
from frappe import _

from lumen_reports import api, licensing, report

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TEST_COOLDOWN_SECONDS = 30

MAIL = {
	"en": {
		"subject": "Scheduled report: {0}",
		"body": (
			"<p>Your scheduled report <b>{0}</b> is attached.</p>"
			"<p>It was generated on {1} with your own access rights, so it only includes data "
			"you are allowed to see.</p>"
		),
		"test_subject": "Test report: {0}",
	},
	"ar": {
		"subject": "تقرير مجدول: {0}",
		"body": (
			'<div dir="rtl"><p>مرفق تقريرك المجدول <b>{0}</b>.</p>'
			"<p>تم إنشاؤه في {1} وفق صلاحياتك، لذلك لا يتضمن إلا البيانات المسموح لك بالاطلاع عليها.</p></div>"
		),
		"test_subject": "تقرير تجريبي: {0}",
	},
}


# ---------------------------------------------------------------- timing


def next_run(schedule, after=None):
	"""The next moment this schedule is due, strictly after `after`."""
	now = after or frappe.utils.now_datetime()
	at = frappe.utils.get_time(schedule.send_time or "08:00:00")
	today = datetime.datetime.combine(now.date(), at)
	if schedule.frequency == "Daily":
		return today if today > now else today + datetime.timedelta(days=1)
	if schedule.frequency == "Monthly":
		day = max(1, min(28, int(schedule.day_of_month or 1)))
		candidate = datetime.datetime.combine(now.date().replace(day=day), at)
		if candidate > now:
			return candidate
		year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
		return datetime.datetime.combine(datetime.date(year, month, day), at)
	target = WEEKDAYS.index(schedule.day_of_week or "Monday")
	candidate = datetime.datetime.combine(now.date() + datetime.timedelta(days=(target - now.weekday()) % 7), at)
	return candidate if candidate > now else candidate + datetime.timedelta(days=7)


def run_due():
	"""Scheduler tick: hand every schedule that has come due to a job."""
	now = frappe.utils.now_datetime()
	for name in frappe.get_all(
		"Lumen Report Schedule",
		filters={"enabled": 1, "next_run": ["<=", now]},
		pluck="name",
	):
		doc = frappe.get_doc("Lumen Report Schedule", name)
		# step next_run forward before the job starts, so a slow render can
		# never be picked up a second time by the next tick
		doc.db_set("next_run", next_run(doc, after=now), update_modified=False)
		frappe.enqueue(
			"lumen_reports.schedules.deliver",
			queue="long",
			name=name,
			job_id=f"lumen_report_{name}",
			deduplicate=True,
			enqueue_after_commit=True,
		)


# ---------------------------------------------------------------- sending


def _options_for(schedule):
	return {
		"lang": "ar" if schedule.language == "Arabic" else "en",
		"paper": schedule.paper or "A4",
		"summary": bool(schedule.include_summary),
	}


NO_OUTGOING = "Not sent: this site has no outgoing email account set up"


def outgoing_ready() -> bool:
	"""Whether this site can send mail at all. Without an outgoing account
	Frappe refuses every message, so there is no point rendering PDFs."""
	from frappe.email.doctype.email_account.email_account import EmailAccount

	try:
		return bool(EmailAccount.find_outgoing())
	except Exception:
		frappe.clear_last_message()
		return False


def _mail(dashboard, user, options, pdf, test=False) -> bool:
	"""Queue the message. Returns False when Frappe queued nothing, which it
	does quietly for addresses it will not deliver to (admin@example.com)."""
	lang = options.get("lang") or "en"
	strings = MAIL[lang]
	stamp = report._fmt_date(frappe.utils.now_datetime(), lang)
	subject_key = "test_subject" if test else "subject"
	queued = frappe.sendmail(
		recipients=[frappe.db.get_value("User", user, "email") or user],
		subject=strings[subject_key].format(dashboard.dashboard_title),
		message=strings["body"].format(frappe.utils.escape_html(dashboard.dashboard_title), stamp),
		attachments=[{"fname": report._filename(dashboard, options), "fcontent": pdf}],
		reference_doctype="Lumen Dashboard",
		reference_name=dashboard.name,
	)
	return bool(queued)


def _send_as(dashboard_name, user, options) -> str:
	"""Render and send one person's copy while running as that person.
	Returns sent, no_access or undeliverable."""
	frappe.set_user(user)  # nosemgrep: frappe-setuser -- each copy must carry its recipient's own permissions
	if not frappe.has_permission("Lumen Dashboard", "read", dashboard_name):
		return "no_access"
	dashboard = frappe.get_doc("Lumen Dashboard", dashboard_name)
	pdf = report.render_pdf(dashboard, {**options, "prepared_for": frappe.utils.get_fullname(user)})
	return "sent" if _mail(dashboard, user, options, pdf) else "undeliverable"


def deliver(name):
	"""Background job: one PDF per recipient, each under their own access."""
	schedule = frappe.get_doc("Lumen Report Schedule", name)
	outcome = {"sent": [], "no_access": [], "undeliverable": [], "failed": []}
	if not outgoing_ready():
		schedule.db_set(
			{"last_sent_on": frappe.utils.now_datetime(), "last_status": NO_OUTGOING},
			update_modified=False,
		)
		outcome["failed"] = [row.user for row in schedule.recipients]
		outcome["reason"] = NO_OUTGOING
		return outcome

	options = _options_for(schedule)
	started_as = frappe.session.user
	try:
		for row in schedule.recipients:
			try:
				outcome[_send_as(schedule.dashboard, row.user, options)].append(row.user)
			except Exception:
				frappe.log_error(
					title=f"Lumen report {name}: could not send to {row.user}",
					message=frappe.get_traceback(),
				)
				outcome["failed"].append(row.user)
	finally:
		frappe.set_user(started_as)  # nosemgrep: frappe-setuser -- restore the job's own user

	parts = [f"Sent to {len(outcome['sent'])}"]
	if outcome["no_access"]:
		parts.append("skipped, cannot open the dashboard: " + ", ".join(outcome["no_access"]))
	if outcome["undeliverable"]:
		parts.append("not delivered, address refused by Frappe: " + ", ".join(outcome["undeliverable"]))
	if outcome["failed"]:
		parts.append("failed, see Error Log: " + ", ".join(outcome["failed"]))
	schedule.db_set(
		{"last_sent_on": frappe.utils.now_datetime(), "last_status": "; ".join(parts)},
		update_modified=False,
	)
	return outcome


# ---------------------------------------------------------------- endpoints


def _schedule_row(doc):
	# a Time field reads back as a timedelta ("8:00:00"), so format it rather
	# than slicing the string
	at = frappe.utils.get_time(doc.send_time or "08:00:00")
	return {
		"name": doc.name,
		"enabled": doc.enabled,
		"frequency": doc.frequency,
		"day_of_week": doc.day_of_week,
		"day_of_month": doc.day_of_month,
		"send_time": at.strftime("%H:%M"),
		"language": doc.language,
		"paper": doc.paper,
		"include_summary": doc.include_summary,
		"recipients": [r.user for r in doc.recipients],
		"next_run": doc.next_run,
		"last_sent_on": doc.last_sent_on,
		"last_status": doc.last_status,
		"can_edit": doc.has_permission("write"),
	}


@frappe.whitelist()
def get_schedules(slug: str):
	dashboard = api._get_dashboard_doc(slug)
	names = frappe.get_list(
		"Lumen Report Schedule",
		filters={"dashboard": dashboard.name},
		pluck="name",
		order_by="creation asc",
	)
	return {
		"schedules": [_schedule_row(frappe.get_doc("Lumen Report Schedule", n)) for n in names],
		"can_schedule": frappe.has_permission("Lumen Report Schedule", "create"),
		# the UI warns before anyone sets up a schedule that could never send
		"email_ready": outgoing_ready(),
	}


@frappe.whitelist()
def save_schedule(payload: str | dict):
	licensing.require_license()
	data = frappe.parse_json(payload)
	if data.get("name"):
		doc = frappe.get_doc("Lumen Report Schedule", data["name"])
	else:
		doc = frappe.new_doc("Lumen Report Schedule")
		doc.dashboard = api._get_dashboard_doc(data.get("slug") or "").name
	for field in (
		"enabled",
		"frequency",
		"day_of_week",
		"day_of_month",
		"send_time",
		"language",
		"paper",
		"include_summary",
	):
		if field in data:
			doc.set(field, data[field])
	if "recipients" in data:
		doc.set("recipients", [{"user": u} for u in data.get("recipients") or [] if isinstance(u, str) and u])
	doc.save()  # frappe enforces create/write, the controller validates the rest
	return _schedule_row(doc)


@frappe.whitelist()
def delete_schedule(name: str):
	frappe.delete_doc("Lumen Report Schedule", name)  # permission checked by frappe
	return {"ok": True}


@frappe.whitelist()
def send_test(slug: str, options: str | dict | None = None):
	"""Send the report to the person asking, now, rendered as themselves."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not outgoing_ready():
		frappe.throw(
			_(
				"This site has no outgoing email account yet, so nothing can be sent. Set one up in the "
				"desk under Email Account, then send the test again. Downloading the PDF works without it."
			),
			title=_("Email is not set up"),
		)
	key = f"lumen_report_test|{user}"
	# expires=True reads redis directly. The plain read caches a miss in the
	# request-local cache, which then hides the value set just below
	if frappe.cache.get_value(key, expires=True):
		frappe.throw(_("A test was just sent. Wait a few seconds before sending another."))
	frappe.cache.set_value(key, 1, expires_in_sec=TEST_COOLDOWN_SECONDS)

	dashboard = api._get_dashboard_doc(slug)  # read permission enforced here
	opts = report._options(options)
	opts["prepared_for"] = frappe.utils.get_fullname(user)
	pdf = report.render_pdf(dashboard, opts)
	address = frappe.db.get_value("User", user, "email") or user
	if not _mail(dashboard, user, opts, pdf, test=True):
		frappe.throw(_("Frappe will not deliver to {0}. Set a real email address on your user.").format(address))
	return {"sent_to": address}
