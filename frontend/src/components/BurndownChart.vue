<script setup>
import { ref, computed, watch } from 'vue'
import { createResource, AxisChart } from 'frappe-ui'
import SelectField from './SelectField.vue'
import { cssColor } from '@/utils/chartColors'

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

const chart = computed(() => ({
	data: series.value.map((p) => ({ date: p.date, ideal: p.ideal, remaining: p.remaining })),
	title: '',
	colors: ['var(--gray-400)', 'var(--blue-500)'].map(cssColor),
	xAxis: { key: 'date', type: 'time', timeGrain: 'day' },
	yAxis: {},
	series: [
		{ name: 'ideal', type: 'line', lineType: 'dashed', lineWidth: 2 },
		{ name: 'remaining', type: 'line', lineWidth: 2 },
	],
}))

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
			<div class="pjx-card__h" style="margin: 0">Sprint burndown</div>
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
			<div class="pjx-burn__chart">
				<AxisChart :config="chart" />
			</div>
			<div class="pjx-burn__cap">
				{{ lastRemaining ?? '—' }} of {{ total }} pts remaining
				<span class="pjx-dim" style="margin-left: auto">{{ fmtDate(data.start_date) }} → {{ fmtDate(data.end_date) }}</span>
			</div>
		</template>
	</div>
</template>

<style scoped>
.pjx-burn__top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; gap: 12px; }
.pjx-card__h { font-size: 14px; font-weight: 500; color: var(--ink-gray-8); }
.pjx-burn__chart { height: 260px; }
.pjx-burn__cap { display: flex; align-items: center; margin-top: 2px; font-size: 12px; color: var(--ink-gray-6); }
.pjx-burn__empty { padding: 24px 8px; font-size: 13px; color: var(--ink-gray-4); }
</style>
