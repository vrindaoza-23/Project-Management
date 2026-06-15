import { describe, it, expect } from 'vitest'
import { sumPoints, donePoints } from './scrum'

describe('sumPoints', () => {
	it('adds estimates, treating missing/invalid as zero', () => {
		expect(sumPoints([{ estimate: 5 }, { estimate: 3 }, {}])).toBe(8)
	})
	it('returns 0 for an empty list', () => {
		expect(sumPoints([])).toBe(0)
	})
})

describe('donePoints', () => {
	it('counts only points of issues in a completed status', () => {
		const issues = [
			{ estimate: 5, status: 'done' },
			{ estimate: 3, status: 'open' },
		]
		expect(donePoints(issues, new Set(['done']))).toBe(5)
	})
	it('returns 0 when no status is completed', () => {
		expect(donePoints([{ estimate: 5, status: 'open' }], new Set())).toBe(0)
	})
})
