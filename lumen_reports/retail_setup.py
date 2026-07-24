# Development helper: stand up a retail ERPNext company + demo data on a site
# whose ERPNext setup wizard was never run. Replicates the wizard's ERPNext
# stage step by step (fixtures -> fiscal year -> company -> defaults -> demo).
# Run with: bench --site <site> execute lumen_reports.retail_setup.run

import frappe
from frappe.utils import getdate


COMPANY_NAME = "Lumen Retail"
COMPANY_ABBR = "LR"
CURRENCY = "USD"
COUNTRY = "United States"


def ensure_fixtures():
	"""Baseline ERPNext records the wizard normally seeds: Warehouse Types,
	UOMs, item groups, roles, etc. Company creation depends on these."""
	if frappe.db.exists("Warehouse Type", "Transit"):
		return "already installed"
	from erpnext.setup.setup_wizard.operations import install_fixtures

	install_fixtures.install(COUNTRY)
	frappe.db.commit()
	return "installed"


def ensure_fiscal_year():
	"""Demo transactions need a Fiscal Year covering today."""
	today = getdate()
	existing = frappe.db.sql(
		"""select name from `tabFiscal Year`
		where year_start_date <= %s and year_end_date >= %s limit 1""",
		(today, today),
	)
	if existing:
		return existing[0][0]

	year = today.year
	fy = frappe.get_doc(
		{
			"doctype": "Fiscal Year",
			"year": str(year),
			"year_start_date": f"{year}-01-01",
			"year_end_date": f"{year}-12-31",
		}
	).insert(ignore_permissions=True)
	return fy.name


def ensure_company():
	if frappe.db.exists("Company", COMPANY_NAME):
		return COMPANY_NAME

	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": COMPANY_NAME,
			"abbr": COMPANY_ABBR,
			"default_currency": CURRENCY,
			"country": COUNTRY,
			"enable_perpetual_inventory": 1,
			"chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": "Standard",
			"create_chart_of_accounts_based_on": "Standard Template",
		}
	)
	company.insert(ignore_permissions=True)
	frappe.db.commit()
	return company.name


def ensure_defaults():
	"""Price lists, global defaults, stock settings, bank account."""
	from erpnext.setup.setup_wizard.operations import install_fixtures

	args = frappe._dict(
		{
			"company_name": COMPANY_NAME,
			"currency": CURRENCY,
			"country": COUNTRY,
			"bank_account": "Cash",
		}
	)
	install_fixtures.install_defaults(args)
	frappe.db.commit()
	return "ok"


def _generate_demo():
	"""Run ERPNext's demo generator, patching its record creator to build
	each master via new_doc() instead of get_doc(dict). The demo master JSON
	omits mandatory fields that carry field/global defaults (Item.stock_uom,
	Customer.customer_type, ...); new_doc() applies those defaults, get_doc()
	does not."""
	from erpnext.setup import demo

	original_record = demo.create_demo_record
	original_txn = demo.create_transaction

	def patched_record(record):
		record = dict(record)
		doctype = record.pop("doctype")
		doc = frappe.new_doc(doctype)
		doc.update(record)
		doc.insert(ignore_permissions=True)

	def patched_transaction(record, company, start_date):
		document_type = record.get("doctype")
		warehouse = demo.get_warehouse(company)
		if document_type == "Purchase Order":
			posting_date = demo.get_random_date(start_date, 1, 25)
		else:
			posting_date = demo.get_random_date(start_date, 31, 350)

		record = dict(record)
		record.update(
			{
				"company": company,
				"set_posting_time": 1,
				"transaction_date": posting_date,
				"schedule_date": posting_date,
				"delivery_date": posting_date,
				"set_warehouse": warehouse,
			}
		)
		doctype = record.pop("doctype")
		doc = frappe.new_doc(doctype)
		doc.update(record)
		doc.save(ignore_permissions=True)
		doc.submit()

	demo.create_demo_record = patched_record
	demo.create_transaction = patched_transaction
	try:
		demo.setup_demo_data()
	finally:
		demo.create_demo_record = original_record
		demo.create_transaction = original_txn


def last_error():
	rows = frappe.get_all(
		"Error Log", fields=["error"], order_by="creation desc", limit_page_length=1
	)
	if not rows:
		return "no errors"
	return rows[0].error[-2000:]


DEMO_COMPANY = "Lumen Retail (Demo)"
TERRITORIES = ["North", "South", "East", "West"]
RETAIL_CUSTOMERS = [
	"Aurora Boutique",
	"Metro Electronics",
	"Sunrise Grocers",
	"Peak Outfitters",
	"Urban Threads",
	"Coastal Cafe Supplies",
	"Nimbus Tech",
	"Golden Leaf Books",
	"Velocity Sports",
	"Harbor Home Goods",
	"Bright Bazaar",
	"Summit Gadgets",
]


def _ensure_territories():
	import random

	for t in TERRITORIES:
		if not frappe.db.exists("Territory", t):
			frappe.get_doc(
				{
					"doctype": "Territory",
					"territory_name": t,
					"parent_territory": "All Territories",
					"is_group": 0,
				}
			).insert(ignore_permissions=True)


def _ensure_customers():
	import random

	for name in RETAIL_CUSTOMERS:
		if not frappe.db.exists("Customer", name):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": name,
					"customer_type": "Company",
					"customer_group": "Demo Customer Group",
					"territory": random.choice(TERRITORIES),
				}
			).insert(ignore_permissions=True)
	# give the original demo customers a territory too
	for name in frappe.get_all("Customer", filters={"territory": ["in", [None, ""]]}, pluck="name"):
		frappe.db.set_value("Customer", name, "territory", random.choice(TERRITORIES))


def enrich(n=180):
	"""Add retail customers + a year of Sales Invoices so dashboards have shape.
	Billing-only invoices (update_stock=0) to avoid stock-ledger constraints."""
	import random

	from frappe.utils import add_days, getdate, nowdate
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	random.seed(7)
	frappe.flags.in_import = True

	_ensure_territories()
	_ensure_customers()

	items = frappe.get_all(
		"Item", filters={"item_group": "Demo Item Group"}, fields=["item_code", "valuation_rate"]
	)
	customers = frappe.get_all("Customer", pluck="name")
	start = getdate("2026-01-01")
	today = getdate(nowdate())
	span = (today - start).days

	created = 0
	paid = 0
	for _i in range(n):
		si = frappe.new_doc("Sales Invoice")
		si.company = DEMO_COMPANY
		si.customer = random.choice(customers)
		si.set_posting_time = 1
		si.posting_date = add_days(start, random.randint(0, span))
		si.due_date = add_days(si.posting_date, 30)
		si.update_stock = 0
		for _line in range(random.randint(1, 3)):
			it = random.choice(items)
			si.append(
				"items",
				{
					"item_code": it.item_code,
					"qty": random.randint(1, 5),
					"rate": round((it.valuation_rate or 100) * random.uniform(1.3, 1.8), 2),
				},
			)
		si.insert(ignore_permissions=True)
		si.submit()
		created += 1

		# pay ~65% so Paid / Unpaid / Overdue statuses all appear
		if random.random() < 0.65:
			try:
				pe = get_payment_entry("Sales Invoice", si.name)
				pay_date = add_days(si.posting_date, random.randint(1, 20))
				pe.posting_date = pay_date if getdate(pay_date) <= today else today
				pe.reference_no = si.name
				pe.reference_date = pe.posting_date
				pe.submit()
				paid += 1
			except Exception:
				frappe.clear_last_message()

		if created % 40 == 0:
			frappe.db.commit()

	frappe.db.commit()
	return {
		"invoices_created": created,
		"payments_created": paid,
		"total_sales_invoices": frappe.db.count("Sales Invoice"),
		"customers": frappe.db.count("Customer"),
	}


BRANDS = ["Nimbus", "Vertex", "Lumina", "Terra"]
ITEM_GROUPS = ["Electronics", "Apparel", "Home & Kitchen", "Books & Media"]
# SKU -> (item_group, brand)
ITEM_ATTRS = {
	"SKU001": ("Apparel", "Terra"),
	"SKU002": ("Electronics", "Vertex"),
	"SKU003": ("Books & Media", "Lumina"),
	"SKU004": ("Electronics", "Vertex"),
	"SKU005": ("Apparel", "Terra"),
	"SKU006": ("Home & Kitchen", "Lumina"),
	"SKU007": ("Electronics", "Nimbus"),
	"SKU008": ("Apparel", "Terra"),
	"SKU009": ("Electronics", "Nimbus"),
	"SKU010": ("Electronics", "Vertex"),
}


def enrich_items():
	"""Give the demo SKUs brands and real item groups so related-field
	reporting (revenue by brand / item group) has shape. The report engine
	joins Item live, so historical invoice lines attribute correctly."""
	for b in BRANDS:
		if not frappe.db.exists("Brand", b):
			frappe.get_doc({"doctype": "Brand", "brand": b}).insert(ignore_permissions=True)

	for g in ITEM_GROUPS:
		if not frappe.db.exists("Item Group", g):
			frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": g,
					"parent_item_group": "All Item Groups",
					"is_group": 0,
				}
			).insert(ignore_permissions=True)

	updated = 0
	for sku, (group, brand) in ITEM_ATTRS.items():
		if not frappe.db.exists("Item", sku):
			continue
		frappe.db.set_value("Item", sku, {"item_group": group, "brand": brand})
		updated += 1
	frappe.db.commit()
	return {"brands": len(BRANDS), "item_groups": len(ITEM_GROUPS), "items_updated": updated}


SALES_PEOPLE = ["Ahmed Al-Rashid", "Sara Hassan", "Khalid Omar", "Noura Salem"]


def add_sales_team():
	"""Create demo sales persons and assign one to every demo invoice, so
	salesperson-performance analysis has real shape."""
	import random

	random.seed(23)
	if not frappe.db.exists("Sales Person", "All Sales Persons"):
		frappe.get_doc(
			{"doctype": "Sales Person", "sales_person_name": "All Sales Persons", "is_group": 1}
		).insert(ignore_permissions=True)
	for name in SALES_PEOPLE:
		if not frappe.db.exists("Sales Person", name):
			frappe.get_doc(
				{
					"doctype": "Sales Person",
					"sales_person_name": name,
					"parent_sales_person": "All Sales Persons",
					"is_group": 0,
				}
			).insert(ignore_permissions=True)

	invoices = frappe.get_all(
		"Sales Invoice", filters={"company": DEMO_COMPANY}, fields=["name", "net_total"]
	)
	added = 0
	for inv in invoices:
		if frappe.db.exists("Sales Team", {"parent": inv.name, "parenttype": "Sales Invoice"}):
			continue
		row = frappe.new_doc("Sales Team")
		row.update(
			{
				"parent": inv.name,
				"parenttype": "Sales Invoice",
				"parentfield": "sales_team",
				"idx": 1,
				"sales_person": random.choice(SALES_PEOPLE),
				"allocated_percentage": 100,
				"allocated_amount": inv.net_total,
			}
		)
		row.db_insert()
		added += 1
	# child rows must mirror the submitted parent's docstatus
	frappe.db.sql(
		"""update `tabSales Team` st join `tabSales Invoice` si on si.name = st.parent
		set st.docstatus = si.docstatus
		where st.parenttype = 'Sales Invoice' and si.company = %s""",
		(DEMO_COMPANY,),
	)
	frappe.db.commit()
	frappe.cache.delete_keys("lumen_res|Sales Invoice|")
	return {"sales_people": len(SALES_PEOPLE), "invoices_assigned": added}


def scatter_transaction_hours():
	"""Give demo invoices realistic in-store times (10:00-22:00, evening peak)
	so hour-of-day (peak hours) analysis has shape. Sets creation + posting_time."""
	import random

	random.seed(11)
	rows = frappe.get_all(
		"Sales Invoice", filters={"company": DEMO_COMPANY}, fields=["name", "posting_date"]
	)
	for row in rows:
		# weighted: evenings busiest, like a real shop
		hour = random.choices(
			list(range(10, 23)),
			weights=[2, 3, 4, 4, 3, 3, 4, 6, 8, 9, 8, 5, 2],
		)[0]
		minute, second = random.randint(0, 59), random.randint(0, 59)
		time_str = f"{hour:02d}:{minute:02d}:{second:02d}"
		frappe.db.sql(
			"""update `tabSales Invoice`
			set creation = timestamp(posting_date, %s), posting_time = %s
			where name = %s""",
			(time_str, time_str, row.name),
		)
	frappe.db.commit()
	frappe.cache.delete_keys("lumen_res|Sales Invoice|")
	return {"updated": len(rows)}


def backfill_territory():
	"""The original ERPNext demo invoices snapshotted an empty territory.
	Backfill from each invoice's customer so the territory breakdown is clean."""
	fixed = 0
	rows = frappe.get_all(
		"Sales Invoice",
		filters={"territory": ["in", [None, ""]]},
		fields=["name", "customer"],
	)
	for row in rows:
		territory = frappe.db.get_value("Customer", row.customer, "territory")
		if territory:
			frappe.db.set_value("Sales Invoice", row.name, "territory", territory, update_modified=False)
			fixed += 1
	frappe.db.commit()
	return {"backfilled": fixed}


def counts():
	demo_company = frappe.db.get_single_value("Global Defaults", "demo_company")
	doctypes = [
		"Company",
		"Item",
		"Customer",
		"Supplier",
		"Sales Order",
		"Sales Invoice",
		"Purchase Order",
		"Purchase Invoice",
		"Payment Entry",
	]
	return {
		"demo_company": demo_company,
		"counts": {dt: frappe.db.count(dt) for dt in doctypes},
	}


def run():
	frappe.flags.in_import = True
	steps = {}
	steps["fixtures"] = ensure_fixtures()
	steps["fiscal_year"] = ensure_fiscal_year()
	steps["company"] = ensure_company()
	steps["defaults"] = ensure_defaults()

	# generate retail demo data (items, customers, suppliers, sales/purchase
	# orders -> invoices) into a "<Company> (Demo)" company
	if frappe.db.get_single_value("Global Defaults", "demo_company"):
		steps["demo"] = "already generated"
	else:
		_generate_demo()
		frappe.db.commit()
		steps["demo_company"] = frappe.db.get_single_value("Global Defaults", "demo_company")

	return steps
