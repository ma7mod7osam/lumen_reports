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


def expressions():
	"""Direct engine tests for computed metrics."""
	from lumen_reports import query_engine

	base = {"doctype": "Sales Invoice", "filters": [["docstatus", "=", 1]]}
	out = {}
	# avg payment terms in days (enriched invoices: due = posting + 30)
	out["avg_terms_days"] = query_engine.execute(
		{**base, "aggregate": {"function": "avg", "expr": {"op": "diff_days", "args": ["posting_date", "due_date"]}, "format": "days"}}
	)
	# avg transaction time-of-day (hours since midnight; evening-weighted demo)
	out["avg_txn_clock"] = query_engine.execute(
		{**base, "aggregate": {"function": "avg", "expr": {"op": "clock", "args": ["creation"]}, "format": "clock"}}
	)
	# avg unpaid ratio = outstanding / grand_total
	out["avg_unpaid_ratio"] = query_engine.execute(
		{**base, "aggregate": {"function": "avg", "expr": {"op": "div", "args": ["outstanding_amount", "grand_total"]}, "format": "percent"}}
	)
	# grouped: avg office-hours-style diff per territory (creation->modified is
	# not meaningful data-wise, but proves diff_hours + group_by compose)
	out["diff_hours_by_territory"] = query_engine.execute(
		{
			**base,
			"aggregate": {"function": "avg", "expr": {"op": "diff_hours", "args": ["posting_date", "due_date"]}, "format": "hours"},
			"group_by": {"field": "territory"},
		}
	)
	return out


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
		elif result.get("result_type") == "matrix":
			summary["rows"] = result.get("rows")
			summary["cols"] = len(result.get("cols") or [])
		elif result.get("result_type") == "points":
			summary["axes"] = [result.get("x_label"), result.get("y_label")]
			summary["points"] = len(result.get("points") or [])
			summary["first"] = (result.get("points") or [])[:2]
		if w.get("style"):
			summary["style"] = w["style"]
		out["widgets"].append(summary)
	return out


def new_charts():
	"""Live ask expecting Heatmap / Gauge / Horizontal Bar forms."""
	import frappe

	frappe.set_user("Administrator")
	try:
		ans = ai.ask_ai("when is the shop busiest? show a heatmap of sales invoices by day and hour")
		out = {"clarify": ans.get("clarify"), "widgets": []}
		for entry in ans.get("widgets") or []:
			w = entry["widget"]
			r = entry.get("result") or {}
			out["widgets"].append(
				{
					"type": w["widget_type"],
					"title": w["title"],
					"empty": entry.get("empty"),
					"kind": r.get("result_type"),
					"rows": len(r.get("rows") or []) if r.get("result_type") == "matrix" else None,
					"cols": len(r.get("cols") or []) if r.get("result_type") == "matrix" else None,
				}
			)
		return out
	except Exception:
		return {"traceback": traceback.format_exc()[-1500:]}


def new_charts_raw():
	"""Same live ask, dumping the raw first-widget payload."""
	import frappe

	frappe.set_user("Administrator")
	try:
		ans = ai.ask_ai("when is the shop busiest? show me a heatmap of activity by day and hour")
		entries = ans.get("widgets") or []
		if not entries:
			return {"clarify": ans.get("clarify"), "note": "no widgets"}
		e = entries[0]
		r = e.get("result") or {}
		return {
			"query": e["widget"].get("query"),
			"result_keys": sorted(r.keys()),
			"rows": r.get("rows"),
			"cols": r.get("cols"),
			"first_values": (r.get("values") or [[]])[0][:6],
		}
	except Exception:
		return {"traceback": traceback.format_exc()[-1500:]}


def scatter():
	"""Direct engine test for the points (bubble scatter) shape."""
	from lumen_reports import query_engine

	out = {}
	# price vs volume per item, bubbles sized by number of invoice lines
	try:
		r = query_engine.execute(
			{
				"doctype": "Sales Invoice Item",
				"parent_doctype": "Sales Invoice",
				"filters": [["docstatus", "=", 1]],
				"group_by": {"field": "item_code"},
				"aggregate": {"function": "avg", "field": "rate"},
				"aggregate_y": {"function": "sum", "field": "qty"},
				"aggregate_size": {"function": "count"},
			}
		)
		out["price_vs_volume"] = {
			"type": r.get("result_type"),
			"x_label": r.get("x_label"),
			"y_label": r.get("y_label"),
			"n": len(r.get("points") or []),
			"first3": (r.get("points") or [])[:3],
		}
	except Exception:
		out["price_vs_volume"] = traceback.format_exc()[-600:]

	# guard rails
	for name, q in {
		"no_group_by": {
			"doctype": "Sales Invoice",
			"aggregate": {"function": "count"},
			"aggregate_y": {"function": "sum", "field": "grand_total"},
		},
		"size_without_y": {
			"doctype": "Sales Invoice",
			"group_by": {"field": "status"},
			"aggregate": {"function": "count"},
			"aggregate_size": {"function": "count"},
		},
		"with_group_by2": {
			"doctype": "Sales Invoice",
			"group_by": {"field": "status"},
			"group_by2": {"field": "territory"},
			"aggregate": {"function": "count"},
			"aggregate_y": {"function": "sum", "field": "grand_total"},
		},
	}.items():
		try:
			query_engine.execute(q)
			out[name] = "NO ERROR (bad)"
		except Exception as e:
			import frappe

			frappe.clear_last_message()
			out[name] = str(e)[:90]
	return out


def tree():
	"""Direct engine test for the hierarchical tree report."""
	from lumen_reports import query_engine

	try:
		r = query_engine.execute(
			{
				"doctype": "Sales Invoice Item",
				"parent_doctype": "Sales Invoice",
				"filters": [["docstatus", "=", 1]],
				"shape": "tree",
				"aggregate": {"function": "sum", "field": "amount"},
				"group_by": {"field": "item_group", "via": {"link_field": "item_code", "doctype": "Item"}},
				"group_by2": {"field": "brand", "via": {"link_field": "item_code", "doctype": "Item"}},
				"group_by3": {"field": "item_code"},
			}
		)
		first = (r.get("nodes") or [{}])[0]
		return {
			"kind": r.get("result_type"),
			"levels": r.get("levels"),
			"total": r.get("total"),
			"roots": [n["label"] for n in r.get("nodes") or []],
			"first_label": first.get("label"),
			"first_share": round(first.get("share", 0), 3),
			"first_children": [
				{"label": c["label"], "value": c["value"], "kids": len(c.get("children") or [])}
				for c in (first.get("children") or [])
			],
		}
	except Exception:
		return {"traceback": traceback.format_exc()[-900:]}


def asks(prompt="how are my sales doing?"):
	"""Does the AI clarify / surface its assumptions as refinements?"""
	try:
		a = ai.ask_ai(prompt)
		return {
			"clarify": a.get("clarify"),
			"options": a.get("options"),
			"questions": a.get("questions"),
			"types": [w["widget"]["widget_type"] for w in (a.get("widgets") or [])],
			"explanation": (a.get("explanation") or "")[:200],
		}
	except Exception:
		return {"traceback": traceback.format_exc()[-700:]}


def licensing_check():
	"""Verify the entitlement logic without a Frappe Cloud subscription."""
	import frappe

	from lumen_reports import licensing

	out = {}
	frappe.cache().delete_value(licensing.CACHE_KEY)
	frappe.cache().delete_value(f"{licensing.CACHE_KEY}:last_good")

	# this bench has no sk_ key -> unlicensed, but must never block
	out["no_key"] = licensing.get_status(force=True)
	out["is_licensed_when_unlicensed"] = licensing.is_licensed()
	out["notice_in_developer_mode"] = licensing.notice()

	# simulate Frappe Cloud answers
	real_fetch = licensing._fetch
	try:
		licensing._fetch = lambda key: {"enabled": 1, "plan": "Pro", "site": "acme.frappe.cloud"}
		frappe.conf[licensing.CONFIG_KEY] = "test-secret"
		out["active"] = licensing.get_status(force=True)

		licensing._fetch = lambda key: {"enabled": 0, "plan": "Pro", "site": "acme.frappe.cloud"}
		out["disabled"] = licensing.get_status(force=True)
		out["is_licensed_when_expired"] = licensing.is_licensed()

		# outage after a good check -> fall back to last good, stay working
		def boom(key):
			raise RuntimeError("frappe cloud unreachable")

		licensing._fetch = lambda key: {"enabled": 1, "plan": "Pro", "site": "acme.frappe.cloud"}
		licensing.get_status(force=True)
		licensing._fetch = boom
		out["outage"] = licensing.get_status(force=True)
		out["is_licensed_during_outage"] = licensing.is_licensed()
	finally:
		licensing._fetch = real_fetch
		frappe.conf.pop(licensing.CONFIG_KEY, None)
		frappe.cache().delete_value(licensing.CACHE_KEY)
		frappe.cache().delete_value(f"{licensing.CACHE_KEY}:last_good")
	return out


def licensing_debug():
	import frappe

	from lumen_reports import licensing

	steps = []
	frappe.cache().delete_value(licensing.CACHE_KEY)
	frappe.cache().delete_value(f"{licensing.CACHE_KEY}:last_good")
	real = licensing._fetch
	try:
		frappe.conf[licensing.CONFIG_KEY] = "test-secret"
		licensing._fetch = lambda key: {"enabled": 1, "plan": "Pro", "site": "acme"}
		s1 = licensing.get_status(force=True)
		steps.append({"after_good_fetch": s1})
		steps.append({"cache_main": frappe.cache().get_value(licensing.CACHE_KEY)})
		steps.append({"cache_last_good": frappe.cache().get_value(f"{licensing.CACHE_KEY}:last_good")})

		def boom(key):
			raise RuntimeError("unreachable")

		licensing._fetch = boom
		steps.append({"forced_during_outage": licensing.get_status(force=True)})
		steps.append({"unforced_during_outage": licensing.get_status()})
		steps.append({"is_licensed": licensing.is_licensed()})
	finally:
		licensing._fetch = real
		frappe.conf.pop(licensing.CONFIG_KEY, None)
	return steps
