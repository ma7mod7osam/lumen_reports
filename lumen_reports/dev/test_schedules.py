# Copyright (c) 2026, Lumen and contributors
# Dev test: scheduled report delivery.
# bench --site <site> execute lumen_reports.dev.test_schedules.run
# Uses the test users created by lumen_reports.dev.test_perms.run.

import datetime
import json
from unittest import mock

import frappe

from lumen_reports import schedules

SLUG = "retail-sales"
BUILDER = "lumen.builder@test.local"
RESTRICTED = "lumen.restricted@test.local"
VIEWER = "lumen.viewer@test.local"


def _at(text):
	return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")


def _timing():
	s = frappe._dict(frequency="Daily", send_time="08:00:00", day_of_week="Monday", day_of_month=1)
	out = {}
	out["daily_before_time"] = str(schedules.next_run(s, _at("2026-09-11 07:00")))
	out["daily_after_time"] = str(schedules.next_run(s, _at("2026-09-11 09:00")))
	s.frequency = "Weekly"
	# 2026-09-11 is a Friday
	out["weekly_monday"] = str(schedules.next_run(s, _at("2026-09-11 09:00")))
	out["weekly_same_day_later"] = str(schedules.next_run(frappe._dict(s, day_of_week="Friday"), _at("2026-09-11 07:00")))
	out["weekly_same_day_passed"] = str(schedules.next_run(frappe._dict(s, day_of_week="Friday"), _at("2026-09-11 09:00")))
	s.frequency = "Monthly"
	out["monthly_this_month"] = str(schedules.next_run(frappe._dict(s, day_of_month=20), _at("2026-09-11 09:00")))
	out["monthly_rolls_year"] = str(schedules.next_run(frappe._dict(s, day_of_month=1), _at("2026-12-05 09:00")))
	return out


def run():
	frappe.set_user("Administrator")
	results = {"timing": _timing()}
	dashboard = frappe.db.get_value("Lumen Dashboard", {"route_slug": SLUG})
	started = frappe.utils.now_datetime()
	created = []

	try:
		# a disabled or outside recipient is refused at save time
		try:
			bad = frappe.get_doc(
				{
					"doctype": "Lumen Report Schedule",
					"dashboard": dashboard,
					"frequency": "Daily",
					"send_time": "08:00:00",
					"recipients": [{"user": "Guest"}],
				}
			)
			bad.insert()
			created.append(bad.name)
			results["guest_recipient_refused"] = False
		except frappe.ValidationError:
			results["guest_recipient_refused"] = True

		# a viewer cannot create schedules at all
		frappe.set_user(VIEWER)
		try:
			frappe.get_doc(
				{
					"doctype": "Lumen Report Schedule",
					"dashboard": dashboard,
					"frequency": "Daily",
					"send_time": "08:00:00",
					"recipients": [{"user": VIEWER}],
				}
			).insert()
			results["viewer_cannot_schedule"] = False
		except frappe.PermissionError:
			results["viewer_cannot_schedule"] = True
		finally:
			frappe.set_user("Administrator")

		# the real thing: three recipients, one of whom cannot open the board
		doc = frappe.get_doc(
			{
				"doctype": "Lumen Report Schedule",
				"dashboard": dashboard,
				"frequency": "Weekly",
				"day_of_week": "Monday",
				"send_time": "08:00:00",
				"language": "Arabic",
				"recipients": [{"user": "Administrator"}, {"user": BUILDER}, {"user": RESTRICTED}, {"user": BUILDER}],
			}
		)
		doc.insert()
		created.append(doc.name)
		results["duplicate_recipient_dropped"] = [r.user for r in doc.recipients]
		results["next_run_set"] = str(doc.next_run)

		# without an outgoing email account nothing is rendered or claimed as sent
		if not schedules.outgoing_ready():
			outcome = schedules.deliver(doc.name)
			doc.reload()
			results["no_email_account_status"] = doc.last_status
			results["no_email_account_sent"] = outcome["sent"]
			try:
				schedules.send_test(SLUG, {"lang": "en"})
				results["no_email_account_test_refused"] = False
			except frappe.ValidationError as e:
				results["no_email_account_test_refused"] = "no outgoing email account" in str(e)

		# with one: every copy is rendered while running as its recipient. The
		# fake sendmail records who the session belonged to at that moment and
		# what the attached PDF actually says
		captured = []

		def fake_sendmail(**kwargs):
			from io import BytesIO

			from pypdf import PdfReader

			attachment = kwargs["attachments"][0]
			text = "".join(page.extract_text() or "" for page in PdfReader(BytesIO(attachment["fcontent"])).pages)
			captured.append(
				{
					"to": kwargs["recipients"],
					"session_user": frappe.session.user,
					"file": attachment["fname"],
					"is_pdf": attachment["fcontent"][:4] == b"%PDF",
					"prepared_for_line": "مخصص لـ" in text,
					"revenue_on_page": "1,090,597" in text,
				}
			)
			# Frappe returns nothing for an address it will not deliver to
			return [] if "example.com" in kwargs["recipients"][0] else ["queued"]

		with (
			mock.patch.object(schedules, "outgoing_ready", return_value=True),
			mock.patch.object(frappe, "sendmail", side_effect=fake_sendmail),
		):
			outcome = schedules.deliver(doc.name)
		results["sent"] = outcome["sent"]
		results["skipped_no_access"] = outcome["no_access"]
		results["undeliverable"] = outcome["undeliverable"]
		results["failed"] = outcome["failed"]
		results["copies"] = captured
		results["each_rendered_as_its_recipient"] = all(
			c["session_user"] in (u for u in ("Administrator", BUILDER)) for c in captured
		) and len({c["session_user"] for c in captured}) == len(captured)
		doc.reload()
		results["last_status"] = doc.last_status

		# the scheduler tick hands due schedules to a job and moves next_run on
		frappe.db.set_value("Lumen Report Schedule", doc.name, "next_run", started - datetime.timedelta(minutes=5))
		with mock.patch.object(frappe, "enqueue") as enqueue:
			schedules.run_due()
		results["tick_enqueued"] = [
			c.kwargs.get("name") for c in enqueue.call_args_list if c.kwargs.get("name") == doc.name
		]
		results["tick_moved_next_run_forward"] = frappe.db.get_value("Lumen Report Schedule", doc.name, "next_run") > started

		# a test send goes only to the person asking, with a cooldown
		frappe.cache.delete_value(f"lumen_report_test|{BUILDER}")
		frappe.set_user(BUILDER)
		with (
			mock.patch.object(schedules, "outgoing_ready", return_value=True),
			mock.patch.object(frappe, "sendmail", return_value=["queued"]) as sendmail,
		):
			out = schedules.send_test(SLUG, {"lang": "en"})
			results["test_sent_to"] = out["sent_to"]
			results["test_only_to_asker"] = sendmail.call_args.kwargs["recipients"] == [out["sent_to"]]
			try:
				schedules.send_test(SLUG, {"lang": "en"})
				results["test_cooldown"] = False
			except frappe.ValidationError:
				results["test_cooldown"] = True
		frappe.set_user("Administrator")
		frappe.cache.delete_value(f"lumen_report_test|{BUILDER}")
	finally:
		frappe.set_user("Administrator")
		for name in created:
			frappe.delete_doc("Lumen Report Schedule", name, force=True)
		for q in frappe.get_all(
			"Email Queue",
			filters={"reference_doctype": "Lumen Dashboard", "reference_name": dashboard, "creation": [">=", started]},
			pluck="name",
		):
			frappe.delete_doc("Email Queue", q, force=True)

	print(json.dumps(results, indent=1, default=str, ensure_ascii=False))
	return results
