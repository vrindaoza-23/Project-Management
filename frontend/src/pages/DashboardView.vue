<script setup>
import { computed, watch } from 'vue'
import { createResource, Button, Avatar, Badge, NumberChart, DonutChart, AxisChart } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import PriorityBars from '@/components/PriorityBars.vue'
import { openReportBug } from '@/data/ui'
import { dueLabel, isToday } from '@/utils/format'
import { cssColor } from '@/utils/chartColors'

const props = defineProps({ projectKey: { type: String, required: true } })
const emit = defineEmits(['open'])

const dash = createResource({
	url: 'projex.api.get_issues_dashboard',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
watch(() => props.projectKey, () => dash.reload())

const d = computed(() => dash.data || {})
const byType = computed(() => d.value.by_type || [])
const byPriority = computed(() => (d.value.by_priority || []).filter((p) => p.count > 0))
const openBugs = computed(() => d.value.open_bugs || [])
const workload = computed(() => d.value.workload || [])
const cat = computed(() => d.value.by_category || {})
const openCount = computed(() => (cat.value.backlog || 0) + (cat.value.unstarted || 0) + (cat.value.started || 0))

// Task is the most common type; giving it a real color (not grey) keeps the
// "By type" donut legible for the common single-type project. Grey stays the
// fallback for unknown types only.
const TYPE_COLOR = { Task: 'var(--blue-500)', Bug: 'var(--red-500)', Story: 'var(--green-600)', Epic: 'var(--purple-500)' }
const PRIO_COLOR = { Urgent: 'var(--red-500)', High: 'var(--orange-500)', Medium: 'var(--amber-500)', Low: 'var(--blue-500)', None: 'var(--gray-400)' }

const stats = computed(() => [
	{ title: 'Total issues', value: d.value.total ?? 0 },
	{ title: 'Open', value: openCount.value },
	{ title: 'Open bugs', value: openBugs.value.length },
	{ title: 'Completed', value: cat.value.completed || 0 },
])

// DonutChart sorts rows by value descending, so the colors array must follow
// that order, not the API order.
const typeChart = computed(() => ({
	data: byType.value.map((t) => ({ type: t.label, count: t.count })),
	title: 'By type',
	colors: [...byType.value].sort((a, b) => b.count - a.count).map((t) => cssColor(TYPE_COLOR[t.label] || 'var(--gray-500)')),
	categoryColumn: 'type',
	valueColumn: 'count',
}))

const priorityChart = computed(() => ({
	data: byPriority.value.map((p) => ({ priority: p.label, count: p.count })),
	title: 'By priority',
	colors: byPriority.value.map((p) => cssColor(PRIO_COLOR[p.label] || 'var(--gray-400)')),
	xAxis: { key: 'priority', type: 'category' },
	yAxis: {},
	swapXY: true,
	series: [{ name: 'count', type: 'bar', showDataLabels: true, echartOptions: { colorBy: 'data' } }],
}))
</script>

<template>
	<div class="pjx-dash">
		<div class="pjx-dash__bar">
			<h3 class="pjx-dash__title">Issues dashboard</h3>
			<Button variant="subtle" theme="gray" @click="openReportBug(projectKey)">
				<template #prefix><Icon name="bug" :size="14" /></template>Report bug
			</Button>
		</div>

		<div class="pjx-cards">
			<div v-for="s in stats" :key="s.title" class="pjx-card">
				<NumberChart :config="s" />
			</div>
		</div>

		<div class="pjx-dgrid">
			<div class="pjx-card pjx-card--chart">
				<DonutChart v-if="byType.length" :config="typeChart" />
				<div v-else class="pjx-card__empty">No issues yet.</div>
			</div>

			<div class="pjx-card pjx-card--chart">
				<AxisChart v-if="byPriority.length" :config="priorityChart" />
				<div v-else class="pjx-card__empty">No issues yet.</div>
			</div>

			<div class="pjx-card pjx-card--list pjx-card--wide">
				<div class="pjx-card__h">Open bugs</div>
				<div v-for="b in openBugs" :key="b.name" class="pjx-bugrow" @click="emit('open', b.name)">
					<PriorityBars :priority="b.priority" />
					<span class="pjx-id">{{ b.issue_id }}</span>
					<span class="pjx-bugrow__t">{{ b.title }}</span>
					<span v-if="b.due_date" class="pjx-due" :class="{ 'is-today': isToday(b.due_date) }">{{ dueLabel(b.due_date) }}</span>
				</div>
				<div v-if="!openBugs.length" class="pjx-card__empty">No open bugs. 🎉</div>
			</div>

			<div class="pjx-card pjx-card--list">
				<div class="pjx-card__h">
					Workload &amp; capacity
					<span class="pjx-card__sub">Open story points per member (avg {{ d.workload_avg_points ?? 0 }})</span>
				</div>
				<div v-for="w in workload" :key="w.user" class="pjx-wl">
					<Avatar :label="w.name_full" size="sm" />
					<span class="pjx-wl__name">{{ w.name_full }}</span>
					<Badge v-if="w.level === 'over'" theme="red" variant="subtle" size="sm">Overloaded</Badge>
					<Badge v-else-if="w.level === 'under'" theme="orange" variant="subtle" size="sm">{{ w.open ? 'Light' : 'Idle' }}</Badge>
					<div class="pjx-wl__bar">
						<span :class="w.level" :style="{ width: ((d.workload_max_points ? w.points / d.workload_max_points : 0) * 100) + '%' }" />
					</div>
					<span class="pjx-wl__n">{{ w.points }} pt · {{ w.open }}</span>
				</div>
				<div v-if="!workload.length" class="pjx-card__empty">No project members yet.</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-dash { padding: 16px; overflow-y: auto; }
.pjx-dash__bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.pjx-dash__title { font-size: 16px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }
.pjx-card { border: 1px solid var(--outline-gray-1); border-radius: 8px; background: var(--surface-base); overflow: hidden; }
.pjx-card--chart { height: 300px; }
.pjx-card--list { padding: 14px 16px; }
.pjx-card--wide { grid-column: 1 / -1; }
/* Match the ECharts title styles (getTitleOptions) so hand-built panels and
   chart panels read as one family. */
.pjx-card__h { font-size: 14px; font-weight: 500; color: var(--ink-gray-8); margin-bottom: 10px; }
.pjx-card__sub { font-size: 13px; font-weight: 400; color: var(--ink-gray-6); margin-inline-start: 4px; }
.pjx-card__empty { display: flex; align-items: center; height: 100%; min-height: 40px; font-size: 13px; color: var(--ink-gray-5); padding: 0 16px; }
.pjx-card--list .pjx-card__empty { padding: 0; }
.pjx-dgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pjx-wl { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; color: var(--ink-gray-8); }
.pjx-wl__name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pjx-wl__bar { width: 110px; height: 6px; border-radius: 4px; background: var(--surface-gray-2); overflow: hidden; flex: none; }
.pjx-wl__bar span { display: block; height: 100%; border-radius: 4px; background: var(--blue-500); }
.pjx-wl__bar span.over { background: var(--red-500); }
.pjx-wl__bar span.under { background: var(--amber-500); }
.pjx-wl__n { width: 64px; text-align: right; font-variant-numeric: tabular-nums; color: var(--ink-gray-6); flex: none; font-size: 12px; }
.pjx-bugrow { display: flex; align-items: center; gap: 10px; padding: 7px 8px; margin: 0 -8px; border-radius: 7px; cursor: pointer; font-size: 13px; }
.pjx-bugrow:hover { background: var(--surface-gray-1); }
.pjx-bugrow__t { flex: 1; color: var(--ink-gray-8); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 900px) { .pjx-cards { grid-template-columns: repeat(2, 1fr); } .pjx-dgrid { grid-template-columns: 1fr; } }
</style>
