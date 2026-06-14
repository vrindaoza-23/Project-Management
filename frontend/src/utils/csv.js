// Lightweight client-side CSV export. No deps; works on already-loaded rows.

// Quote a single cell per RFC 4180 (wrap in quotes if it contains a comma,
// quote, or newline; double any embedded quotes).
function cell(value) {
	if (value === null || value === undefined) return ''
	const s = String(value)
	if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"'
	return s
}

// Build a CSV string from an array of column defs [{ header, get }] and rows.
export function toCsv(columns, rows) {
	const head = columns.map((c) => cell(c.header)).join(',')
	const body = rows.map((row) => columns.map((c) => cell(c.get(row))).join(',')).join('\n')
	return head + '\n' + body
}

// Trigger a browser download of `text` as `filename`.
export function downloadText(filename, text, mime = 'text/csv;charset=utf-8') {
	const blob = new Blob(['﻿' + text], { type: mime }) // BOM so Excel reads UTF-8
	const url = URL.createObjectURL(blob)
	const a = document.createElement('a')
	a.href = url
	a.download = filename
	document.body.appendChild(a)
	a.click()
	document.body.removeChild(a)
	URL.revokeObjectURL(url)
}

// Export Projex issue rows (as returned by get_issues) to a CSV download.
export function exportIssuesCsv(issues, statuses, projectKey) {
	const statusName = Object.fromEntries((statuses || []).map((s) => [s.name, s.status_name]))
	const columns = [
		{ header: 'ID', get: (i) => i.issue_id },
		{ header: 'Title', get: (i) => i.title },
		{ header: 'Status', get: (i) => statusName[i.status] || i.status || '' },
		{ header: 'Priority', get: (i) => i.priority || '' },
		{ header: 'Assignees', get: (i) => (i.assignees || []).join('; ') },
		{ header: 'Labels', get: (i) => (i.labels || []).map((l) => l.label || l.title || l).join('; ') },
		{ header: 'Points', get: (i) => i.estimate ?? '' },
		{ header: 'Due', get: (i) => i.due_date || '' },
		{ header: 'Subtasks', get: (i) => (i.sub_total ? `${i.sub_done || 0}/${i.sub_total}` : '') },
		{ header: 'Updated', get: (i) => i.modified || '' },
	]
	const stamp = new Date().toISOString().slice(0, 10)
	downloadText(`${projectKey}-issues-${stamp}.csv`, toCsv(columns, issues))
}
