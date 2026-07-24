# Dev helper: run ask_ai with the stored key and show the real error if any.
# bench --site <site> execute lumen_reports.dev_ask.run --kwargs "{'prompt': '...'}"

import traceback

import requests

from lumen_reports import ai


def models():
	"""List generateContent-capable models available to the stored key."""
	key, _model, source = ai._resolve_key()
	if not key:
		return {"error": "no key configured"}
	response = requests.get(
		"https://generativelanguage.googleapis.com/v1beta/models",
		headers={"x-goog-api-key": key},
		params={"pageSize": 100},
		timeout=30,
	)
	if response.status_code != 200:
		return {"status": response.status_code, "body": ai._scrub(response.text[:400], key)}
	rows = response.json().get("models", [])
	return sorted(
		m["name"].replace("models/", "")
		for m in rows
		if "generateContent" in (m.get("supportedGenerationMethods") or [])
	)


def fix_stored_models():
	"""Move any stored deprecated model names to the floating alias."""
	import frappe

	frappe.db.set_single_value("Lumen AI Site Settings", "model", "gemini-flash-latest")
	frappe.db.sql(
		"update `tabLumen AI Settings` set model = 'gemini-flash-latest' where model like 'gemini-2.%'"
	)
	frappe.db.commit()
	return "ok"


def hour_grain():
	"""Direct engine test: sales by hour of day (peak hours)."""
	from lumen_reports import query_engine

	result = query_engine.execute(
		{
			"doctype": "Sales Invoice",
			"aggregate": {"function": "count"},
			"group_by": {"field": "creation", "time_grain": "hour"},
			"filters": [["docstatus", "=", 1]],
		}
	)
	return dict(zip(result["labels"], result["values"]))


def conversation():
	"""Live two-turn test: initial ask, then a follow-up that relies on history
	and must not recreate existing widgets."""
	try:
		first = ai.ask_ai("revenue by brand")
		titles = [w["widget"]["title"] for w in first["widgets"]]
		second = ai.ask_ai(
			"now also show it by item group, and add a total revenue card",
			history=[
				{"role": "user", "text": "revenue by brand"},
				{"role": "assistant", "text": f"Built: {first['title']}"},
			],
			existing_titles=titles,
		)
		return {
			"first_titles": titles,
			"first_suggestions": first.get("suggestions"),
			"second_titles": [w["widget"]["title"] for w in second["widgets"]],
			"second_recreated_existing": any(
				w["widget"]["title"] in titles for w in second["widgets"]
			),
			"second_suggestions": second.get("suggestions"),
		}
	except Exception:
		return {"error": traceback.format_exc()[-600:]}


def modify(prompt="turn it into a donut chart"):
	"""Live test of modify_ai_widget against the brand widget."""
	widget = {
		"title": "Revenue by Brand",
		"widget_type": "Bar Chart",
		"style": {"tint": "green"},
		"query": {
			"doctype": "Sales Invoice Item",
			"parent_doctype": "Sales Invoice",
			"aggregate": {"function": "sum", "field": "amount"},
			"group_by": {"field": "brand", "via": {"link_field": "item_code", "doctype": "Item"}},
			"filters": [["docstatus", "=", 1]],
		},
	}
	try:
		entry = ai.modify_ai_widget(prompt, widget)
	except Exception:
		return {"error": traceback.format_exc()[-900:]}
	return {
		"explanation": entry.get("explanation"),
		"widget_type": entry["widget"]["widget_type"],
		"style_kept": entry["widget"]["style"],
		"query": entry["widget"]["query"],
		"labels": entry["result"].get("labels"),
	}


def run(prompt="revenue by brand"):
	try:
		answer = ai.ask_ai(prompt)
	except Exception:
		return {"error": traceback.format_exc()[-1200:]}
	if answer.get("clarify"):
		return {"clarify": answer["clarify"]}
	out = {
		"title": answer.get("title"),
		"explanation": answer.get("explanation"),
		"dropped": answer.get("dropped"),
		"widgets": [],
	}
	for entry in answer.get("widgets") or []:
		w, result = entry["widget"], entry["result"]
		summary = {"title": w["title"], "type": w["widget_type"]}
		if result.get("result_type") == "series":
			summary["labels"] = result.get("labels")
			summary["values"] = result.get("values")
		elif result.get("result_type") == "number":
			summary["value"] = result.get("value")
		elif result.get("result_type") == "rows":
			summary["rows"] = len(result.get("rows") or [])
			summary["columns"] = [c.get("label") for c in result.get("columns") or []]
		out["widgets"].append(summary)
	return out
