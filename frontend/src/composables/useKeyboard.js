import { onMounted, onUnmounted } from 'vue'

/**
 * Global keyboard map (Linear-style). Does not hijack keys while typing.
 *   cmd/ctrl-K  -> toggle palette
 *   Esc         -> close overlays
 *   g then i/m/r-> go to Inbox / My tasks / Roadmap
 *   c           -> new issue
 */
export function useKeyboard({ onPalette, onEscape, onGo, onNew }) {
	function isTyping(e) {
		const tag = (e.target?.tagName || '').toLowerCase()
		return tag === 'input' || tag === 'textarea' || e.target?.isContentEditable
	}

	function handler(e) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault()
			onPalette?.()
			return
		}
		if (isTyping(e)) return
		if (e.key === 'Escape') onEscape?.()
		if (e.key === 'c') onNew?.()
		if (e.key === 'g') {
			const second = (ev) => {
				if (ev.key === 'i') onGo?.('inbox')
				if (ev.key === 'm') onGo?.('my-tasks')
				if (ev.key === 'r') onGo?.('roadmap')
				window.removeEventListener('keydown', second, true)
			}
			window.addEventListener('keydown', second, true)
			setTimeout(() => window.removeEventListener('keydown', second, true), 800)
		}
	}

	onMounted(() => window.addEventListener('keydown', handler))
	onUnmounted(() => window.removeEventListener('keydown', handler))
}
