# Copyright (c) 2026, Lumen and contributors
# Dev check: render a dashboard to PDF and write it where it can be inspected.
# bench --site <site> execute lumen_reports.dev.test_pdf.render --kwargs "{'slug': 'retail-sales', 'lang': 'ar'}"

import json
import os

import frappe

from lumen_reports import api, report

OUT = "/tmp/lumen_pdf"


def render(slug="retail-sales", lang="en", paper="A4", summary=0):
	frappe.set_user("Administrator")
	os.makedirs(OUT, exist_ok=True)
	doc = api._get_dashboard_doc(slug)
	options = {"lang": lang, "paper": paper, "summary": bool(int(summary))}
	pdf = report.render_pdf(doc, options)
	path = os.path.join(OUT, f"{slug}-{lang}.pdf")
	with open(path, "wb") as f:
		f.write(pdf)
	with open(os.path.join(OUT, f"{slug}-{lang}.html"), "w") as f:
		f.write(report.render_html(doc, options))
	print(json.dumps({"pdf": path, "bytes": len(pdf)}))


def blocked_fetch():
	"""The renderer must refuse anything but bundled fonts and public files."""
	from weasyprint.urls import URLFetchingError

	results = {}
	for url in (
		"http://169.254.169.254/latest/meta-data/",
		"http://localhost:8000/api/method/frappe.auth.get_logged_user",
		"file:///etc/passwd",
		"file://" + os.path.realpath(frappe.get_site_path("site_config.json")),
		"file://" + os.path.realpath(frappe.get_site_path("public", "files")) + "/../../site_config.json",
	):
		try:
			report._safe_fetcher(url)
			results[url[-60:]] = "FETCHED"
		except URLFetchingError:
			results[url[-60:]] = "blocked"
	font = os.path.join(report._font_dir(), "plus-jakarta-sans-latin-400-normal.woff2")
	try:
		report._safe_fetcher("file://" + font)
		results["bundled font"] = "allowed"
	except URLFetchingError:
		results["bundled font"] = "BLOCKED"
	print(json.dumps(results, indent=1))
	return results
