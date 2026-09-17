// Copyright (c) 2026 Lumen Solutions. All rights reserved.
// SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
// Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
import { io } from 'socket.io-client'

let socket = null

function config(key, fallback) {
  const value = window[key]
  if (!value || String(value).startsWith('{{')) return fallback
  return value
}

// Build the socket.io URL the way Frappe's own client does (get_host in
// socketio_client.js): in production the page is on a standard port and
// socket.io is proxied at the same origin, so connect to the origin as-is; only
// a dev bench, where the page runs on its own port (e.g. 8000) and socket.io
// listens on socketio_port (9000), swaps the port. Hardcoding :9000 broke every
// Frappe Cloud site (port 9000 is not exposed there), which showed as a stuck
// "Offline" badge and no live updates.
function socketUrl() {
  const siteName = config('site_name', window.location.hostname)
  const pagePort = window.location.port
  const socketioPort = config('socketio_port', '')
  if (pagePort && socketioPort) {
    // dev: same host, socket.io on its own port
    return `${window.location.protocol}//${window.location.hostname}:${socketioPort}/${siteName}`
  }
  // production behind a proxy: same origin, standard port, /socket.io proxied
  return `${window.location.origin}/${siteName}`
}

export function getSocket() {
  if (socket) return socket
  socket = io(socketUrl(), {
    withCredentials: true,
    reconnectionAttempts: 5,
  })
  window.__lumen_socket = socket // debug/test handle, mirrors __lumen_chart
  return socket
}
