# Development helper: exercise every widget on the demo dashboard.
# Run with: bench --site <site> execute lumen_reports.dev_test.run

from lumen_reports import api


def run():
	out = {}
	dashboard = api.get_dashboard("demo")
	for widget in dashboard["widgets"]:
		try:
			result = api.run_widget("demo", widget["widget_id"])
			if result["result_type"] == "rows":
				summary = {"rows": len(result["rows"]), "total": result["total"]}
			elif result["result_type"] == "series":
				summary = {"labels": result["labels"][:6], "values": result["values"][:6]}
			else:
				summary = {"value": result["value"]}
			out[widget["widget_id"]] = summary
		except Exception as e:
			out[widget["widget_id"]] = f"FAIL {type(e).__name__}: {e}"
	out["filtered_check"] = api.run_widget("demo", "by_status", {"priority": "High"})
	return out
