import { request } from '@playwright/test'

// Log in once via the API and persist the session so specs run authenticated.
export default async function globalSetup() {
	const base = process.env.PROJEX_BASE_URL || 'http://mysite.localhost:8000'
	const usr = process.env.PROJEX_USER || 'Administrator'
	const pwd = process.env.PROJEX_PWD || 'admin123'

	const ctx = await request.newContext({ baseURL: base })
	const res = await ctx.post('/api/method/login', { form: { usr, pwd } })
	if (!res.ok()) throw new Error(`Login failed: ${res.status()} ${await res.text()}`)
	await ctx.storageState({ path: './tests/e2e/.auth.json' })
	await ctx.dispose()
}
