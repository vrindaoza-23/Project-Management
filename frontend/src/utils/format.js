export function isToday(dateStr) {
	if (!dateStr) return false
	const d = new Date(dateStr)
	const t = new Date()
	return d.toDateString() === t.toDateString()
}

export function dueLabel(dateStr) {
	if (!dateStr) return ''
	const d = new Date(dateStr)
	if (isToday(dateStr)) return 'Today'
	const opts = { month: 'short', day: 'numeric' }
	return d.toLocaleDateString(undefined, opts)
}

export function relativeTime(dateStr) {
	if (!dateStr) return ''
	const then = new Date(dateStr.replace(' ', 'T'))
	const secs = Math.floor((Date.now() - then.getTime()) / 1000)
	if (secs < 60) return 'now'
	const mins = Math.floor(secs / 60)
	if (mins < 60) return `${mins}m`
	const hrs = Math.floor(mins / 60)
	if (hrs < 24) return `${hrs}h`
	const days = Math.floor(hrs / 24)
	if (days < 7) return `${days}d`
	const wks = Math.floor(days / 7)
	return `${wks}w`
}
