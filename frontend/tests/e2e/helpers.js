import { expect } from '@playwright/test'

// Shared helpers matching the current (production-UI) component vocabulary:
//   - top surface nav + task sub-views are frappe-ui TabButtons => role="radio"
//   - the app settings dialog opens via Cmd/Ctrl+Shift+,
//   - portaled menus live in [data-reka-popper-content-wrapper]

// Attach a console/page error collector. Returns an array that fills as errors
// occur. We ignore benign noise (favicon/sourcemap 404s, ResizeObserver spam).
export function collectErrors(page) {
	const errors = []
	// Ignore known-benign noise:
	//  - favicon / sourcemap 404s
	//  - ResizeObserver "loop limit" warnings
	//  - a frappe-ui chart bug that calls ResizeObserver.observe(null) during a
	//    mount/unmount race (stack is in vendor-frappe-ui; charts still render).
	//    Tracked as an upstream issue; scoped tightly so real app errors still fail.
	const ignore = (t) =>
		/favicon|sourcemap|source map|ResizeObserver loop|Failed to execute 'observe' on 'ResizeObserver'|Failed to load resource: the server responded with a status of 404/.test(t)
	page.on('console', (m) => { if (m.type() === 'error' && !ignore(m.text())) errors.push(m.text()) })
	page.on('pageerror', (e) => { if (!ignore(e.message)) errors.push('PAGEERROR ' + e.message) })
	return errors
}

// Open a project by key and wait for its shell to be ready.
export async function openProject(page, key = 'BIL') {
	await page.goto(`/projex/projects/${key}`)
	await expect(page.locator('.pjx-topbar').first()).toBeVisible({ timeout: 20000 })
}

// Click a top-level surface (Overview / Tasks / Dashboard / Timesheets / Docs).
export async function openSurface(page, name) {
	await page.getByRole('radio', { name: new RegExp('^' + name) }).first().click()
	await page.waitForTimeout(600)
}

// Within the Tasks surface, switch task sub-view (List/Board/Calendar/Gantt/Backlog).
export async function openTaskView(page, name) {
	await page.getByRole('radio', { name, exact: true }).first().click()
	await page.waitForTimeout(800)
}

// True if the currently-open portaled menu is the top-most element at its own
// centre — i.e. actually clickable, not hidden behind a dialog/drawer overlay.
export async function menuIsClickable(page) {
	return page.evaluate(() => {
		const w = document.querySelector('[data-reka-popper-content-wrapper]')
		if (!w) return false
		const r = w.getBoundingClientRect()
		const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)
		return !!(hit && w.contains(hit))
	})
}

// Open the app settings dialog via its keyboard shortcut.
export async function openSettings(page) {
	await page.keyboard.press(process.platform === 'darwin' ? 'Meta+Shift+Comma' : 'Control+Shift+Comma')
	await page.waitForTimeout(700)
}
