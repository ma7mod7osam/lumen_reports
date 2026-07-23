<div align="center">

# Lumen Reports

**Beautiful, fast, live-updating reports and dashboards for Frappe / ERPNext.**

Build gorgeous dashboards with a no-code builder, ask your data questions in plain
English, and watch everything update in real time.

</div>

---

## Why Lumen

Frappe ships capable but plain reporting. Lumen is a standalone Vue 3 single-page app
(served at `/lumen`) that makes operational reporting genuinely pleasant:

- **A designed look, not default charts** — a cohesive design system (Plus Jakarta Sans +
  IBM Plex Mono, a validated color palette), light **and** dark themes, and charts that
  re-theme instantly.
- **Live updates** — when an underlying document changes, the affected widgets refresh
  in place over websockets. No refresh button.
- **No-code builder** — pick a data source, a measure and a breakdown; drag/resize widgets
  on a grid. Everything you can point at, you can chart.
- **Permission-safe by construction** — every widget query runs through Frappe's
  permission layer, so users only ever see data their roles allow.

## Features

- **Widget types** — number cards, bar / line / area / pie / donut charts, and tables.
- **Dashboard filters** — Select, Link (searchable), Checkbox, and **line-item** filters,
  all combined with AND. Filter the whole board from one bar.
- **Cross-filtering** — click any chart segment to focus every other widget; stack
  multiple dimensions at once.
- **Related fields (one-hop joins)** — report on attributes pulled *live* from linked
  master records (e.g. Sales Invoice line -> Item -> **Brand / Item Group**), computed at
  line-item grain without double-counting.
- **Ask AI** *(bring-your-own Gemini key)* — describe a report in plain English and Lumen
  generates validated widgets, or a whole dashboard, that you can pin permanently. The AI
  also lives **inside the builder**: an "Ask AI" button to add widgets and a sparkle button
  on each widget to modify it ("make it a donut", "only paid invoices").
- **Result caching** with automatic doc-event invalidation, **CSV / SVG export**, and
  **publish-based visibility** (users see published dashboards plus their own drafts).
- **Responsive** — the viewer is built for phones as well as desktops.

## Requirements

- Frappe Framework **v15**
- Node 18+ and Yarn (to build the frontend)

## Installation

From your bench directory:

```bash
bench get-app https://github.com/ma7mod7osam/lumen_reports
bench --site your-site.localhost install-app lumen_reports

# build the SPA (served at /lumen)
cd apps/lumen_reports/frontend
yarn install
yarn build
```

Then open `https://your-site.localhost/lumen`.

### Frontend development

```bash
cd apps/lumen_reports/frontend
yarn dev      # Vite dev server with HMR, proxied to your bench
yarn build    # production build -> served at /lumen
```

## Ask AI setup (optional)

The AI features run on **Google Gemini**, using a key you provide — cost stays with you.

1. Open `/lumen/ask` in the app.
2. Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   (no credit card needed; a step-by-step guide is on the page).
3. Paste it as your **personal key**, or — as a System Manager — set a **site-wide key**
   shared by everyone (a personal key always takes priority).

Keys are stored **encrypted** in the site database and never leave the server. The model
only ever emits Lumen's query specification, which is executed through the same
permission-aware engine as every other widget — the AI never touches the database directly.

## Architecture

| Layer | What it does |
|---|---|
| `Lumen Dashboard` / `Lumen Widget` doctypes | Store dashboards, widget query specs (JSON), layout and filters |
| `query_engine.py` | Compiles a JSON query to `frappe.get_list` — role/user permissions always apply |
| `report_engine.py` | `frappe.qb` join engine for line-item grain + one-hop related fields |
| `realtime.py` | Doctype->dashboard registry; publishes invalidation events on doc change |
| `api.py` | Dashboard + widget + builder endpoints |
| `ai.py` | Ask AI orchestration (Gemini), validated through the query engines |
| `frontend/` | Vue 3 + Vite + frappe-ui + ECharts SPA served at `/lumen` |

## Optional: demo data

The repo includes helpers to spin up a retail demo (ERPNext required) — brands, item
groups, ~185 sales invoices, and a ready-made dashboard:

```bash
bench --site your-site.localhost execute lumen_reports.retail_setup.run
bench --site your-site.localhost execute lumen_reports.retail_setup.enrich
bench --site your-site.localhost execute lumen_reports.retail_setup.enrich_items
bench --site your-site.localhost execute lumen_reports.retail_dashboard.run
```

## License

MIT
