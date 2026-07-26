# Dev test: cross-filtering across grains + dashboard filters on line widgets.
# bench --site <site> execute lumen_reports.dev_test_xfilter.run

from lumen_reports import api

BRAND_CLICK = [
	{
		"field": "brand",
		"via": {"link_field": "item_code", "doctype": "Item"},
		"value": "Vertex",
		"source_doctype": "Sales Invoice Item",
		"parent_doctype": "Sales Invoice",
		"sourceId": "by_brand",
	}
]


def run():
	out = {}

	# baseline
	out["revenue_all"] = api.run_widget("retail-sales", "revenue")["value"]

	# brand click -> parent KPI: revenue of invoices involving Vertex items
	out["revenue_involving_vertex"] = api.run_widget(
		"retail-sales", "revenue", cross_filters=BRAND_CLICK
	)["value"]

	# brand click -> line widget (item groups), same grain: only Vertex lines
	ig = api.run_widget("retail-sales", "by_item_group", cross_filters=BRAND_CLICK)
	out["item_groups_for_vertex"] = dict(zip(ig["labels"], ig["values"]))

	# dashboard Item filter -> line brand widget: only that item's brand
	bb = api.run_widget(
		"retail-sales", "by_brand", filter_values={"Sales Invoice Item::item_code": "SKU004"}
	)
	out["brand_for_sku004"] = dict(zip(bb["labels"], bb["values"]))

	# dashboard Item filter -> parent revenue KPI: invoices containing SKU004
	out["revenue_invoices_with_sku004"] = api.run_widget(
		"retail-sales", "revenue", filter_values={"Sales Invoice Item::item_code": "SKU004"}
	)["value"]

	return out
