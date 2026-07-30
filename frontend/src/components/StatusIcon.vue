<script setup>
import { computed } from 'vue'

// Linear-style status glyph: a 16px SVG whose shape encodes the workflow
// category (backlog → dashed ring, todo → empty ring, in-progress → filled
// wedge, done → check, cancelled → cross) and whose color follows the status'
// theme. Richer than StatusDot; used as the leading mark on every task row.
const props = defineProps({
	status: { type: Object, default: null }, // { category, color_theme, status_name }
	size: { type: Number, default: 15 },
})

const COLOR = {
	gray: 'var(--gray-500)',
	blue: 'var(--blue-500)',
	amber: 'var(--amber-500)',
	green: 'var(--green-600)',
	red: 'var(--red-500)',
	purple: 'var(--purple-500)',
}
const category = computed(() => props.status?.category || 'unstarted')
const color = computed(() => COLOR[props.status?.color_theme] || 'var(--gray-500)')
</script>

<template>
	<svg
		:width="size"
		:height="size"
		viewBox="0 0 16 16"
		fill="none"
		class="pjx-sicon"
	>
		<title>{{ status?.status_name }}</title>
		<!-- backlog: dashed ring -->
		<circle
			v-if="category === 'backlog'"
			cx="8" cy="8" r="6"
			:stroke="color" stroke-width="1.6" stroke-dasharray="1.6 2.4"
			opacity="0.85"
		/>
		<!-- completed: filled disc + check -->
		<template v-else-if="category === 'completed'">
			<circle cx="8" cy="8" r="7" :fill="color" />
			<path d="M5 8.3l2 2 4-4.4" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
		</template>
		<!-- cancelled: filled disc + cross -->
		<template v-else-if="category === 'cancelled'">
			<circle cx="8" cy="8" r="7" :fill="color" />
			<path d="M5.6 5.6l4.8 4.8M10.4 5.6l-4.8 4.8" stroke="white" stroke-width="1.5" stroke-linecap="round" />
		</template>
		<!-- started: ring + progress wedge (~50%) -->
		<template v-else-if="category === 'started'">
			<circle cx="8" cy="8" r="6" :stroke="color" stroke-width="1.6" />
			<circle
				cx="8" cy="8" r="3"
				:stroke="color" stroke-width="6"
				stroke-dasharray="9.4 18.8" transform="rotate(-90 8 8)"
			/>
		</template>
		<!-- unstarted (Todo): empty ring -->
		<circle v-else cx="8" cy="8" r="6" :stroke="color" stroke-width="1.6" />
	</svg>
</template>

<style scoped>
.pjx-sicon { flex: none; display: block; }
</style>
