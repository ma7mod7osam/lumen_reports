# Dev helper: build a dashboard holding one widget of every chart type, so the
# renderers can be eyeballed (and DOM-checked) against real data in one place.
# bench --site <site> execute lumen_reports.dev.gallery.run

import frappe

SLUG = "chart-gallery"

SUBMITTED = [["docstatus", "=", 1]]
LINE_BASE = {
	"doctype": "Sales Invoice Item",
	"parent_doctype": "Sales Invoice",
	"filters": SUBMITTED,
}


def widgets():
	monthly = {
		"doctype": "Sales Invoice",
		"filters": SUBMITTED,
		"aggregate": {"function": "sum", "field": "grand_total"},
		"group_by": {"field": "posting_date", "time_grain": "month"},
	}
	return [
		{
			"title": "Revenue trend",
			"widget_type": "Sparkline",
			"query": monthly,
			"style": {"accent": 0},
		},
		{
			"title": "How the year built up",
			"widget_type": "Waterfall",
			"query": monthly,
			"style": {"accent": 1},
		},
		{
			"title": "Revenue share by territory",
			"widget_type": "Rings",
			"query": {
				"doctype": "Sales Invoice",
				"filters": SUBMITTED,
				"aggregate": {"function": "sum", "field": "grand_total"},
				"group_by": {"field": "territory"},
			},
		},
		{
			"title": "Category profile",
			"widget_type": "Radar",
			"query": {
				**LINE_BASE,
				"aggregate": {"function": "sum", "field": "amount"},
				"group_by": {"field": "item_group", "via": {"link_field": "item_code", "doctype": "Item"}},
			},
			"style": {"accent": 3},
		},
		{
			"title": "Category profile per territory",
			"widget_type": "Radar",
			"query": {
				**LINE_BASE,
				"aggregate": {"function": "sum", "field": "amount"},
				"group_by": {"field": "item_group", "via": {"link_field": "item_code", "doctype": "Item"}},
				"group_by2": {"field": "territory", "via": {"link_field": "parent", "doctype": "Sales Invoice"}},
			},
		},
		{
			"title": "Price vs volume",
			"widget_type": "Scatter",
			"query": {
				**LINE_BASE,
				"group_by": {"field": "item_code"},
				"aggregate": {"function": "avg", "field": "rate"},
				"aggregate_y": {"function": "sum", "field": "qty"},
				"aggregate_size": {"function": "count"},
			},
			"style": {"accent": 2},
		},
		{
			"title": "Monthly sales by territory",
			"widget_type": "Bar Chart",
			"query": {
				"doctype": "Sales Invoice",
				"filters": SUBMITTED,
				"aggregate": {"function": "sum", "field": "grand_total"},
				"group_by": {"field": "posting_date", "time_grain": "month"},
				"group_by2": {"field": "territory"},
			},
		},
		{
			"title": "Sales mix by territory",
			"widget_type": "Stacked Bar",
			"query": {
				"doctype": "Sales Invoice",
				"filters": SUBMITTED,
				"aggregate": {"function": "sum", "field": "grand_total"},
				"group_by": {"field": "posting_date", "time_grain": "month"},
				"group_by2": {"field": "territory"},
			},
		},
		{
			"title": "Territory attainment",
			"widget_type": "Progress Bars",
			"query": {
				"doctype": "Sales Invoice",
				"filters": SUBMITTED,
				"aggregate": {"function": "sum", "field": "grand_total"},
				"group_by": {"field": "territory"},
			},
			"style": {"target": 400000},
		},
		{
			"title": "Sales breakdown",
			"widget_type": "Tree Report",
			"query": {
				**LINE_BASE,
				"shape": "tree",
				"aggregate": {"function": "sum", "field": "amount"},
				"group_by": {"field": "item_group", "via": {"link_field": "item_code", "doctype": "Item"}},
				"group_by2": {"field": "brand", "via": {"link_field": "item_code", "doctype": "Item"}},
				"group_by3": {"field": "item_code"},
			},
		},
		{
			"title": "Busiest times",
			"widget_type": "Heatmap",
			"query": {
				"doctype": "Sales Invoice",
				"filters": SUBMITTED,
				"aggregate": {"function": "count"},
				"group_by": {"field": "creation", "time_grain": "weekday"},
				"group_by2": {"field": "creation", "time_grain": "hour"},
			},
		},
	]


def run():
	"""(Re)create the gallery dashboard from scratch."""
	import traceback

	try:
		return _run()
	except Exception:
		return {"traceback": traceback.format_exc()[-1500:]}


def _run():
	if frappe.db.exists("Lumen Dashboard", SLUG):
		frappe.delete_doc("Lumen Dashboard", SLUG, force=True)

	doc = frappe.new_doc("Lumen Dashboard")
	doc.dashboard_title = "Chart gallery"
	doc.route_slug = SLUG
	doc.is_published = 1
	doc.auto_refresh = 1

	layout = []
	x = y = 0
	for i, w in enumerate(widgets()):
		widget_id = f"g{i}"
		doc.append(
			"widgets",
			{
				"widget_id": widget_id,
				"title": w["title"],
				"widget_type": w["widget_type"],
				"query_json": frappe.as_json(w["query"]),
				"style_json": frappe.as_json(w.get("style") or {}),
			},
		)
		width = 12 if w["widget_type"] in ("Heatmap", "Tree Report") else 6 if "Bar" in w["widget_type"] else 4
		if x + width > 12:
			x, y = 0, y + 4
		layout.append({"widget_id": widget_id, "x": x, "y": y, "w": width, "h": 4})
		x += width
		if x >= 12:
			x, y = 0, y + 4

	doc.layout_json = frappe.as_json(layout)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — dev/test helper run by hand via bench execute; commits fixtures so the assertions that follow (which roll back on denial) cannot undo them
	return {"slug": SLUG, "widgets": len(doc.widgets)}


def check():
	"""Run every gallery widget through the engine and report its shape."""
	from lumen_reports import query_engine

	out = []
	for w in widgets():
		row = {"title": w["title"], "type": w["widget_type"]}
		try:
			r = query_engine.execute(w["query"])
			row["kind"] = r.get("result_type")
			if row["kind"] == "series":
				row["n"] = len(r.get("labels") or [])
				row["labels"] = (r.get("labels") or [])[:4]
			elif row["kind"] == "matrix":
				row["rows"] = r.get("rows")
				row["cols"] = len(r.get("cols") or [])
			elif row["kind"] == "points":
				row["n"] = len(r.get("points") or [])
			elif row["kind"] == "tree":
				row["levels"] = r.get("levels")
				row["roots"] = len(r.get("nodes") or [])
		except Exception as e:
			frappe.clear_last_message()
			row["error"] = str(e)[:140]
		out.append(row)
	return out
