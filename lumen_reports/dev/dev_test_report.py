# Dev test for the join/related-field report engine.
# bench --site <site> execute lumen_reports.dev_test_report.run

import traceback

import frappe

from lumen_reports import query_engine


def _try(fn):
	try:
		return fn()
	except Exception:
		return "ERROR: " + traceback.format_exc().splitlines()[-1]

COMPANY = "Lumen Retail (Demo)"
BASE = [
	["docstatus", "=", 1],
	[{"field": "company", "via": {"link_field": "parent", "doctype": "Sales Invoice"}}, "=", COMPANY],
]


def _si_item(**kw):
	q = {"doctype": "Sales Invoice Item", "parent_doctype": "Sales Invoice", "filters": list(BASE)}
	q.update(kw)
	return q


def run():
	out = {}
	brand_via = {"field": "brand", "via": {"link_field": "item_code", "doctype": "Item"}}
	group_via = {"field": "item_group", "via": {"link_field": "item_code", "doctype": "Item"}}

	out["revenue_by_brand"] = _try(
		lambda: query_engine.execute(
			_si_item(aggregate={"function": "sum", "field": "amount"}, group_by=brand_via)
		)
	)
	out["revenue_by_item_group"] = _try(
		lambda: query_engine.execute(
			_si_item(aggregate={"function": "sum", "field": "amount"}, group_by=group_via)
		)
	)
	out["units_by_brand"] = _try(
		lambda: query_engine.execute(
			_si_item(aggregate={"function": "sum", "field": "qty"}, group_by=brand_via)
		)
	)

	def table_test():
		table = query_engine.execute(
			_si_item(
				fields=[
					"item_code",
					{"field": "item_name", "via": {"link_field": "item_code", "doctype": "Item"}},
					brand_via,
					"amount",
					{"field": "posting_date", "via": {"link_field": "parent", "doctype": "Sales Invoice"}},
				],
				sort={"field": "amount", "order": "desc"},
				limit=3,
			)
		)
		return {
			"columns": [c["label"] for c in table["columns"]],
			"first_row": table["rows"][0] if table["rows"] else None,
			"total": table["total"],
		}

	out["table_sample"] = _try(table_test)

	out["revenue_brand_vertex"] = _try(
		lambda: query_engine.execute(
			_si_item(
				aggregate={"function": "sum", "field": "amount"},
				filters=BASE + [[brand_via, "=", "Vertex"]],
			)
		)
	)

	return out
