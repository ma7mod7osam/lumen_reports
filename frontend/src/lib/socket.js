import { io } from 'socket.io-client'

let socket = null

function config(key, fallback) {
  const value = window[key]
  if (!value || String(value).startsWith('{{')) return fallback
  return value
}

export function getSocket() {
  if (socket) return socket
  const siteName = config('site_name', window.location.hostname)
  const port = config('socketio_port', '9000')
  const host = window.location.hostname
  const protocol = window.location.protocol
  const url = `${protocol}//${host}:${port}/${siteName}`
  socket = io(url, {
    withCredentials: true,
    reconnectionAttempts: 5,
  })
  return socket
}
