import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
	plugins: [vue()],
	resolve: {
		alias: { '@': path.resolve(__dirname, 'src') },
	},
	test: {
		environment: 'jsdom',
		globals: true,
		// Unit tests live alongside source; Playwright e2e specs run via `yarn e2e`.
		include: ['src/**/*.{test,spec}.js'],
		exclude: ['node_modules', 'tests/e2e'],
	},
})
