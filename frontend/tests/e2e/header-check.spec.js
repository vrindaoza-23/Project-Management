import { test, expect } from '@playwright/test'

// Verifies the project topbar: many tabs must not overlap or cover the
// action buttons (New task / settings / search), and those buttons stay clickable.
test('project header tabs and buttons do not overlap', async ({ page }) => {
	await page.setViewportSize({ width: 1280, height: 800 })
	await page.goto('/projex/projects/BIL')
	await page.waitForSelector('.pjx-vtabs', { timeout: 20000 })

	const tabs = page.locator('.pjx-vtab')
	const tabCount = await tabs.count()
	const right = page.locator('.pjx-topbar__right')
	const newBtn = right.getByRole('button', { name: /New task/i })

	const rightBox = await right.boundingBox()
	const tabsBox = await page.locator('.pjx-vtabs').boundingBox()
	// Tab strip must end before the action group begins (no horizontal overlap).
	expect(tabsBox.x + tabsBox.width).toBeLessThanOrEqual(rightBox.x + 1)

	// New task button must be fully on-screen and clickable.
	const nb = await newBtn.boundingBox()
	expect(nb.x + nb.width).toBeLessThanOrEqual(1280)
	await expect(newBtn).toBeVisible()
	await newBtn.click()
	// A dialog should appear.
	await expect(page.locator('[role="dialog"]').first()).toBeVisible({ timeout: 5000 })

	console.log(`tabs=${tabCount} tabsRight=${Math.round(tabsBox.x + tabsBox.width)} actionLeft=${Math.round(rightBox.x)}`)
})
