import { test, expect } from '@playwright/test'
import { collectErrors, openProject, openSurface, openTaskView } from './helpers'

// Broad smoke: every major surface loads, shows a landmark element, and logs no
// console/page errors. This is the codified version of the manual audit — it
// fails loudly on the class of regression (e.g. a blank view or a thrown error)
// that "it builds" never catches.

test.describe('Global routes load cleanly', () => {
	const routes = [
		{ path: '/projex/inbox', landmark: '.pjx-side' },
		{ path: '/projex/my-tasks', landmark: '.pjx-side' },
		{ path: '/projex/users', landmark: '.pjx-side' },
		{ path: '/projex/roadmap', landmark: '.pjx-side' },
	]
	for (const r of routes) {
		test(`route ${r.path}`, async ({ page }) => {
			const errors = collectErrors(page)
			await page.goto(r.path)
			await expect(page.locator(r.landmark).first()).toBeVisible({ timeout: 20000 })
			await page.waitForTimeout(1000)
			expect(errors, `console errors on ${r.path}:\n${errors.join('\n')}`).toEqual([])
		})
	}
})

test.describe('Project surfaces load cleanly', () => {
	test('Overview shows status panel', async ({ page }) => {
		const errors = collectErrors(page)
		await openProject(page, 'BIL')
		await expect(page.getByText('Status overview')).toBeVisible()
		await page.waitForTimeout(800)
		expect(errors, errors.join('\n')).toEqual([])
	})

	test('all five task views render without errors', async ({ page }) => {
		const errors = collectErrors(page)
		await openProject(page, 'BIL')
		await openSurface(page, 'Tasks')
		for (const view of ['List', 'Board', 'Calendar', 'Gantt', 'Backlog']) {
			const before = errors.length
			await openTaskView(page, view)
			await expect(page.locator('.pjx-view').first()).toBeVisible()
			expect(errors.slice(before), `errors after opening ${view}:\n${errors.slice(before).join('\n')}`).toEqual([])
		}
	})

	test('Dashboard, Timesheets, Docs surfaces load', async ({ page }) => {
		const errors = collectErrors(page)
		await openProject(page, 'BIL')
		await openSurface(page, 'Dashboard')
		await page.waitForTimeout(1000)
		await openSurface(page, 'Timesheets')
		await page.waitForTimeout(1000)
		await openSurface(page, 'Docs')
		await page.waitForTimeout(1000)
		expect(errors, errors.join('\n')).toEqual([])
	})

	test('More menu surfaces (Reports / Activity) load', async ({ page }) => {
		const errors = collectErrors(page)
		await openProject(page, 'BIL')
		await page.getByRole('button', { name: /^More/ }).click()
		await page.getByRole('menuitem', { name: /Reports/ }).click()
		await page.waitForTimeout(1200)
		await page.getByRole('button', { name: /^More/ }).click()
		await page.getByRole('menuitem', { name: /Activity/ }).click()
		await page.waitForTimeout(1200)
		expect(errors, errors.join('\n')).toEqual([])
	})
})
