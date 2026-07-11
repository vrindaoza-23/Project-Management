import { defineConfig } from '@playwright/test'

// Default targets the local bench default-site (served on bare localhost:8000).
// Override PROJEX_BASE_URL / PROJEX_USER / PROJEX_PWD for CI or another site.
const BASE = process.env.PROJEX_BASE_URL || 'http://localhost:8000'

export default defineConfig({
	testDir: './tests/e2e',
	timeout: 40000,
	expect: { timeout: 10000 },
	fullyParallel: false,
	// The local dev server is single-threaded; under a full sequential run its
	// async bootstrap/socket can occasionally lag. One retry absorbs that
	// flakiness without masking real failures.
	retries: 1,
	workers: 1,
	reporter: [['list']],
	globalSetup: './tests/e2e/global-setup.js',
	use: {
		baseURL: BASE,
		headless: true,
		// Local dev drives the system Google Chrome (Playwright's bundled Chromium
		// often isn't installed on a working bench). CI installs bundled Chromium
		// (`playwright install chromium`), so leave the channel unset there.
		channel: process.env.CI ? undefined : 'chrome',
		storageState: './tests/e2e/.auth.json',
		screenshot: 'only-on-failure',
		trace: 'retain-on-failure',
	},
})
