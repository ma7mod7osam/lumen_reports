# Copyright (c) 2026, Lumen and contributors
# Dev test: the studio copilot's operation simulator, with the model scripted.
# bench --site <site> execute lumen_reports.dev.test_copilot.run
#
# The model is replaced by a fake so no Gemini quota is spent, but every
# widget the fake "builds" still goes through the real query engine.

import json
from unittest import mock

import frappe

from lumen_reports import ai, api, copilot

SLUG = "retail-sales"


class _Fake:
	"""Answers _generate by what the prompt is for. Tests swap .plan."""

	def __init__(self):
		self.plan = {"reply": "", "operations": []}
		self.prompts = []

	def __call__(self, prompt, key, model):
		self.prompts.append(prompt)
		if "You are the copilot inside Lumen Reports" in prompt:
			return self.plan
		if "Available doctypes" in prompt:
			return {"doctypes": ["Sales Invoice"]}
		if "You modify ONE analytics widget" in prompt:
			return {
				"explanation": "only paid",
				"widgets": [
					{
						"title": "Paid Revenue",
						"widget_type": "Number Card",
						"query": {
							"doctype": "Sales Invoice",
							"filters": [["docstatus", "=", 1], ["status", "=", "Paid"]],
							"aggregate": {"function": "sum", "field": "grand_total"},
						},
					}
				],
			}
		if "business analyst" in prompt:
			return {
				"analysis": {
					"headline": "Revenue reached 1.09M across 185 invoices — a strong quarter",
					"findings": ["Vertex leads with 30.7 percent", "North is the largest territory"],
					"watch": [],
				}
			}
		# the build step of ask_ai
		return {
			"title": "Territory view",
			"widgets": [
				{
					"title": "Revenue by Territory",
					"widget_type": "Bar Chart",
					"query": {
						"doctype": "Sales Invoice",
						"filters": [["docstatus", "=", 1]],
						"aggregate": {"function": "sum", "field": "grand_total"},
						"group_by": {"field": "territory"},
					},
				}
			],
		}


def _board():
	d = api.get_dashboard(SLUG)
	return {
		"title": d["title"],
		"theme": d.get("theme") or {},
		"widgets": d["widgets"],
		"layout": d["layout"],
	}


def _overlaps(layout):
	items = list(layout)
	for i, a in enumerate(items):
		for b in items[i + 1 :]:
			if copilot._collides(a, b):
				return (a["widget_id"], b["widget_id"])
	return None


def _first(board, predicate):
	return next(w for w in board["widgets"] if predicate(w))


def run():
	frappe.set_user("Administrator")
	fake = _Fake()
	results = {}
	board = _board()
	kpis = [w for w in board["widgets"] if w["widget_type"] == "Number Card"]
	trend = _first(board, lambda w: (w["query"].get("group_by") or {}).get("time_grain"))
	category = _first(
		board,
		lambda w: w["widget_type"] in ("Bar Chart", "Horizontal Bar")
		and (w["query"].get("group_by") or {})
		and not (w["query"].get("group_by") or {}).get("time_grain")
		and not w["query"].get("group_by2"),
	)

	with (
		mock.patch.object(ai, "_resolve_key", return_value=("test-key", "gemini-test", "site")),
		mock.patch.object(ai, "_generate", new=fake),
	):
		# 1. arranging a messy board: the cards sit at the bottom and the trend is
		# squeezed. The plan puts them back; every widget survives and nothing overlaps
		messy = json.loads(json.dumps(board))
		kpi_ids = {k["widget_id"] for k in kpis[:4]}
		for p in messy["layout"]:
			if p["widget_id"] in kpi_ids:
				p["y"] += 40
			if p["widget_id"] == trend["widget_id"]:
				p["w"] = 4
		items = [{"id": k["widget_id"], "x": i * 3, "y": 0, "w": 3, "h": 2} for i, k in enumerate(kpis[:4])]
		items.append({"id": trend["widget_id"], "x": 0, "y": 2, "w": 8, "h": 5})
		fake.plan = {
			"reply": "هذا الترتيب — جاهز",
			"operations": [{"op": "set_layout", "label": "نقل المؤشرات", "items": items}],
		}
		out = copilot.copilot("رتب اللوحة", messy)
		prop = out["proposal"]
		trend_pos = next(p for p in prop["layout"] if p["widget_id"] == trend["widget_id"])
		results["arrange_all_widgets_kept"] = len(prop["widgets"]) == len(board["widgets"])
		results["arrange_no_overlap"] = _overlaps(prop["layout"]) is None
		results["arrange_trend_width"] = trend_pos["w"]
		results["arrange_kpis_first_row"] = all(
			p["y"] == 0 for p in prop["layout"] if p["widget_id"] in {k["widget_id"] for k in kpis[:4]}
		)
		results["reply_has_no_em_dash"] = "—" not in out["reply"]
		results["reply_arabic_comma"] = "،" in out["reply"]

		# 2. theme: valid keys kept, invented ones dropped
		fake.plan = {
			"reply": "done",
			"operations": [
				{"op": "set_theme", "label": "dark green", "theme": {"preset": "emerald", "brand": "#2BC79B", "card": "shiny"}}
			],
		}
		out = copilot.copilot("dark green please", board)
		results["theme"] = out["proposal"]["theme"]

		# 3. a chart swap outside the data's family is refused, not applied
		fake.plan = {
			"reply": "ok",
			"operations": [{"op": "set_type", "label": "pie", "id": trend["widget_id"], "widget_type": "Pie Chart"}],
		}
		out = copilot.copilot("make the trend a pie", board)
		results["time_to_pie_refused"] = out["proposal"] is None and bool(out["notes"])

		# 4. a swap inside the family goes through
		fake.plan = {
			"reply": "ok",
			"operations": [{"op": "set_type", "label": "donut", "id": category["widget_id"], "widget_type": "Donut Chart"}],
		}
		out = copilot.copilot("donut", board)
		swapped = next(w for w in out["proposal"]["widgets"] if w["widget_id"] == category["widget_id"])
		results["category_to_donut"] = swapped["widget_type"]

		# 5. removing closes the hole it leaves
		fake.plan = {"reply": "ok", "operations": [{"op": "remove", "label": "rm", "id": kpis[0]["widget_id"]}]}
		out = copilot.copilot("remove the first card", board)
		prop = out["proposal"]
		results["remove_gone"] = all(w["widget_id"] != kpis[0]["widget_id"] for w in prop["widgets"])
		results["remove_no_overlap"] = _overlaps(prop["layout"]) is None

		# 6. a heading at the top pushes the board down and stays one row tall
		fake.plan = {
			"reply": "ok",
			"operations": [
				{"op": "add_element", "label": "h", "element": "Heading", "text": "Sales review", "subtext": "Q3", "position": "top"}
			],
		}
		out = copilot.copilot("add a title", board)
		prop = out["proposal"]
		head = prop["widgets"][0]
		head_pos = next(p for p in prop["layout"] if p["widget_id"] == head["widget_id"])
		results["heading_first"] = head["widget_type"] == "Heading" and head["style"]["text"] == "Sales review"
		results["heading_pos"] = [head_pos["y"], head_pos["h"], head_pos["w"]]
		results["heading_no_overlap"] = _overlaps(prop["layout"]) is None

		# 7. ids the board does not have are ignored, and an empty turn changes nothing
		fake.plan = {"reply": "hi", "operations": [{"op": "remove", "label": "x", "id": "nope"}]}
		out = copilot.copilot("hello", board)
		results["unknown_id_ignored"] = out["proposal"] is None

		# 8. clarify comes back as a question, unless the person already answered one
		fake.plan = {"clarify": "Which period?", "options": ["This year", "All time"]}
		out = copilot.copilot("compare periods", board)
		results["clarify"] = out.get("clarify") == "Which period?" and len(out.get("options") or []) == 2
		out = copilot.copilot("This year", board, answered=True)
		results["no_second_question"] = "clarify" not in out

		# 9. a selected widget is named in the prompt so "this" resolves
		fake.prompts.clear()
		fake.plan = {"reply": "ok", "operations": []}
		copilot.copilot("make this blue", board, selected=category["widget_id"])
		results["selection_in_prompt"] = category["widget_id"] in fake.prompts[0]

		# 10. new widgets are built by the real pipeline and executed by the engine
		fake.plan = {
			"reply": "ok",
			"operations": [{"op": "add_widgets", "label": "add", "request": "revenue by territory", "position": "bottom"}],
		}
		out = copilot.copilot("add revenue by territory", board)
		prop = out["proposal"]
		added = [w for w in prop["widgets"] if w["widget_id"].startswith("cp")]
		results["added_titles"] = [w["title"] for w in added]
		results["added_no_overlap"] = _overlaps(prop["layout"]) is None

		# 11. changing a widget's data goes through modify_ai_widget
		fake.plan = {
			"reply": "ok",
			"operations": [{"op": "change_data", "label": "paid", "id": kpis[0]["widget_id"], "instruction": "only paid"}],
		}
		out = copilot.copilot("only paid invoices", board)
		changed = next(w for w in out["proposal"]["widgets"] if w["widget_id"] == kpis[0]["widget_id"])
		results["change_data_title"] = changed["title"]

		# 12. the summary is written from real numbers and its dash is removed
		fake.plan = {"reply": "ok", "operations": [{"op": "add_summary", "label": "summary", "position": "top"}]}
		out = copilot.copilot("add an executive summary", board)
		summary = out["proposal"]["widgets"][0]
		results["summary_type"] = summary["widget_type"]
		results["summary_clean"] = "—" not in summary["style"]["text"]
		results["summary_first_line"] = summary["style"]["text"].split("\n")[0]

		# 13. explain answers without touching the board
		fake.plan = {"reply": "ok", "operations": [{"op": "explain", "label": "read"}]}
		out = copilot.copilot("what is my best territory", board)
		results["explain_no_change"] = out["proposal"] is None
		results["explain_headline"] = bool((out.get("analysis") or {}).get("headline"))

		# 14. the copilot runs the board's queries, so it is a builder's tool:
		# a viewer is turned away before any model call is made
		viewer = "lumen.viewer@test.local"
		if frappe.db.exists("User", viewer):
			fake.prompts.clear()
			frappe.set_user(viewer)
			try:
				copilot.copilot("add a summary", board)
				results["viewer_blocked"] = False
			except frappe.PermissionError:
				results["viewer_blocked"] = True
			finally:
				frappe.set_user("Administrator")
			results["viewer_spent_no_model_call"] = not fake.prompts
		else:
			results["viewer_blocked"] = "skipped: run test_perms first to create the viewer"

	print(json.dumps(results, indent=1, ensure_ascii=False))
	return results


def proposal():
	"""A realistic multi-operation turn on the retail board, computed by the
	real simulator with the planner scripted. Used to drive the studio UI in a
	browser when no Gemini key is configured."""
	frappe.set_user("Administrator")
	fake = _Fake()
	board = _board()
	category = _first(
		board,
		lambda w: w["widget_type"] in ("Bar Chart", "Horizontal Bar")
		and (w["query"].get("group_by") or {})
		and not (w["query"].get("group_by") or {}).get("time_grain")
		and not w["query"].get("group_by2"),
	)
	fake.plan = {
		"reply": "تم تجهيز التعديلات — راجعها وطبقها.",
		"operations": [
			{"op": "set_theme", "label": "تطبيق السمة الخضراء الداكنة", "theme": {"preset": "emerald"}},
			{"op": "add_element", "label": "إضافة عنوان في أعلى اللوحة", "element": "Heading", "text": "مراجعة المبيعات", "subtext": "الربع الثالث", "position": "top"},
			{"op": "set_type", "label": "تحويل " + category["title"] + " إلى حلقي", "id": category["widget_id"], "widget_type": "Donut Chart"},
			{"op": "add_widgets", "label": "إضافة الإيراد حسب المنطقة", "request": "revenue by territory", "position": "bottom"},
		],
		"suggestions": ["أضف ملخصا تنفيذيا", "قارن بالربع الماضي"],
	}
	with (
		mock.patch.object(ai, "_resolve_key", return_value=("test-key", "gemini-test", "site")),
		mock.patch.object(ai, "_generate", new=fake),
	):
		out = copilot.copilot("غير الألوان لأخضر داكن وحط عنوان فوق", board)
	path = frappe.get_site_path("private", "copilot_proposal.json")
	with open(path, "w") as f:
		json.dump(out, f, ensure_ascii=False)
	print(path)
	print(json.dumps({"reply": out["reply"], "changes": out["changes"], "widgets": len(out["proposal"]["widgets"])}, ensure_ascii=False))
