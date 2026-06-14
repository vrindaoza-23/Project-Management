import { defineConfig } from '@playwright/test'

const BASE = process.env.PROJEX_BASE_URL || 'http://mysite.localhost:8000'

export default defineConfig({
	testDir: './tests/e2e',
	timeout: 30000,
	fullyParallel: false,
	// The local dev server is single-threaded; under a full sequential run its
	// async bootstrap/socket can occasionally lag. One retry absorbs that
	// flakiness without masking real failures.
	retries: 1,
	reporter: 'list',
	globalSetup: './tests/e2e/global-setup.js',
	use: {
		baseURL: BASE,
		headless: true,
		storageState: './tests/e2e/.auth.json',
		screenshot: 'only-on-failure',
	},
})
