<script setup>
import { Select, SettingsBody, SettingsHeader, SettingsRow, Switch } from 'frappe-ui'
import { tweaks, setTweak } from '@/composables/useTweaks'

const DENSITY_OPTIONS = [
	{ label: 'Compact', value: 'compact' },
	{ label: 'Regular', value: 'regular' },
	{ label: 'Comfy', value: 'comfy' },
]
const ACCENTS = [
	{ v: 'var(--blue-500)', c: '#0289F7' },
	{ v: 'var(--violet-500)', c: '#6846E3' },
	{ v: 'var(--green-600)', c: '#278F5E' },
	{ v: 'var(--orange-500)', c: '#E86C13' },
	{ v: 'var(--gray-900)', c: '#171717' },
]
</script>

<template>
	<SettingsHeader title="Preferences" />
	<SettingsBody>
		<div class="divide-y divide-outline-gray-1">
			<SettingsRow title="Dark mode" description="Use the dark interface theme.">
				<Switch :model-value="tweaks.dark" @update:model-value="(v) => setTweak('dark', v)" />
			</SettingsRow>
			<SettingsRow title="Density" description="How compact lists and boards feel.">
				<Select
					:options="DENSITY_OPTIONS"
					:model-value="tweaks.density"
					@update:model-value="(v) => setTweak('density', v)"
				/>
			</SettingsRow>
			<SettingsRow title="Accent color" description="Used for highlights and emphasis.">
				<div class="flex gap-2">
					<button
						v-for="a in ACCENTS"
						:key="a.v"
						class="pjx-accent"
						:class="{ on: tweaks.accent === a.v }"
						:style="{ background: a.c }"
						:aria-label="`Accent ${a.c}`"
						@click="setTweak('accent', a.v)"
					/>
				</div>
			</SettingsRow>
			<SettingsRow title="Presence avatars" description="Show who's viewing a project in its header.">
				<Switch :model-value="tweaks.presence" @update:model-value="(v) => setTweak('presence', v)" />
			</SettingsRow>
		</div>
	</SettingsBody>
</template>

<style scoped>
.pjx-accent {
	width: 22px;
	height: 22px;
	border-radius: 9999px;
	border: 2px solid transparent;
	cursor: pointer;
}
.pjx-accent.on {
	border-color: var(--ink-gray-9);
}
</style>
