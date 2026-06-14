import { describe, it, expect, beforeAll } from 'vitest'
import { isToday, dueLabel, relativeTime } from './format'

describe('format utils', () => {
	it('isToday is true for today, false for other days', () => {
		const today = new Date().toISOString().slice(0, 10)
		expect(isToday(today)).toBe(true)
		expect(isToday('2000-01-01')).toBe(false)
		expect(isToday(null)).toBe(false)
	})

	it('dueLabel says Today for today and a short date otherwise', () => {
		const today = new Date().toISOString().slice(0, 10)
		expect(dueLabel(today)).toBe('Today')
		expect(dueLabel('')).toBe('')
		expect(dueLabel('2000-01-15')).toMatch(/Jan/)
	})

	it('relativeTime returns compact units', () => {
		const now = new Date().toISOString()
		expect(relativeTime(now)).toMatch(/now|m/)
		const twoHrsAgo = new Date(Date.now() - 2 * 3600 * 1000).toISOString()
		expect(relativeTime(twoHrsAgo)).toBe('2h')
		expect(relativeTime('')).toBe('')
	})
})
