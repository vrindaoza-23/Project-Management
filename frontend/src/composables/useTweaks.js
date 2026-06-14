import { reactive, watchEffect } from 'vue'

const STORAGE_KEY = 'projex:tweaks'

const defaults = {
	dark: false,
	density: 'regular', // compact | regular | comfy
	accent: 'var(--blue-500)',
	showAI: true,
	presence: true,
}

function load() {
	try {
		return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') }
	} catch {
		return { ...defaults }
	}
}

export const tweaks = reactive(load())

export function setTweak(key, value) {
	tweaks[key] = value
}

export function useTweaks() {
	// Apply theme/density/accent to the document; persist on change.
	watchEffect(() => {
		const root = document.documentElement
		root.setAttribute('data-theme', tweaks.dark ? 'dark' : 'light')
		const app = document.querySelector('.fu-app')
		if (app) {
			app.setAttribute('data-density', tweaks.density)
			if (tweaks.accent) {
				app.style.setProperty('--accent', tweaks.accent)
				app.style.setProperty('--accent-ink', tweaks.accent)
				app.style.setProperty(
					'--accent-surface',
					`color-mix(in srgb, ${tweaks.accent} 13%, var(--surface-white))`,
				)
			}
		}
		localStorage.setItem(STORAGE_KEY, JSON.stringify(tweaks))
	})
	return { tweaks, setTweak }
}
