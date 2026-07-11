<script setup>
import { computed, watch } from 'vue'
import { createResource, Avatar, NumberChart, DonutChart } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import { openDrawer } from '@/data/ui'
import { relativeTime } from '@/utils/format'
import { cssColor } from '@/utils/chartColors'

const props = defineProps({ projectKey: { type: String, required: true } })

const summary = createResource({
	url: 'projex.api.get_project_summary',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
watch(() => props.projectKey, () => summary.reload())

const stats = computed(() => {
	const cards = summary.data?.cards || {}
	return [
		{ title: 'Completed in last 7 days', value: cards.completed ?? 0 },
		{ title: 'Updated in last 7 days', value: cards.updated ?? 0 },
		{ title: 'Created in last 7 days', value: cards.created ?? 0 },
		{ title: 'Due in next 7 days', value: cards.due_soon ?? 0 },
	]
})

const DOT = { gray: 'var(--gray-400)', blue: 'var(--blue-500)', amber: 'var(--amber-500)', green: 'var(--green-600)', red: 'var(--red-500)', purple: 'var(--purple-500)' }

const breakdown = computed(() => (summary.data?.status_breakdown || []).filter((s) => s.count > 0))
// DonutChart sorts rows by value descending, so the colors array must follow
// that order, not the API order.
const statusChart = computed(() => ({
	data: breakdown.value.map((s) => ({ status: s.status_name, count: s.count })),
	title: 'Status overview',
	colors: [...breakdown.value].sort((a, b) => b.count - a.count).map((s) => cssColor(DOT[s.color_theme] || 'var(--gray-400)')),
	categoryColumn: 'status',
	valueColumn: 'count',
}))
</script>

<template>
	<div class="pjx-summary">
		<!-- stat cards -->
		<div class="pjx-cards">
			<div v-for="s in stats" :key="s.title" class="pjx-card">
				<NumberChart :config="s" />
			</div>
		</div>

		<div class="pjx-sumgrid">
			<!-- status overview -->
			<div class="pjx-card pjx-card--chart">
				<DonutChart v-if="breakdown.length" :config="statusChart" />
				<template v-else>
					<div class="pjx-card__h" style="padding: 14px 16px 0">Status overview</div>
					<div class="pjx-card__empty">No work items yet.</div>
				</template>
			</div>

			<!-- recent activity -->
			<div class="pjx-card pjx-card--list">
				<div class="pjx-card__h">Recent activity</div>
				<div class="pjx-actfeed">
					<div v-for="a in summary.data?.activity || []" :key="a.name" class="pjx-actrow" @click="a.issue && openDrawer(a.issue)">
						<Avatar :label="a.actor_name" size="sm" />
						<span class="pjx-actrow__t">
							<strong>{{ a.actor_name }}</strong> {{ a.action }}
							<span v-if="a.issue_id" class="pjx-id" style="margin: 0 5px">{{ a.issue_id }}</span>
							<span v-if="a.detail" class="pjx-dim">{{ a.detail }}</span>
						</span>
						<span class="pjx-actrow__w">{{ relativeTime(a.creation) }}</span>
					</div>
					<div v-if="!(summary.data?.activity || []).length" class="pjx-soon" style="height: 160px">
						<span class="pjx-soon__icon"><Icon name="activity" :size="18" /></span>
						<div class="t-sm ink-5">No activity yet</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-summary { padding: 16px; overflow-y: auto; }
.pjx-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }
.pjx-card { border: 1px solid var(--outline-gray-1); border-radius: 8px; background: var(--surface-base); overflow: hidden; }
.pjx-card--chart { min-height: 300px; }
.pjx-card--list { padding: 14px 16px; }
/* Match the ECharts title styles (getTitleOptions) so hand-built panels and
   chart panels read as one family. */
.pjx-card__h { font-size: 14px; font-weight: 500; color: var(--ink-gray-8); margin-bottom: 8px; }
.pjx-card__empty { display: flex; align-items: center; min-height: 40px; font-size: 13px; color: var(--ink-gray-5); padding: 8px 16px; }
.pjx-sumgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pjx-actfeed { display: flex; flex-direction: column; }
.pjx-actrow { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--outline-gray-1); cursor: pointer; font-size: 13px; }
.pjx-actrow:last-child { border-bottom: 0; }
.pjx-actrow:hover { background: var(--surface-gray-1); }
.pjx-actrow__t { flex: 1; color: var(--ink-gray-7); }
.pjx-actrow__w { color: var(--ink-gray-4); font-size: 11px; flex: none; }
@media (max-width: 900px) { .pjx-cards { grid-template-columns: repeat(2, 1fr); } .pjx-sumgrid { grid-template-columns: 1fr; } }
</style>
