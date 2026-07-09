import { reactive } from 'vue'
import { toast } from 'frappe-ui'

// Toast notifications ------------------------------------------------------- //

export const notify = {
	success: (message, opts = {}) => toast.create({ type: 'success', message, ...opts }),
	error: (message, opts = {}) => toast.create({ type: 'error', message, ...opts }),
	info: (message, opts = {}) => toast.create({ type: 'info', message, ...opts }),
	warning: (message, opts = {}) => toast.create({ type: 'warning', message, ...opts }),
}

// Pull a human message out of a Frappe API error and surface it as a toast.
export function notifyError(err, fallback = 'Something went wrong') {
	let message = fallback
	if (typeof err === 'string') message = err
	else if (err?.messages?.length) message = err.messages.join(', ')
	else if (err?.message) message = err.message
	notify.error(message)
}

// Promise-based confirm dialog --------------------------------------------- //
// A single shared slot (one confirm at a time is all this app needs). The host
// component <ConfirmHost/> renders it; confirm() resolves true/false.

export const confirmState = reactive({
	open: false,
	title: 'Are you sure?',
	message: '',
	confirmLabel: 'Confirm',
	cancelLabel: 'Cancel',
	theme: 'gray',
	_resolve: null,
})

export function confirm(opts = {}) {
	return new Promise((resolve) => {
		Object.assign(confirmState, {
			title: 'Are you sure?',
			message: '',
			confirmLabel: 'Confirm',
			cancelLabel: 'Cancel',
			theme: 'gray',
			...opts,
			open: true,
			_resolve: resolve,
		})
	})
}

export function resolveConfirm(value) {
	confirmState.open = false
	confirmState._resolve?.(value)
	confirmState._resolve = null
}

// Promise-based single-field text prompt ----------------------------------- //
// Replaces window.prompt with a proper frappe-ui dialog. Resolves the trimmed
// string, or null on cancel.

export const promptState = reactive({
	open: false,
	title: '',
	label: '',
	placeholder: '',
	value: '',
	confirmLabel: 'Save',
	_resolve: null,
})

export function promptText(opts = {}) {
	return new Promise((resolve) => {
		Object.assign(promptState, {
			title: '',
			label: '',
			placeholder: '',
			value: '',
			confirmLabel: 'Save',
			...opts,
			open: true,
			_resolve: resolve,
		})
	})
}

export function resolvePrompt(value) {
	promptState.open = false
	promptState._resolve?.(value)
	promptState._resolve = null
}
