<div align="center">

<img src="lumen_reports/public/logo/svg/app-icon.svg" width="76" height="76" alt="Lumen Reports" />

# Lumen Reports

**Beautiful, fast, live-updating dashboards and reports for Frappe / ERPNext.**

Build dashboards by dragging, from a template, or by asking in plain words.
Style them your way, send them as PDF reports, and use the whole app in English or Arabic.

</div>

---

## Why Lumen

Frappe ships capable but plain reporting. Getting a straight answer usually means
exporting to a spreadsheet or waiting on a custom script report.

Lumen is a standalone Vue 3 single-page app served at `/lumen`. It is **not** a BI
suite for analysts. It is an operational dashboard layer for the people who run the
business, built on the doctypes you already have.

- **A designed look, not default charts.** A cohesive design system, per-dashboard
  themes, and charts that recolor with the theme.
- **Live updates.** When an underlying document changes, affected widgets refresh in
  place over websockets. No refresh button.
- **No-code studio.** Start from a template or a blank canvas, edit any widget in a
  side inspector with a live preview, and drag and resize on a 12-column grid.
- **Permission-safe by construction.** Lumen never runs raw SQL. Every widget stores
  a query definition that the server compiles through Frappe's permission layer,
  checking read access on the base doctype *and* every joined doctype. PDF reports
  and scheduled emails are rendered with the same checks, as the person reading them.

## Features

**19 chart types and 4 layout elements**

| | |
|---|---|
| Trends | Line, Area, Sparkline, Waterfall |
| Comparisons | Bar (single or grouped), Stacked bar, Ranked bars, Radar |
| Composition | Donut, Pie, Funnel, Radial rings |
| Progress | Number card, Gauge, Progress bars |
| Distribution | Heatmap, Scatter / bubble |
| Detail | Table, Tree report |
| Layout elements | Heading, Text, Divider, Image |

**Building**

- **Starter templates.** Executive Overview, Products and Retail, Receivables,
  Purchasing and Team Workload. Each one is validated against the site's own data
  when it is created, and widgets the site cannot answer are left out. Only templates
  whose doctypes the user can read are offered. Team Workload works on any Frappe
  site, the other four use ERPNext doctypes.
- **Studio.** A side inspector with live preview, undo and redo (Ctrl+Z,
  Ctrl+Shift+Z), duplicate (Ctrl+D), and autosave for drafts. Published dashboards
  change only on an explicit Save changes.
- **Themes, per dashboard.** Six presets (Lumen Light, Lumen Dark, Emerald, Midnight,
  Sand, Paper), plus brand color, card style (flat, outlined, elevated, glass), corner
  radius, density, background (solid, gradient, brand tint) and font. Charts read
  their colors from the dashboard's theme. A color set by hand on a widget is kept.
- **Form follows data.** The chart type that suits the numbers is chosen by default,
  and the variant bar offers only the alternatives that also make sense.

**AI** *(optional, bring-your-own Gemini key)*

- **Copilot.** A panel in the studio that changes the whole dashboard, or one
  selected widget, on request: arrange the layout, apply a theme, retitle, switch
  chart types within the same shape family, recolor, remove, add headings and notes,
  build new widgets from the site's data, change what a widget measures, write an
  executive summary, or explain what stands out. Every proposal is shown as a list of
  changes first, and applying it is a single undo step. It replies in the user's
  language.
- **Ask AI** at `/lumen/ask`. Describe a report in plain English and Lumen generates
  validated widgets with a short written analysis, to save as a new dashboard or add
  to an existing one. It asks a clarifying question when a request is genuinely
  ambiguous, and surfaces the assumptions it made as one-tap refinements.

**Reading and sharing**

- **Dashboard filters.** Select, Link (searchable), Checkbox and **line-item**
  filters, all combined with AND.
- **Cross-filtering.** Click any chart segment to refocus every other widget, across
  document and line-item grain. Dimensions stack, each with a removable chip.
- **Related fields (one-hop joins).** Report on attributes pulled *live* from linked
  masters (Sales Invoice line to Item to **Brand / Item Group**) at line grain,
  without double-counting.
- **Two-dimensional grouping.** A second breakdown turns a chart into grouped bars,
  stacked bars, multi-line, a heatmap or a radar.
- **Tree reports.** Drill from category to brand to item, totals rolled up, every row
  showing its share of the whole.
- **Computed metrics.** Values that exist in no field: average check-in time, hours
  worked, payment terms in days, outstanding as a percentage of invoiced.
- **PDF reports** at `/lumen/dashboard/<slug>/report`. A4 or Letter, a company header
  (the default Company's name and logo, where set), page numbers, the dashboard's
  current filters, an optional AI executive summary, and an English or Arabic
  edition. Rendered on the server with WeasyPrint, which ships with Frappe. Fonts are
  bundled, and the renderer fetches nothing from outside the site.
- **Scheduled delivery.** Email a dashboard's PDF daily, weekly or monthly to users
  of the site. Each copy is rendered as its recipient, so it carries their
  permissions, and a recipient who cannot open the dashboard receives nothing. A test
  copy can be sent to yourself first.
- **Arabic interface.** A language switch in the app turns the whole interface, the
  PDFs and the emails to Arabic, right to left.
- **Result caching** with automatic doc-event invalidation, **CSV / SVG export**, and
  **publish-based visibility** (users see published dashboards plus their own drafts).
- **Responsive.** Built for phones as well as desktops.

## Requirements

- Frappe Framework **v15** or **v16**
- Works alongside ERPNext, or on any custom app. Lumen reads whatever doctypes exist.
- The AI features are optional and need your own Google Gemini API key
- Scheduled delivery needs an outgoing **Email Account** on the site and the Frappe
  scheduler running. Due schedules are picked up every 10 minutes.

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
yarn build    # production build, served at /lumen
```

## Permissions

Lumen ships four roles (created on install):

| Role | Can do |
|---|---|
| **Lumen Viewer** | Open the app and see published dashboards |
| **Lumen Restricted Viewer** | See **only** dashboards that name them, which is how you give someone exactly one dashboard |
| **Lumen Builder** | Viewer, plus create dashboards, edit or delete their own, and schedule reports |
| **Lumen Manager** | Full control over all dashboards and schedules |

Three independent layers:

1. **App access.** `/lumen` requires one of the roles above (System Managers always
   have access).
2. **Dashboard visibility.** Drafts are private to their owner. Published dashboards
   are visible to everyone with Lumen access, unless the dashboard names an audience
   ("Who can see it" in settings): roles, specific people, or both. Restricted
   Viewers invert the default: they see nothing except dashboards that name them.
3. **Data.** Every widget query runs through Frappe's permission layer for the
   *viewing* user. A builder can only report on doctypes their roles let them read,
   and two users can open the same dashboard and correctly see different numbers.
   PDFs and scheduled emails follow the same rule for the person receiving them.

Assign the roles from the desk (User, then Roles) like any other Frappe role.

## AI setup (optional)

The AI features run on **Google Gemini**, using a key you provide. Usage, and any
charge for it, sits with the Google account that owns the key.

1. Open `/lumen/ask` in the app.
2. Get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). A
   step-by-step guide is on the page.
3. Paste it as your **personal key**, or, as a System Manager, set a **site-wide
   key** shared by everyone (a personal key always takes priority).

Keys are stored **encrypted** in the site database, never returned to the browser and
never included in error messages. The model only ever emits Lumen's query
specification, or the copilot's list of operations, and both are executed through the
same permission-aware engine as every other widget. The AI never touches the
database directly.

**What Google receives:** the user's request, the structure of the relevant doctypes
(names, fields, labels, types), summary figures (record counts, date ranges, a few
field values with counts) and, for analyses and executive summaries, the totals shown
on the charts with their category names. It never receives whole documents or table
rows.

## Architecture

| Layer | What it does |
|---|---|
| `Lumen Dashboard` / `Lumen Widget` doctypes | Dashboards, theme, widget query specs (JSON), layout, filters |
| `Lumen Report Schedule` / `Lumen Report Recipient` doctypes | Scheduled PDF delivery and its recipients |
| `query_engine.py` | Compiles a JSON query to `frappe.get_list`, so permissions always apply |
| `report_engine.py` | `frappe.qb` engine for line-item grain, one-hop joins, matrices, trees, computed metrics |
| `realtime.py` | Doctype to dashboard registry, publishes invalidation on doc change |
| `api.py` | Dashboard, widget and builder endpoints |
| `starters.py` | Starter templates, validated against the site's data on creation |
| `ai.py` | Ask AI orchestration (Gemini), validated through the query engines |
| `copilot.py` | Studio copilot: typed operations, simulated on a copy before they are proposed |
| `report.py` | PDF rendering (WeasyPrint), English and Arabic |
| `schedules.py` | Schedule runner (scheduler cron, every 10 minutes) and delivery as each recipient |
| `licensing.py` | Frappe Cloud subscription check, cached, and never blocking reads |
| `frontend/` | Vue 3 + Vite + frappe-ui + ECharts SPA served at `/lumen` |
| `lumen_reports/dev/` | Developer verification helpers, not part of the product surface |

## Optional: demo data

Helpers to spin up a retail demo (ERPNext required): brands, item groups, about 185
sales invoices, and a ready-made dashboard:

```bash
bench --site your-site.localhost execute lumen_reports.retail_setup.run
bench --site your-site.localhost execute lumen_reports.retail_setup.enrich
bench --site your-site.localhost execute lumen_reports.retail_setup.enrich_items
bench --site your-site.localhost execute lumen_reports.retail_dashboard.run
```

## Licence

**Proprietary. © 2026 Lumen Solutions. All rights reserved.**

This repository is public so that Frappe Cloud can build and distribute the app, and
so you can read exactly what runs on your site. **It is not open source.** Being able
to read the source does not grant a right to copy, redistribute or resell it.

Using the app requires a valid subscription or purchase. You may modify it for use on
your own licensed sites. You may not distribute it, in original or modified form. See
[`license.txt`](license.txt) for the full terms.

Third-party open-source components retain their own licences. The bundled fonts (Plus
Jakarta Sans, IBM Plex Sans Arabic, IBM Plex Mono) are under the SIL Open Font
License, included next to them in `lumen_reports/public/fonts/`.

Commercial enquiries: [hello@lumen-solutions.co](mailto:hello@lumen-solutions.co)
