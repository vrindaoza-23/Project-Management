import { test, expect } from '@playwright/test'

// Browser-level checks for the gap-closure roadmap features. Runs against the
// seeded Projex site (project BIL, task "Redesign invoice detail page" = BIL-1).
test.describe('Projex gap-closure features', () => {
	test('List view shows Export + Views controls and bulk bar on selection', async ({ page }) => {
		await page.goto('/projex/projects/BIL')
		await page.locator('.pjx-vtab', { hasText: 'List' }).click()

		// CSV export (#1) and Saved Views (#2) controls render.
		await expect(page.getByRole('button', { name: 'Export' })).toBeVisible()
		await expect(page.getByRole('button', { name: 'Views' })).toBeVisible()

		// Bulk multi-select (#5): selecting a row reveals the action bar.
		const row = page.locator('.pjx-row', { hasText: 'Redesign invoice detail page' }).first()
		await row.hover()
		await row.locator('.pjx-check').check({ force: true })
		const bar = page.locator('.pjx-bulkbar')
		await expect(bar).toBeVisible()
		await expect(bar).toContainText('selected')
		await expect(bar.getByRole('button', { name: 'Status' })).toBeVisible()
	})

	test('Task drawer exposes Repeat (recurrence) and Checklist', async ({ page }) => {
		await page.goto('/projex/projects/BIL')
		await page.locator('.pjx-vtab', { hasText: 'List' }).click()
		await page.getByText('Redesign invoice detail page').first().click()

		const drawer = page.locator('.pjx-drawer')
		await expect(drawer).toBeVisible()
		await expect(drawer).toContainText('BIL-1')
		await expect(drawer).toContainText('Repeat') // recurring tasks (#9)
		await expect(drawer).toContainText('Checklist') // checklists (#4)
	})

	test('Inbox exposes email notification preferences', async ({ page }) => {
		await page.goto('/projex/inbox')
		await page.getByTitle('Email notifications').click()
		// email prefs dialog (#7)
		await expect(page.getByText('When someone @mentions me')).toBeVisible()
		await expect(page.getByText('Status changes on my issues')).toBeVisible()
	})
})
