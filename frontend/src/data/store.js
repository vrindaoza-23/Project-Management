import { reactive } from 'vue'
import { createResource } from 'frappe-ui'

// Shared, API-backed app state (no hardcoded domain data).
export const store = reactive({
	user: null,
	projects: [],
	workspaces: [],
	users: [],
	counts: { inbox: 0 },
	loaded: false,
})

let bootResource = null

export function initStore() {
	if (bootResource) return bootResource
	bootResource = createResource({
		url: 'projex.api.bootstrap',
		auto: true,
		onSuccess(data) {
			store.user = data.user
			store.projects = data.projects || []
			store.workspaces = data.workspaces || []
			store.users = data.users || []
			store.counts = data.counts || { inbox: 0 }
			store.loaded = true
		},
	})
	return bootResource
}

export function reloadBootstrap() {
	if (bootResource) bootResource.reload()
}

export function userById(name) {
	return store.users.find((u) => u.name === name)
}

export function userName(name) {
	const u = userById(name)
	return u ? u.full_name || u.name : name
}

export function projectByKey(key) {
	return store.projects.find((p) => p.key === key || p.name === key)
}
