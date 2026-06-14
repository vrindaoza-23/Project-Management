import path from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'

export default defineConfig({
	plugins: [
		frappeui({
			frontendRoute: '/projex',
			lucideIcons: true,
			jinjaBootData: true,
			frappeProxy: true,
			buildConfig: true,
		}),
		vue(),
	],
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
		},
	},
	optimizeDeps: {
		include: ['frappe-ui > feather-icons', 'showdown', 'engine.io-client'],
	},
	build: {
		rollupOptions: {
			output: {
				// Split heavy vendors out of the main chunk for faster first paint.
				manualChunks: {
					'vendor-vue': ['vue', 'vue-router'],
					'vendor-frappe-ui': ['frappe-ui'],
					'vendor-icons': ['lucide-vue-next'],
				},
			},
		},
		chunkSizeWarningLimit: 800,
	},
})
