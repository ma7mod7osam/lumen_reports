# Lumen Reports — Logo Kit

Product logo for **Lumen Reports**, the analytics & dashboards app for ERPNext.
Part of the Lumen family: same 48-unit grid, same blue, same rounded geometry as the
Lumen Solutions company mark and LumenPDF Studio — but its own object, the **axis**.

## The mark
**Axis Bars** — one solid vertical axis on the left with three report rows measuring off it,
the middle row longest and carrying the brand blue. It is the Barcode-L's bar vocabulary
rotated 90°, which is what makes Reports read as a sibling of Solutions rather than a
stranger. Holds legibility down to 18px in the mini cut.

## Colors
- Brand blue `#1463FF` — axis + emphasis row · deep `#0B43B8` (gradient end)
- Accent `#7FA8FF` — secondary rows
- Dark-mode: axis `#2F7BFF` / rows `#6BA4FF`
- Ink (mono) `#0C1322` / gray `#98A1B2`
- Type: **Plus Jakarta Sans 800** ("LumenReports", *Reports* carried in blue) +
  **IBM Plex Mono 500** letter-spaced eyebrow ("ANALYTICS").
  Arabic: **IBM Plex Sans Arabic** 700/500.

## Files

### svg/ (vector masters)
- `mark.svg` · `mark-white.svg` · `mark-ink.svg` · `mark-darkmode.svg` — the symbol
- `mark-mini.svg` · `-white` · `-ink` — **simplified cut for below 28px** (third row drops,
  bars thicken)
- `lockup-horizontal.svg` · `-dark` · `-white` — **primary lockup**
- `lockup-stacked.svg` — square placements
- `lockup-bilingual.svg` — EN / AR pair with divider rule
- `wordmark.svg` — type only
- `app-icon.svg` (rounded) · `app-icon-square.svg` (full-bleed, stores) · `-dark` · `-mono`
- `favicon.svg` — mini cut in a tile

⚠ Lockup **SVGs** use live text. Install Plus Jakarta Sans + IBM Plex Mono + IBM Plex Sans
Arabic (all free on Google Fonts), or convert to outlines before production. The lockup
**PNGs** are already rendered with the correct fonts — use those if you can't install them.

### png/ (ready to use, transparent where applicable)
- `app-icon-1024-square.png` — App Store / Play Store source (platforms apply their own mask)
- `app-icon-512 / 180 / 120.png` — rounded tile
- `app-icon-dark-512.png`, `app-icon-mono-512.png`
- `mark-512.png`, `mark-white-512.png`, `mark-ink-512.png`, `mark-darkmode-512.png`
- `mark-mini-512.png`, `mark-mini-white-512.png`
- `lockup-horizontal.png` (+ `-dark`, `-white`), `lockup-stacked.png`, `lockup-bilingual.png`
  — rendered at 2x with live fonts
- `favicon-32.png`, `favicon-16.png`

## Usage rules
- Clear space: ≥ 25% of mark height on all sides.
- **Minimum size for the full three-row mark is 28px.** Below that use `mark-mini` /
  `favicon` — the third row congests. (Same convention as LumenPDF Studio.)
- On blue or photo backgrounds use the white cut; on light UI the brand cut; print/stamp
  the ink cut; night dashboards the dark-mode cut.
- *Reports* always carries the blue in the wordmark — don't set it all one color.
- Don't recolor the rows to chart-series colors, rotate, stretch, or add effects.

## In-product placement
- **Frappe sidebar / app switcher** → rounded app-icon tile at 30px (mini cut inside).
- **Dashboard header** → `mark-mini.svg` at 22px + "LumenReports" wordmark.
- **Exported reports / PDFs** → `mark-mini.svg` at 14px in the footer, beside
  "Generated with Lumen Reports" in IBM Plex Mono.
- **Favicon** → `favicon-32.png` / `favicon-16.png`.

## Arabic
The name translates cleanly — `لومِن تقارير` with `تحليلات` as the eyebrow, mirrored
right-to-left across the divider rule. Unlike LumenPDF there's no Latin acronym to preserve.
Keep the Arabic line on one line (`white-space:nowrap`); it wraps and clips otherwise.

---
Reference page with all concepts, size ladder, and in-context mocks:
`Lumen Reports Logo.html` in the project root.
