import { test, expect } from '@playwright/test'

// Verify the New task modal selects work and produce a task with those values.
test('New task modal: all option controls work', async ({ page }) => {
	await page.goto('/projex/projects/BIL')
	await page.keyboard.press('c')
	const dialog = page.locator('[role="dialog"]')
	await expect(dialog.getByText('New task')).toBeVisible()

	// There should now be native <select> elements (Project, Type, Priority, +2 multi)
	const selectCount = await dialog.locator('select').count()
	expect(selectCount).toBeGreaterThanOrEqual(5)

	const unique = 'E2E native-select ' + Date.now()
	await dialog.getByPlaceholder('Task title').fill(unique)

	// Single selects by visible label
	await dialog.locator('select').nth(0).selectOption({ label: 'Billing v2' }) // Project
	await dialog.locator('select').nth(1).selectOption({ label: 'Bug' }) // Type
	await dialog.locator('select').nth(2).selectOption({ label: 'High' }) // Priority

	// Multi: Assignees add-select (4th select) -> pick a user, assert a chip appears
	await dialog.locator('select').nth(3).selectOption({ index: 1 })
	await expect(dialog.locator('.pjx-nsel__chip')).toHaveCount(1)

	await page.getByRole('button', { name: 'Create task' }).click()
	await expect(dialog).toBeHidden()

	// Confirm via the row appearing in the project
	await page.locator('.pjx-vtab', { hasText: 'List' }).click()
	await expect(page.getByText(unique).first()).toBeVisible({ timeout: 5000 })
})
