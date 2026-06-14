import { initSocket } from 'frappe-ui'

let socket = null

export function getSocket() {
	if (socket) return socket
	try {
		socket = initSocket()
	} catch (e) {
		console.warn('[projex] realtime unavailable:', e)
		socket = null
	}
	return socket
}

/**
 * Subscribe to a Projex realtime event. Returns an unsubscribe fn.
 * No-ops gracefully if the socket could not be created.
 */
export function onRealtime(event, handler) {
	const s = getSocket()
	if (!s) return () => {}
	s.on(event, handler)
	return () => s.off(event, handler)
}

export function joinProjectRoom(project) {
	const s = getSocket()
	if (s) s.emit('doctype_subscribe', `projex:project:${project}`)
}
