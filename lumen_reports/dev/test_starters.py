# Copyright (c) 2026, Lumen and contributors
# Dev check: run every starter template's widgets against this site's data.
# bench --site <site> execute lumen_reports.dev.test_starters.run

import frappe

from lumen_reports import query_engine, starters


def run():
	"""Execute every widget of every starter and report what this site can build."""
	offered = {s["id"] for s in starters.list_starters()}
	for s in starters.STARTERS:
		mark = "offered" if s["id"] in offered else "hidden "
		print(f"\n[{mark}] {s['name']}  ({s['doctype']})")
		for w in s["widgets"]:
			if not w["query"]:
				print(f"    ....  {w['title']}  ({w['widget_type']}, no query)")
				continue
			try:
				result = query_engine.execute(w["query"])
				print(f"    ok    {w['title']}  -> {_shape(result)}")
			except Exception as e:
				print(f"    FAIL  {w['title']}  -> {type(e).__name__}: {str(e)[:160]}")


def _shape(result):
	kind = result.get("result_type")
	if kind == "number":
		return f"number {result.get('value')}"
	if kind == "series":
		return f"series {len(result.get('labels') or [])} points"
	if kind == "matrix":
		return f"matrix {len(result.get('rows') or [])}x{len(result.get('cols') or [])}"
	if kind == "rows":
		return f"rows {len(result.get('rows') or [])}"
	if kind == "tree":
		return f"tree {len(result.get('nodes') or [])} nodes"
	if kind == "points":
		return f"points {len(result.get('points') or [])}"
	return str(kind)


def build(starter_id="executive"):
	"""Create a dashboard from a starter and print where it landed."""
	out = starters.create_from_starter(starter_id, title=f"Starter check {starter_id}")
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — CLI helper, not a request path
	print(out)
	return out
