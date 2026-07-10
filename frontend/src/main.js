import { createApp } from 'vue'
import { FrappeUI, setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'

// Tailwind first, then frappe-ui component styles, then design tokens + the
// ported (token-accurate) layout layer from the design handoff.
import './tailwind.css'
import 'frappe-ui/style.css'
import 'frappe-ui/editor-style.css'
import 'frappe-ui/list-style.css'
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
