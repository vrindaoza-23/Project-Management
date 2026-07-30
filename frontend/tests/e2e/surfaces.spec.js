import { test, expect } from '@playwright/test'
import { collectErrors, openProject, openSurface, openMoreItem } from './helpers'

// Deeper per-surface coverage beyond "it loads": each asserts a real landmark
// and, where it makes sense, exercises one interaction — without mutating data.

test.describe('Global surfaces', () => {
	test('Inbox lists notifications and opens email preferences', async ({ page }) => {
		const errors = collectErrors(page)
		await page.goto('/projex/inbox')
		await expect(page.locator('.pjx-inbox')).toBeVisible({ timeout: 20000 })
		// email-notification preferences dialog (interaction)
		await page.getByTitle('Email notifications').click()
		await expect(page.getByText('When someone @mentions me')).toBeVisible()
		await page.keyboard.press('Escape')
		expect(errors, errors.join('\n')).toEqual([])
	})

	test('My tasks shows the personal task list', async ({ page }) => {
		const errors = collectErrors(page)
		await page.goto('/projex/my-tasks')
		// either grouped task rows or an empty state, inside the list container
		await expect(page.locator('.pjx-list, .pjx-view').first()).toBeVisible({ timeout: 20000 })
		await page.waitForTimeout(800)
		expect(errors, errors.join('\n')).toEqual([])
	})

	test('Users management page renders people + all-access control', async ({ page }) => {
		const errors = collectErrors(page)
		await page.goto('/projex/users')
		await expect(page.locator('.pjx-users, .pjx-ppl-list').first()).toBeVisible({ timeout: 20000 })
		await expect(page.getByText('Alice Chen').first()).toBeVisible()
		// the privileged "grant visibility into every project" control is present
		await expect(page.getByTitle('Grant visibility into every project').first()).toBeVisible()
		expect(errors, errors.join('\n')).toEqual([])
	})

	test('Roadmap renders its timeline container', async ({ page }) => {
		const errors = collectErrors(page)
		await page.goto('/projex/roadmap')
		await expect(page.locator('.pjx-roadmap, .pjx-roadmap__state').first()).toBeVisible({ timeout: 20000 })
		expect(errors, errors.join('\n')).toEqual([])
	})
})

test.describe('Project surfaces (deep)', () => {
	test('Overview renders KPIs and status', async ({ page }) => {
		const errors = collectErrors(page)
		await openProject(page, 'BIL')
		await openSurface(page, 'Overview')
		await expect(page.locator('.pjx-kpis').first()).toBeVisible({ timeout: 15000 })
		await expect(page.getByText('Recent activity')).toBeVisible()
		expect(errors, errors.join('\n')).toEqual([])
	})

	test('Timesheets shows flow-time metrics', async ({ page }) => {
		const errors = collectErrors(page)
		await openProject(page, 'BIL')
		await openMoreItem(page, 'Timesheets')
		await expect(page.locator('.pjx-ts').first()).toBeVisible({ timeout: 15000 })
		await expect(page.getByText('Average time in each status')).toBeVisible()
		expect(errors, errors.join('\n')).toEqual([])
	})

	test('Docs surface renders document content', async ({ page }) => {
		const errors = collectErrors(page)
		await openProject(page, 'BIL')
		await openSurface(page, 'Docs')
		await page.waitForTimeout(1200)
		await expect(page.locator('.pjx-view').first()).toBeVisible()
		expect(errors, errors.join('\n')).toEqual([])
	})

	test('Overview surface shows workload + open bugs panels', async ({ page }) => {
		const errors = collectErrors(page)
		await openProject(page, 'BIL')
		await openSurface(page, 'Overview')
		await expect(page.getByRole('heading', { name: 'Workload' })).toBeVisible({ timeout: 15000 })
		await expect(page.getByRole('heading', { name: 'Open bugs' })).toBeVisible()
		expect(errors, errors.join('\n')).toEqual([])
	})

	test('Finance surface renders (manager-only)', async ({ page }) => {
		const errors = collectErrors(page)
		await openProject(page, 'BIL')
		await page.locator('.pjx-moretab').click()
		await page.getByRole('menuitem', { name: /Finance/ }).click()
		// either the finance dashboard or an ERPNext-not-linked state, but no crash
		await expect(page.locator('.pjx-fin, .pjx-soon, .pjx-view').first()).toBeVisible({ timeout: 15000 })
		expect(errors, errors.join('\n')).toEqual([])
	})
})
