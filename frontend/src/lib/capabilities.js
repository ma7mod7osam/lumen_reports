// Copyright (c) 2026 Lumen Solutions. All rights reserved.
// SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
// Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
/**
 * Runtime capabilities the server reports through boot (see www/lumen.py, which
 * writes each boot key to window[key]).
 */

/**
 * Whether PDF reports and scheduled delivery are available. They need
 * WeasyPrint, which ships with Frappe v15 and v16 but not v14.
 *
 * window.reports_enabled is a JSON boolean in a built page. In the Vite dev
 * server the boot template is unrendered, so treat anything that is not an
 * explicit false as on.
 */
export function reportsEnabled() {
  try {
    return window.reports_enabled !== false
  } catch {
    return true
  }
}
