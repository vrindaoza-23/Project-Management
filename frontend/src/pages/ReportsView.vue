<script setup>
import { computed, watch } from 'vue'
import { createResource, NumberChart, DonutChart, AxisChart } from 'frappe-ui'
import BurndownChart from '@/components/BurndownChart.vue'
import SprintReview from '@/components/SprintReview.vue'
import { cssColor } from '@/utils/chartColors'

const emit = defineEmits(['open'])

const props = defineProps({ projectKey: { type: String, required: true } })

const reports = createResource({
	url: 'projex.api.get_project_reports',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
watch(() => props.projectKey, () => reports.reload())

const DOT = { gray: 'var(--gray-400)', blue: 'var(--blue-500)', amber: 'var(--amber-500)', green: 'var(--green-600)', red: 'var(--red-500)', purple: 'var(--purple-500)' }

const distribution = computed(() => (reports.data?.distribution || []).filter((d) => d.count > 0))
// DonutChart sorts rows by value descending, so the colors array must follow
// that order, not the API order.
const distributionChart = computed(() => ({
	data: distribution.value.map((d) => ({ status: d.label, count: d.count })),
	title: 'Status distribution',
	colors: [...distribution.value].sort((a, b) => b.count - a.count).map((d) => cssColor(DOT[d.color_theme] || 'var(--gray-400)')),
	categoryColumn: 'status',
	valueColumn: 'count',
}))

const velocity = computed(() => reports.data?.velocity || [])
const velocityChart = computed(() => ({
	data: velocity.value.map((v) => ({ cycle: v.cycle, points: v.points })),
	title: 'Velocity by cycle',
	subtitle: 'Story points completed per sprint',
	colors: [cssColor('var(--blue-500)')],
	xAxis: { key: 'cycle', type: 'category' },
	yAxis: {},
	series: [{ name: 'points', type: 'bar', showDataLabels: true }],
}))

const AGE_COLORS = ['var(--green-600)', 'var(--gray-400)', 'var(--amber-500)', 'var(--red-500)']
const agingChart = computed(() => {
	const a = reports.data?.aging || {}
	return {
		data: [
			{ bucket: '≤3d', count: a.le3 || 0 },
			{ bucket: '4–7d', count: a.d4_7 || 0 },
			{ bucket: '8–14d', count: a.d8_14 || 0 },
			{ bucket: '>14d', count: a.gt14 || 0 },
		],
		title: 'Status aging',
		subtitle: 'Open tasks by time in current status',
		colors: AGE_COLORS.map(cssColor),
		xAxis: { key: 'bucket', type: 'category' },
		yAxis: {},
		series: [{ name: 'count', type: 'bar', showDataLabels: true, echartOptions: { colorBy: 'data' } }],
	}
})

const throughput = computed(() => reports.data?.throughput || [])
function weekLabel(iso) {
	return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
const throughputChart = computed(() => ({
	data: throughput.value.map((t) => ({ week: weekLabel(t.week), count: t.count })),
	title: 'Throughput',
	subtitle: 'Tasks completed per week',
	colors: [cssColor('var(--green-600)')],
	xAxis: { key: 'week', type: 'category' },
	yAxis: {},
	series: [{ name: 'count', type: 'bar', showDataLabels: true }],
}))

const rework = computed(() => reports.data?.rework || {})
const cycleStat = computed(() => ({ title: 'Avg cycle time (created → done)', value: reports.data?.avg_cycle_time ?? 0, suffix: 'd' }))
const reworkStat = computed(() => ({ title: 'Rework rate (tasks bounced back)', value: rework.value.rework_rate ?? 0, suffix: '%' }))
</script>

<template>
	<div class="pjx-reports">
		<div class="pjx-card pjx-card--list" style="margin-bottom: 12px">
			<BurndownChart :project-key="projectKey" />
		</div>
		<div class="pjx-card pjx-card--list" style="margin-bottom: 12px">
			<SprintReview :project-key="projectKey" @open="emit('open', $event)" />
		</div>

		<div class="pjx-rgrid" style="margin-bottom: 12px">
			<div class="pjx-card">
				<NumberChart :config="cycleStat" />
				<div class="pjx-card__cap">{{ reports.data?.total_completed ?? 0 }} completed tasks measured</div>
			</div>
			<div class="pjx-card">
				<NumberChart :config="reworkStat" />
				<div class="pjx-card__cap">
					<b>{{ rework.total_reopens ?? 0 }}</b> reopened · <b>{{ rework.total_rejections ?? 0 }}</b> sent back ·
					<b>{{ rework.reworked_tasks ?? 0 }}</b> tasks affected
				</div>
			</div>
		</div>

		<div class="pjx-rgrid">
			<div class="pjx-card pjx-card--chart">
				<DonutChart v-if="distribution.length" :config="distributionChart" />
				<div v-else class="pjx-card__empty">No work items yet.</div>
			</div>
			<div class="pjx-card pjx-card--chart">
				<AxisChart v-if="velocity.length" :config="velocityChart" />
				<div v-else class="pjx-card__empty">No cycles yet.</div>
			</div>
			<div class="pjx-card pjx-card--chart">
				<AxisChart :config="agingChart" />
			</div>
			<div class="pjx-card pjx-card--chart">
				<AxisChart v-if="throughput.length" :config="throughputChart" />
				<div v-else class="pjx-card__empty">Nothing completed yet.</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-reports { padding: 16px; overflow-y: auto; }
.pjx-rgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pjx-card { border: 1px solid var(--outline-gray-1); border-radius: 8px; background: var(--surface-base); overflow: hidden; }
.pjx-card--chart { height: 300px; }
.pjx-card--list { padding: 14px 16px; }
/* Match the ECharts title styles (getTitleOptions) so hand-built panels and
   chart panels read as one family. */
.pjx-card__cap { padding: 0 24px 16px; font-size: 12px; color: var(--ink-gray-5); }
.pjx-card__cap b { color: var(--ink-gray-8); font-weight: 500; }
.pjx-card__empty { display: flex; align-items: center; height: 100%; font-size: 13px; color: var(--ink-gray-5); padding: 0 16px; }
@media (max-width: 900px) { .pjx-rgrid { grid-template-columns: 1fr; } }
</style>
