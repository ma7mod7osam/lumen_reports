# Dev test for Ask AI: mocks the Gemini call to prove the orchestration,
# validation, repair loop, pruning, and persistence work without a real key.
# bench --site <site> execute lumen_reports.dev.test_ai.run

import json
from unittest import mock

import frappe

from lumen_reports import ai

BRAND_WIDGET = {
	"title": "Revenue by Brand",
	"widget_type": "Bar Chart",
	"query": {
		"doctype": "Sales Invoice Item",
		"parent_doctype": "Sales Invoice",
		"aggregate": {"function": "sum", "field": "amount"},
		"group_by": {"field": "brand", "via": {"link_field": "item_code", "doctype": "Item"}},
		"filters": [["docstatus", "=", 1]],
	},
}

KPI_WIDGET = {
	"title": "Total Revenue",
	"widget_type": "Number Card",
	"query": {
		"doctype": "Sales Invoice",
		"aggregate": {"function": "sum", "field": "grand_total"},
		"filters": [["docstatus", "=", 1]],
	},
}

# groups by the line's own (empty) brand copy -> all-null series -> pruned
EMPTY_WIDGET = {
	"title": "Empty Dimension",
	"widget_type": "Bar Chart",
	"query": {
		"doctype": "Sales Invoice Item",
		"parent_doctype": "Sales Invoice",
		"aggregate": {"function": "sum", "field": "amount"},
		"group_by": {"field": "brand"},
		"filters": [["docstatus", "=", 1]],
	},
}

BAD_WIDGET = {
	"title": "Broken",
	"widget_type": "Bar Chart",
	"query": {
		"doctype": "Sales Invoice",
		"aggregate": {"function": "sum", "field": "no_such_field"},
		"group_by": {"field": "status"},
	},
}


def _answer(widgets):
	return {
		"title": "Sales Overview",
		"explanation": "test",
		"widgets": json.loads(json.dumps(widgets)),
		"suggestions": ["Add a monthly trend", "Show top customers"],
		"questions": ["Which year?"],
	}


# One patch.object per test replaces ai._generate with this dispatcher; the
# test bodies then swap  freely. Idiomatic mocking, no bare
# module-attribute assignment, restored automatically on exit.
class _Fake:
	target = None

	def __call__(self, prompt, key, model):
		return self.target(prompt, key, model)


_fake = _Fake()


def run():
	out = {}
	ai.save_ai_settings(api_key="TEST-FAKE-KEY")
	calls = {"n": 0}

	def scripted(responses):
		def inner(prompt, key, model):
			calls["n"] += 1
			if calls["n"] == 1:
				return {"doctypes": ["Sales Invoice"]}
			return responses[min(calls["n"] - 2, len(responses) - 1)]

		calls["n"] = 0
		return inner

	patcher = mock.patch.object(ai, "_generate", _fake)
	patcher.start()
	try:
		# multi-widget happy path: empty widgets are FLAGGED, never dropped
		_fake.target = scripted([_answer([KPI_WIDGET, BRAND_WIDGET, EMPTY_WIDGET])])
		answer = ai.ask_ai("detailed sales dashboard")
		out["widget_count"] = len(answer["widgets"])  # expect 3 — nothing dropped
		out["empty_flags"] = [w["empty"] for w in answer["widgets"]]  # [False, False, True]
		out["kpi_value"] = answer["widgets"][0]["result"]["value"]
		out["brand_labels"] = answer["widgets"][1]["result"]["labels"]

		out["suggestions"] = answer["suggestions"]
		out["questions"] = answer["questions"]

		# best-practice coercion: a donut on an hour distribution becomes a bar
		hour_donut = {
			"title": "Peak Hours",
			"widget_type": "Donut Chart",
			"query": {
				"doctype": "Sales Invoice",
				"aggregate": {"function": "count"},
				"group_by": {"field": "creation", "time_grain": "hour"},
				"filters": [["docstatus", "=", 1]],
			},
		}
		_fake.target = scripted([_answer([hour_donut])])
		coerced = ai.ask_ai("peak hours")
		out["hour_donut_coerced_to"] = coerced["widgets"][0]["widget"]["widget_type"]

		# batch repair: one bad widget in the first answer, fixed in the second
		_fake.target = scripted([_answer([KPI_WIDGET, BAD_WIDGET]), _answer([KPI_WIDGET, BRAND_WIDGET])])
		answer2 = ai.ask_ai("sales dashboard")
		out["repair_widgets"] = len(answer2["widgets"])
		out["repair_calls"] = calls["n"]  # pick + first + repair = 3

		# history + existing_titles are accepted and forwarded into prompts
		seen_prompts = []

		def spy(prompt, key, model):
			seen_prompts.append(prompt)
			if len(seen_prompts) == 1:
				return {"doctypes": ["Sales Invoice"]}
			return _answer([BRAND_WIDGET])

		_fake.target = spy
		ai.ask_ai(
			"also add brand split",
			history=[{"role": "user", "text": "sales dashboard"}, {"role": "assistant", "text": "Built: Sales Overview"}],
			existing_titles=["Total Revenue"],
		)
		out["history_in_prompt"] = "sales dashboard" in seen_prompts[0]
		out["existing_titles_in_prompt"] = "Total Revenue" in seen_prompts[1]

		# clarify with options passes through
		_fake.target = lambda p, k, m: {"clarify": "Which company?", "options": ["Lumen Retail", "All"]}
		clarified = ai.ask_ai("how are sales")
		out["clarify_options"] = clarified.get("options")

		# save as NEW dashboard
		saved = ai.save_ai_result([w["widget"] for w in answer["widgets"]], title="AI Sales Overview")
		out["new_slug"] = saved["slug"]
		doc = frappe.get_doc("Lumen Dashboard", {"route_slug": saved["slug"]})
		out["new_dashboard_widgets"] = len(doc.widgets)
		out["kpi_tinted"] = json.loads(doc.widgets[0].style_json).get("tint")
		layout = json.loads(doc.layout_json)
		out["layout_ok"] = len(layout) == len(doc.widgets) and layout[0]["y"] == 0
		# append to existing dashboard
		before = len(frappe.get_doc("Lumen Dashboard", {"route_slug": "retail-sales"}).widgets)
		ai.save_ai_result([answer["widgets"][1]["widget"]], slug="retail-sales")
		after_doc = frappe.get_doc("Lumen Dashboard", {"route_slug": "retail-sales"})
		out["appended"] = len(after_doc.widgets) == before + 1
		# cleanup: delete the new dashboard and the appended widget
		frappe.delete_doc("Lumen Dashboard", doc.name, ignore_permissions=True)
		appended_id = after_doc.widgets[-1].widget_id
		after_doc.widgets = [w for w in after_doc.widgets if w.widget_id != appended_id]
		after_doc.layout_json = json.dumps(
			[i for i in json.loads(after_doc.layout_json) if i["widget_id"] != appended_id]
		)
		after_doc.save(ignore_permissions=True)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit — dev/test helper run by hand via bench execute; commits fixtures so the assertions that follow (which roll back on denial) cannot undo them
	finally:
		patcher.stop()
		ai.clear_ai_key()
	return out


def run_site():
	"""Site-wide key fallback + admin gate."""
	out = {}

	def fake_generate(prompt, key, model):
		out.setdefault("keys_seen", []).append(key)
		# the pipeline makes several calls per ask (pick, build, analysis...);
		# answer by what is being asked rather than by call position
		if "Available doctypes" in prompt:
			return {"doctypes": ["Sales Invoice"]}
		if "business analyst" in prompt:
			return {"analysis": {"headline": "ok", "findings": ["ok"]}}
		return _answer([BRAND_WIDGET])

	patcher = mock.patch.object(ai, "_generate", _fake)
	patcher.start()
	try:
		ai.clear_ai_key()
		ai.save_site_ai_settings(api_key="SITE-SHARED-KEY")
		_fake.target = fake_generate
		answer = ai.ask_ai("revenue by brand")
		out["site_fallback_worked"] = answer["widgets"][0]["result"]["labels"] == [
			"Vertex",
			"Lumina",
			"Nimbus",
			"Terra",
		]
		ai.save_ai_settings(api_key="PERSONAL-KEY")
		ai.ask_ai("revenue by brand")
		out["personal_won"] = out["keys_seen"][-1] == "PERSONAL-KEY"
		frappe.set_user("viewer@lumen.test")
		try:
			ai.save_site_ai_settings(api_key="HACK")
			out["viewer_blocked"] = False
		except frappe.PermissionError:
			out["viewer_blocked"] = True
	finally:
		patcher.stop()
		frappe.set_user("Administrator")
		ai.clear_ai_key()
		ai.clear_site_ai_key()
	return out
