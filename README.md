<div align="center">

<img src="lumen_reports/public/logo.svg" width="72" height="72" alt="Lumen Reports" />

# Lumen Reports

**Beautiful, fast, live-updating dashboards and reports for Frappe / ERPNext.**

Build dashboards by dragging, ask your data questions in plain English,
and watch every number keep itself current.

</div>

---

## Why Lumen

Frappe ships capable but plain reporting. Getting a straight answer usually means
exporting to a spreadsheet or waiting on a custom script report.

Lumen is a standalone Vue 3 single-page app served at `/lumen`. It is **not** a BI
suite for analysts — it's an operational dashboard layer for the people who run the
business, built on the doctypes you already have.

- **A designed look, not default charts** — a cohesive design system (Plus Jakarta
  Sans + IBM Plex Mono, a validated palette), light **and** dark themes, and charts
  that re-theme instantly.
- **Live updates** — when an underlying document changes, affected widgets refresh
  in place over websockets. No refresh button.
- **No-code builder** — pick a source, a measure and a breakdown, with a live preview
  as you choose. Drag and resize on a 12-column grid.
- **Permission-safe by construction** — Lumen never runs raw SQL. Every widget stores
  a query definition that the server compiles through Frappe's permission layer,
  checking read access on the base doctype *and* every joined doctype.

## Features

**19 widget types**

| | |
|---|---|
| Trends | Line, Area, Sparkline, Waterfall |
| Comparisons | Bar, Grouped bar, Stacked bar, Ranked bars, Radar |
| Composition | Donut, Pie, Funnel, Radial rings |
| Progress | Number card, Gauge, Progress bars |
| Patterns | Heatmap, Scatter / bubble |
| Detail | Table, Tree report |

- **Ask AI** *(bring-your-own Gemini key)* — describe a report in plain English and
  Lumen generates validated widgets, or a whole dashboard. It asks a clarifying
  question when a request is genuinely ambiguous, and surfaces the assumptions it
  made as one-tap refinements. It also lives **inside the builder**: add widgets, or
  hit the sparkle on any widget to modify it ("make it a donut", "only paid invoices").
- **Form follows data** — the chart type that suits the numbers is chosen by default;
  the variant bar offers only the alternatives that also make sense.
- **Dashboard filters** — Select, Link (searchable), Checkbox and **line-item**
  filters, all combined with AND.
- **Cross-filtering** — click any chart segment to refocus every other widget, across
  document and line-item grain. Dimensions stack, each with a removable chip.
- **Related fields (one-hop joins)** — report on attributes pulled *live* from linked
  masters (Sales Invoice line → Item → **Brand / Item Group**) at line grain, without
  double-counting.
- **Two-dimensional grouping** — a second breakdown turns a chart into grouped bars,
  stacked bars, multi-line, a heatmap or a radar.
- **Tree reports** — drill from category to brand to item, totals rolled up, every row
  showing its share of the whole.
- **Computed metrics** — values that exist in no field: average check-in time, hours
  worked, payment terms in days, outstanding as a percentage of invoiced.
- **Result caching** with automatic doc-event invalidation, **CSV / SVG export**, and
  **publish-based visibility** (users see published dashboards plus their own drafts).
- **Responsive** — built for phones as well as desktops.

## Requirements

- Frappe Framework **v15**
- Works alongside ERPNext, or on any custom app — Lumen reads whatever doctypes exist
- Ask AI is optional and needs your own Google Gemini API key

## Installation

From your bench directory:

```bash
bench get-app https://github.com/ma7mod7osam/lumen_reports
bench --site your-site.localhost install-app lumen_reports
bench build --app lumen_reports
```

Then open `https://your-site.localhost/lumen`.

> The SPA is built from `frontend/` by the root `yarn build` script, which
> `bench build` runs for you. To build it by hand: `yarn build` in the app root.

### Frontend development

```bash
cd apps/lumen_reports/frontend
yarn install
yarn dev      # Vite dev server with HMR, proxied to your bench
yarn build    # production build -> served at /lumen
```

## Ask AI setup (optional)

The AI features run on **Google Gemini**, using a key you provide — the cost stays
with you, and Google's free tier is enough to evaluate it.

1. Open `/lumen/ask` in the app.
2. Get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   (no credit card needed; a step-by-step guide is on the page).
3. Paste it as your **personal key**, or — as a System Manager — set a **site-wide
   key** shared by everyone (a personal key always takes priority).

Keys are stored **encrypted** in the site database, never returned to the browser and
never included in error messages. The model only ever emits Lumen's query
specification, which is executed through the same permission-aware engine as every
other widget — the AI never touches the database directly.

## Architecture

| Layer | What it does |
|---|---|
| `Lumen Dashboard` / `Lumen Widget` doctypes | Dashboards, widget query specs (JSON), layout, filters |
| `query_engine.py` | Compiles a JSON query to `frappe.get_list` — permissions always apply |
| `report_engine.py` | `frappe.qb` engine for line-item grain, one-hop joins, matrices, trees, computed metrics |
| `realtime.py` | Doctype→dashboard registry; publishes invalidation on doc change |
| `api.py` | Dashboard, widget and builder endpoints |
| `ai.py` | Ask AI orchestration (Gemini), validated through the query engines |
| `frontend/` | Vue 3 + Vite + frappe-ui + ECharts SPA served at `/lumen` |
| `lumen_reports/dev/` | Developer verification helpers — not part of the product surface |

## Optional: demo data

Helpers to spin up a retail demo (ERPNext required) — brands, item groups, ~185 sales
invoices, and a ready-made dashboard:

```bash
bench --site your-site.localhost execute lumen_reports.retail_setup.run
bench --site your-site.localhost execute lumen_reports.retail_setup.enrich
bench --site your-site.localhost execute lumen_reports.retail_setup.enrich_items
bench --site your-site.localhost execute lumen_reports.retail_dashboard.run
```

## License

MIT
