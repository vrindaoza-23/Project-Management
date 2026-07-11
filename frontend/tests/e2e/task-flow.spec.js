import { test, expect } from '@playwright/test'
import { collectErrors, openProject, openSurface, openTaskView, menuIsClickable } from './helpers'

const TASK = 'Redesign invoice detail page' // BIL-1, seeded

async function openTaskDrawer(page) {
	await openProject(page, 'BIL')
	await openSurface(page, 'Tasks')
	await openTaskView(page, 'List')
	await page.getByText(TASK).first().click()
	await expect(page.locator('.pjx-drawer.is-open')).toBeVisible({ timeout: 8000 })
}

test.describe('Task drawer', () => {
	test('opens with core fields', async ({ page }) => {
		await openTaskDrawer(page)
		const drawer = page.locator('.pjx-drawer')
		await expect(drawer).toContainText('BIL-1')
		await expect(drawer).toContainText('Assignees')
		await expect(drawer).toContainText('Checklist')
		await expect(drawer).toContainText('Repeat')
	})

	test('side-panel select opens ON TOP and is clickable (z-index guard)', async ({ page }) => {
		await openTaskDrawer(page)
		await page.locator('.pjx-drawer__side .pjx-field').first().locator('button, input').first().click()
		await page.waitForTimeout(500)
		expect(await menuIsClickable(page), 'assignee dropdown should render above the drawer').toBe(true)
	})

	test('priority edit persists across reopen', async ({ page }) => {
		await openTaskDrawer(page)
		const prio = page.locator('.pjx-statusrow button').nth(2)
		const original = (await prio.innerText()).trim()

		// pick a different priority from the dropdown
		await prio.click()
		await page.waitForTimeout(300)
		const opts = page.locator('[data-reka-popper-content-wrapper] [role="menuitem"], [data-reka-popper-content-wrapper] button')
		let chosen = null
		for (let i = 0; i < (await opts.count()); i++) {
			const t = (await opts.nth(i).innerText()).trim()
			if (t && t !== original) { chosen = t; await opts.nth(i).click(); break }
		}
		await page.waitForTimeout(900)
		expect((await prio.innerText()).trim()).toBe(chosen)

		// reopen from the server to confirm it stuck
		await page.locator('.pjx-drawer__top button').last().click()
		await page.waitForTimeout(400)
		await page.getByText(TASK).first().click()
		await expect(page.locator('.pjx-drawer.is-open')).toBeVisible()
		await page.waitForTimeout(500)
		expect((await page.locator('.pjx-statusrow button').nth(2).innerText()).trim()).toBe(chosen)

		// restore original
		await page.locator('.pjx-statusrow button').nth(2).click()
		await page.waitForTimeout(300)
		await page.locator('[data-reka-popper-content-wrapper]').getByText(original, { exact: true }).first().click()
		await page.waitForTimeout(700)
	})

	test('checklist add + remove (net zero)', async ({ page }) => {
		await openTaskDrawer(page)
		// unique title so the assertions target this exact row regardless of any
		// pre-existing checklist items (deterministic + self-cleaning on failure)
		const item = 'E2E check ' + Date.now()
		const row = page.locator('.pjx-check__row', { hasText: item })

		await page.locator('input.pjx-check__add').fill(item)
		await page.locator('input.pjx-check__add').press('Enter')
		await expect(row).toBeVisible({ timeout: 5000 })

		await row.locator('.pjx-check__del').click({ force: true })
		await expect(row).toHaveCount(0, { timeout: 5000 })
	})
})

test.describe('Create task', () => {
	const title = 'E2E task ' + Date.now()

	test('create via the New task dialog and see it in the list', async ({ page }) => {
		await openProject(page, 'BIL')
		await page.keyboard.press('c')
		const dialog = page.locator('[role="dialog"]')
		await expect(dialog.getByText('New task')).toBeVisible()
		await dialog.getByPlaceholder('Task title').fill(title)
		// project + type + priority are native selects inside the dialog
		await dialog.locator('select').nth(0).selectOption({ label: 'Billing v2' }).catch(() => {})
		await dialog.getByRole('button', { name: 'Create task' }).click()
		await expect(dialog).toBeHidden({ timeout: 8000 })

		await openSurface(page, 'Tasks')
		await openTaskView(page, 'List')
		await expect(page.getByText(title).first()).toBeVisible({ timeout: 8000 })
	})

	// Remove any tasks this spec created so repeated runs don't accumulate seed
	// data. Uses a freshly-authenticated context (the shared `request` fixture's
	// auth state isn't reliably carried into afterAll) and verifies the delete.
	test.afterAll(async ({ playwright }) => {
		const base = process.env.PROJEX_BASE_URL || 'http://localhost:8000'
		const ctx = await playwright.request.newContext({ baseURL: base })
		await ctx.post('/api/method/login', {
			form: { usr: process.env.PROJEX_USER || 'Administrator', pwd: process.env.PROJEX_PWD || 'admin' },
		})
		const res = await ctx.post('/api/method/frappe.client.get_list', {
			form: {
				doctype: 'Projex Issue',
				filters: JSON.stringify([['title', 'like', 'E2E task %']]),
				fields: JSON.stringify(['name']),
				limit_page_length: 0,
			},
		})
		const names = (await res.json()).message?.map((r) => r.name) || []
		if (names.length) {
			const del = await ctx.post('/api/method/projex.api.bulk_delete_issues', {
				form: { names: JSON.stringify(names) },
			})
			if (!del.ok()) throw new Error('cleanup delete failed: ' + del.status())
		}
		await ctx.dispose()
	})
})
