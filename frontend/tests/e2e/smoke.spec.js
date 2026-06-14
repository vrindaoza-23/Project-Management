import { test, expect } from '@playwright/test'

// End-to-end smoke flow against a seeded Projex site:
// app shell → project → List view → open task drawer.
test.describe('Projex smoke', () => {
	test('app shell renders with projects', async ({ page }) => {
		await page.goto('/projex/inbox')
		await expect(page.locator('.pjx-side')).toBeVisible()
		// Projects section lists at least one seeded project (bootstrap is async,
		// so allow time for it to load before asserting).
		await expect(page.getByText('Billing v2').first()).toBeVisible({ timeout: 15000 })
	})

	test('open a project, list tasks, open the drawer', async ({ page }) => {
		await page.goto('/projex/projects/BIL')
		// view tabs present
		await expect(page.locator('.pjx-vtab', { hasText: 'List' })).toBeVisible()
		// switch to List
		await page.locator('.pjx-vtab', { hasText: 'List' }).click()
		// a seeded task row appears
		const row = page.getByText('Redesign invoice detail page').first()
		await expect(row).toBeVisible()
		// open the drawer
		await row.click()
		await expect(page.locator('.pjx-drawer')).toBeVisible()
		await expect(page.locator('.pjx-drawer')).toContainText('BIL-1')
	})

	test('summary dashboard loads stats', async ({ page }) => {
		await page.goto('/projex/projects/BIL')
		// default Summary tab shows the status overview panel
		await expect(page.getByText('Status overview')).toBeVisible()
	})
})
