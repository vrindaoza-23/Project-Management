/**
 * Data layer. The decided intent was the frappe-ui v3 `useList`/`useDoc`
 * composables, but the installed frappe-ui (0.1.x) ships the
 * createResource/createListResource/createDocumentResource factories. These
 * thin adapters expose the intended `useList`/`useDoc`/`useCall` names so call
 * sites read as decided and can swap to native composables later.
 *
 * Nothing here hardcodes domain data — every value comes from the API.
 */
import { createResource, createListResource, createDocumentResource } from 'frappe-ui'

export function useCall(options) {
	// options: { url (method path) | method, params, auto, ... }
	return createResource(options)
}

export function useList(doctype, options = {}) {
	return createListResource({ doctype, ...options })
}

export function useDoc(doctype, name, options = {}) {
	return createDocumentResource({ doctype, name, ...options })
}

// ---- Projex-specific resources ------------------------------------------- //

export function bootstrapResource() {
	return createResource({
		url: 'projex.api.bootstrap',
		cache: 'projex:bootstrap',
		auto: true,
	})
}

export function boardResource(project) {
	return createResource({
		url: 'projex.api.get_issues',
		makeParams: () => ({ project }),
		auto: true,
	})
}

export function inboxResource(filter = 'all') {
	return createResource({
		url: 'projex.api.get_inbox',
		makeParams: () => ({ filter }),
		auto: true,
	})
}

export function myIssuesResource() {
	return createResource({ url: 'projex.api.get_my_issues', auto: true })
}

export function roadmapResource() {
	return createResource({ url: 'projex.api.get_roadmap', auto: true })
}

export function integrationStatusResource() {
	return createResource({ url: 'projex.api.integration_status', auto: true })
}

// Update an issue field (optimistic callers patch local state first).
export function updateIssue() {
	return createResource({ url: 'frappe.client.set_value' })
}
