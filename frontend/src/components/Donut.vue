<script setup>
import { computed } from 'vue'

const props = defineProps({
	slices: { type: Array, default: () => [] }, // [{ label, count, color_theme }]
	size: { type: Number, default: 160 },
	thickness: { type: Number, default: 22 },
})

const COLOR = {
	gray: 'var(--gray-400)',
	blue: 'var(--blue-500)',
	amber: 'var(--amber-500)',
	green: 'var(--green-600)',
	red: 'var(--red-500)',
	purple: 'var(--purple-500)',
}

const total = computed(() => props.slices.reduce((s, x) => s + x.count, 0))
const radius = computed(() => (props.size - props.thickness) / 2)
const circ = computed(() => 2 * Math.PI * radius.value)

const segments = computed(() => {
	let offset = 0
	return props.slices
		.filter((s) => s.count > 0)
		.map((s) => {
			const frac = total.value ? s.count / total.value : 0
			const seg = {
				color: COLOR[s.color_theme] || 'var(--gray-400)',
				dash: frac * circ.value,
				gap: circ.value - frac * circ.value,
				offset: -offset * circ.value,
			}
			offset += frac
			return seg
		})
})
</script>

<template>
	<div class="pjx-donut" :style="{ width: size + 'px', height: size + 'px' }">
		<svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
			<circle
				:cx="size / 2"
				:cy="size / 2"
				:r="radius"
				fill="none"
				stroke="var(--surface-gray-2)"
				:stroke-width="thickness"
			/>
			<circle
				v-for="(seg, i) in segments"
				:key="i"
				:cx="size / 2"
				:cy="size / 2"
				:r="radius"
				fill="none"
				:stroke="seg.color"
				:stroke-width="thickness"
				:stroke-dasharray="`${seg.dash} ${seg.gap}`"
				:stroke-dashoffset="seg.offset"
				:transform="`rotate(-90 ${size / 2} ${size / 2})`"
				stroke-linecap="butt"
			/>
		</svg>
		<div class="pjx-donut__center">
			<div class="pjx-donut__num">{{ total }}</div>
			<slot name="label"><div class="pjx-donut__lbl">Total</div></slot>
		</div>
	</div>
</template>

<style scoped>
.pjx-donut {
	position: relative;
	flex: none;
}
.pjx-donut__center {
	position: absolute;
	inset: 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
}
.pjx-donut__num {
	font-size: 26px;
	font-weight: 600;
	color: var(--ink-gray-9);
	line-height: 1;
}
.pjx-donut__lbl {
	font-size: 11px;
	color: var(--ink-gray-5);
	margin-top: 2px;
}
</style>
