<script setup>
import { ref, computed, watch } from 'vue'
import { createResource } from 'frappe-ui'
import SelectField from './SelectField.vue'

const props = defineProps({ projectKey: { type: String, required: true } })

const selected = ref(null)
const cycles = createResource({
	url: 'projex.api.get_pickers',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
const burndown = createResource({
	url: 'projex.api.get_burndown',
	makeParams: () => ({ project: props.projectKey, cycle: selected.value || undefined }),
	auto: true,
})
watch(() => props.projectKey, () => { selected.value = null; cycles.reload(); burndown.reload() })
watch(selected, () => burndown.reload())

const cycleOptions = computed(() =>
	(cycles.data?.cycles || []).map((c) => ({ value: c.name, label: c.cycle_name })),
)
const data = computed(() => burndown.data || {})
const series = computed(() => data.value.series || [])
const total = computed(() => data.value.total_points || 0)

// Geometry (viewBox 0..100 x, 0..100 y; y inverted so 0 pts = bottom).
const W = 100
const H = 100
function x(i) {
	const n = series.value.length
	return n <= 1 ? 0 : (i / (n - 1)) * W
}
function y(v) {
	if (total.value <= 0) return H
	return H - (v / total.value) * H
}
const idealPath = computed(() => {
	if (!series.value.length) return ''
	return series.value.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(2)},${y(p.ideal).toFixed(2)}`).join(' ')
})
const actualPath = computed(() => {
	const pts = series.value.filter((p) => p.remaining !== null && p.remaining !== undefined)
	if (!pts.length) return ''
	return pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(series.value.indexOf(p)).toFixed(2)},${y(p.remaining).toFixed(2)}`).join(' ')
})
const lastRemaining = computed(() => {
	const pts = series.value.filter((p) => p.remaining !== null && p.remaining !== undefined)
	return pts.length ? pts[pts.length - 1].remaining : null
})
function fmtDate(iso) {
	return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
</script>

<template>
	<div class="pjx-burn">
		<div class="pjx-burn__top">
			<div class="pjx-panel__h" style="margin: 0">Sprint burndown</div>
			<div style="width: 180px">
				<SelectField
					:options="cycleOptions"
					:model-value="selected || data.cycle"
					placeholder="Select sprint"
					@change="(v) => (selected = v)"
				/>
			</div>
		</div>

		<div v-if="data.needs_dates" class="pjx-burn__empty">
			This sprint needs a start and end date for a burndown. Add them in Project settings → Cycles.
		</div>
		<div v-else-if="!series.length" class="pjx-burn__empty">No sprint data yet.</div>
		<template v-else>
			<svg class="pjx-burn__svg" viewBox="0 0 100 100" preserveAspectRatio="none">
				<line x1="0" y1="0" x2="0" y2="100" class="pjx-burn__axis" />
				<line x1="0" y1="100" x2="100" y2="100" class="pjx-burn__axis" />
				<path :d="idealPath" class="pjx-burn__ideal" />
				<path :d="actualPath" class="pjx-burn__actual" />
			</svg>
			<div class="pjx-burn__legend">
				<span><i class="dot ideal" /> Ideal</span>
				<span><i class="dot actual" /> Remaining ({{ lastRemaining ?? '—' }} of {{ total }} pts)</span>
				<span class="pjx-dim" style="margin-left: auto">{{ fmtDate(data.start_date) }} → {{ fmtDate(data.end_date) }}</span>
			</div>
		</template>
	</div>
</template>

<style scoped>
.pjx-burn__top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; gap: 12px; }
.pjx-burn__svg { width: 100%; height: 200px; overflow: visible; }
.pjx-burn__axis { stroke: var(--outline-gray-2); stroke-width: 0.4; vector-effect: non-scaling-stroke; }
.pjx-burn__ideal { fill: none; stroke: var(--ink-gray-4); stroke-width: 1.4; stroke-dasharray: 3 2; vector-effect: non-scaling-stroke; }
.pjx-burn__actual { fill: none; stroke: var(--blue-500); stroke-width: 2; vector-effect: non-scaling-stroke; stroke-linejoin: round; }
.pjx-burn__legend { display: flex; align-items: center; gap: 16px; margin-top: 10px; font-size: 12px; color: var(--ink-gray-6); }
.pjx-burn__legend .dot { display: inline-block; width: 10px; height: 3px; border-radius: 2px; margin-right: 5px; vertical-align: middle; }
.pjx-burn__legend .dot.ideal { background: var(--ink-gray-4); }
.pjx-burn__legend .dot.actual { background: var(--blue-500); }
.pjx-burn__empty { padding: 24px 8px; font-size: 13px; color: var(--ink-gray-4); }
</style>
