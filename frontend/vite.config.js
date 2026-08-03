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
			// Set indexHtmlPath explicitly: the plugin's auto-detection
			// (findAppName) only resolves inside a full bench layout, so CI's
			// bare-repo checkout throws "indexHtmlPath is required". This path is
			// correct from the frontend/ dir in both CI jobs and local benches.
			buildConfig: {
				indexHtmlPath: '../projex/www/projex.html',
			},
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
