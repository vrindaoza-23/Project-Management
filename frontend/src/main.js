import { createApp } from 'vue'
import { FrappeUI, setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'

// frappe-ui/style.css IS the Tailwind entry (@tailwind base/components/
// utilities + Inter font) — it runs through this app's PostCSS config, so the
// full utility set is emitted here exactly once. Never add a second @tailwind
// entry: duplicate emissions get cross-deduped by the minifier, which breaks
// the base-before-variants order (e.g. `w-full` overriding `sm:w-[220px]`).
import 'frappe-ui/style.css'
import 'frappe-ui/editor-style.css'
// frappe-gantt's package exports don't expose the CSS subpath, so it's vendored.
import './styles/frappe-gantt.css'
import './styles/tokens.css'
import './styles/appkit.css'
import './styles/projex.css'

import App from './App.vue'
import router from './router'

// Route all resource traffic through Frappe's request layer (handles CSRF,
// /api/method + /api/resource, errors).
setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)
app.use(FrappeUI)
app.use(resourcesPlugin)
app.use(router)
app.mount('#app')
