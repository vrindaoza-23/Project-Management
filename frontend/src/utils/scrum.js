// Pure helpers for sprint/backlog story-point math. Kept framework-free so
// they are trivially unit-testable and reusable across views.

export function sumPoints(issues = []) {
	return issues.reduce((total, issue) => total + (Number(issue.estimate) || 0), 0)
}

export function donePoints(issues = [], completedStatuses = new Set()) {
	return sumPoints(issues.filter((issue) => completedStatuses.has(issue.status)))
}
