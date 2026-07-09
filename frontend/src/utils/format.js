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

export function formatMoney(amount, currency = 'USD') {
	const n = Number(amount) || 0
	try {
		return new Intl.NumberFormat(undefined, {
			style: 'currency',
			currency: currency || 'USD',
			maximumFractionDigits: n % 1 === 0 ? 0 : 2,
		}).format(n)
	} catch {
		return `${currency} ${n.toLocaleString()}`
	}
}

export function daysSince(dateStr) {
	if (!dateStr) return 0
	const then = new Date(dateStr.replace(' ', 'T'))
	return Math.floor((Date.now() - then.getTime()) / 86400000)
}

// Age chip for "time in current status": label + staleness level.
// warn ≥ 7 days, stale ≥ 14 days. Falls back to `modified` if no status timestamp.
export function ageChip(statusChangedOn, modified) {
	const ref = statusChangedOn || modified
	if (!ref) return { label: '', level: 'ok', days: 0 }
	const days = daysSince(ref)
	const level = days >= 14 ? 'stale' : days >= 7 ? 'warn' : 'ok'
	return { label: relativeTime(ref), level, days }
}
