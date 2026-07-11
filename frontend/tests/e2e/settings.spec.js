import { test, expect } from '@playwright/test'
import { collectErrors, openProject, openSettings, menuIsClickable } from './helpers'

// Guards the settings dialog we built: the three nav groups, the workspace and
// project switchers, and — critically — that dropdowns opened INSIDE the dialog
// render on top and are clickable (the z-index regression the user hit).

test.describe('App settings dialog', () => {
	test('opens with User / Workspace / Project groups', async ({ page }) => {
		await openProject(page, 'BIL')
		await openSettings(page)
		await expect(page.getByText('User settings')).toBeVisible()
		await expect(page.getByText('Workspace settings')).toBeVisible()
		await expect(page.getByText('Project settings')).toBeVisible()
	})

	test('workspace Members: picker opens ON TOP and is clickable (z-index guard)', async ({ page }) => {
		const errors = collectErrors(page)
		await openProject(page, 'BIL')
		await openSettings(page)

		// Workspace group -> Members
		await page.getByRole('tab', { name: 'Members' }).first().click()
		await page.waitForTimeout(800)

		// role dropdowns render for existing members
		await expect(page.locator('.pjx-rolesel').first()).toBeVisible()

		// open the "Pick users" autocomplete; its menu must be the top element
		await page.getByText('Pick users', { exact: true }).first().click()
		await page.waitForTimeout(600)
		expect(await menuIsClickable(page), 'member picker menu should render on top of the dialog').toBe(true)
		expect(errors, errors.join('\n')).toEqual([])
	})

	test('project settings sections switch via the switcher', async ({ page }) => {
		await openProject(page, 'BIL')
		await openSettings(page)
		// project General/Members/Labels/Cycles/ERPNext exist in the Project group
		await page.getByRole('tab', { name: 'Labels' }).click()
		await page.waitForTimeout(600)
		await expect(page.getByRole('heading', { name: 'Labels' })).toBeVisible()
		await page.getByRole('tab', { name: 'Cycles' }).click()
		await page.waitForTimeout(600)
		await expect(page.getByRole('heading', { name: 'Cycles' })).toBeVisible()
	})
})
