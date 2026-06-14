<script setup>
import { ref } from 'vue'
import Icon from './Icon.vue'
import { tweaks, setTweak } from '@/composables/useTweaks'

const open = ref(false)
const DENSITIES = ['compact', 'regular', 'comfy']
const ACCENTS = [
	{ v: 'var(--blue-500)', c: '#0289F7' },
	{ v: 'var(--violet-500)', c: '#6846E3' },
	{ v: 'var(--green-600)', c: '#278F5E' },
	{ v: 'var(--orange-500)', c: '#E86C13' },
	{ v: 'var(--gray-900)', c: '#171717' },
]
</script>

<template>
	<div class="pjx-tweaks">
		<button class="pjx-tweaks__fab" title="Appearance" @click="open = !open">
			<Icon name="sliders-horizontal" :size="16" />
		</button>
		<div v-if="open" class="pjx-tweaks__panel">
			<div class="pjx-tweaks__row">
				<span>Dark mode</span>
				<button
					class="pjx-toggle"
					:data-on="tweaks.dark ? '1' : '0'"
					@click="setTweak('dark', !tweaks.dark)"
				>
					<i />
				</button>
			</div>
			<div class="pjx-tweaks__row col">
				<span>Density</span>
				<div class="pjx-seg">
					<button
						v-for="d in DENSITIES"
						:key="d"
						:class="{ on: tweaks.density === d }"
						@click="setTweak('density', d)"
					>
						{{ d }}
					</button>
				</div>
			</div>
			<div class="pjx-tweaks__row col">
				<span>Accent</span>
				<div class="pjx-accents">
					<button
						v-for="a in ACCENTS"
						:key="a.v"
						class="pjx-accents__sw"
						:class="{ on: tweaks.accent === a.v }"
						:style="{ background: a.c }"
						@click="setTweak('accent', a.v)"
					/>
				</div>
			</div>
			<div class="pjx-tweaks__row">
				<span>Presence avatars</span>
				<button
					class="pjx-toggle"
					:data-on="tweaks.presence ? '1' : '0'"
					@click="setTweak('presence', !tweaks.presence)"
				>
					<i />
				</button>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-tweaks {
	position: fixed;
	right: 16px;
	bottom: 16px;
	z-index: 300;
}
.pjx-tweaks__fab {
	width: 38px;
	height: 38px;
	border-radius: 9999px;
	border: 1px solid var(--outline-gray-2);
	background: var(--surface-white);
	box-shadow: var(--shadow-md);
	display: grid;
	place-items: center;
	cursor: pointer;
	color: var(--ink-gray-7);
}
.pjx-tweaks__panel {
	position: absolute;
	right: 0;
	bottom: 46px;
	width: 240px;
	background: var(--surface-modal);
	border: 1px solid var(--outline-gray-2);
	border-radius: 12px;
	box-shadow: var(--shadow-lg);
	padding: 12px;
	display: flex;
	flex-direction: column;
	gap: 12px;
}
.pjx-tweaks__row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	font-size: 13px;
	color: var(--ink-gray-7);
}
.pjx-tweaks__row.col {
	flex-direction: column;
	align-items: stretch;
	gap: 6px;
}
.pjx-toggle {
	position: relative;
	width: 32px;
	height: 18px;
	border: 0;
	border-radius: 999px;
	background: var(--surface-gray-4);
	cursor: pointer;
	padding: 0;
}
.pjx-toggle[data-on='1'] {
	background: var(--green-500);
}
.pjx-toggle i {
	position: absolute;
	top: 2px;
	left: 2px;
	width: 14px;
	height: 14px;
	border-radius: 50%;
	background: #fff;
	transition: transform 0.15s;
}
.pjx-toggle[data-on='1'] i {
	transform: translateX(14px);
}
.pjx-seg {
	display: flex;
	background: var(--surface-gray-2);
	border-radius: 8px;
	padding: 2px;
}
.pjx-seg button {
	flex: 1;
	border: 0;
	background: transparent;
	border-radius: 6px;
	font-size: 12px;
	padding: 4px;
	cursor: pointer;
	color: var(--ink-gray-6);
	text-transform: capitalize;
}
.pjx-seg button.on {
	background: var(--surface-white);
	color: var(--ink-gray-9);
	box-shadow: var(--shadow-sm);
}
.pjx-accents {
	display: flex;
	gap: 8px;
}
.pjx-accents__sw {
	width: 24px;
	height: 24px;
	border-radius: 9999px;
	border: 2px solid transparent;
	cursor: pointer;
}
.pjx-accents__sw.on {
	border-color: var(--ink-gray-9);
}
</style>
