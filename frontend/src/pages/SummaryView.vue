<script setup>
import { watch } from 'vue'
import { createResource, Avatar } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import Donut from '@/components/Donut.vue'
import { openDrawer } from '@/data/ui'
import { relativeTime } from '@/utils/format'

const props = defineProps({ projectKey: { type: String, required: true } })

const summary = createResource({
	url: 'projex.api.get_project_summary',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
watch(() => props.projectKey, () => summary.reload())

const CARDS = [
	{ key: 'completed', label: 'completed', sub: 'in the last 7 days', icon: 'circle-check-big' },
	{ key: 'updated', label: 'updated', sub: 'in the last 7 days', icon: 'pencil' },
	{ key: 'created', label: 'created', sub: 'in the last 7 days', icon: 'square-plus' },
	{ key: 'due_soon', label: 'due soon', sub: 'in the next 7 days', icon: 'calendar' },
]

const DOT = { gray: 'var(--gray-400)', blue: 'var(--blue-500)', amber: 'var(--amber-500)', green: 'var(--green-600)', red: 'var(--red-500)', purple: 'var(--purple-500)' }
</script>

<template>
	<div class="pjx-summary">
		<!-- stat cards -->
		<div class="pjx-cards">
			<div v-for="c in CARDS" :key="c.key" class="pjx-statcard">
				<span class="pjx-statcard__ic"><Icon :name="c.icon" :size="18" /></span>
				<div>
					<div class="pjx-statcard__n">{{ summary.data?.cards?.[c.key] ?? 0 }} {{ c.label }}</div>
					<div class="pjx-statcard__s">{{ c.sub }}</div>
				</div>
			</div>
		</div>

		<div class="pjx-sumgrid">
			<!-- status overview -->
			<div class="pjx-panel">
				<div class="pjx-panel__h">Status overview</div>
				<div class="flex items-center g-5" style="padding: 8px 4px">
					<Donut :slices="summary.data?.status_breakdown || []">
						<template #label><div class="pjx-donut__lbl">tasks</div></template>
					</Donut>
					<div class="flex col g-2" style="flex: 1">
						<div v-for="s in summary.data?.status_breakdown || []" :key="s.status_name" class="pjx-legend">
							<span class="pjx-legend__dot" :style="{ background: DOT[s.color_theme] }" />
							<span style="flex: 1">{{ s.status_name }}</span>
							<span class="pjx-dim">{{ s.count }}</span>
						</div>
						<div v-if="!(summary.data?.status_breakdown || []).length" class="pjx-dim t-sm">No work items yet.</div>
					</div>
				</div>
			</div>

			<!-- recent activity -->
			<div class="pjx-panel">
				<div class="pjx-panel__h">Recent activity</div>
				<div class="pjx-actfeed">
					<div v-for="a in summary.data?.activity || []" :key="a.name" class="pjx-actrow" @click="a.issue && openDrawer(a.issue)">
						<Avatar :label="a.actor_name" size="sm" />
						<span class="pjx-actrow__t">
							<strong>{{ a.actor_name }}</strong> {{ a.action }}
							<span v-if="a.issue_id" class="pjx-id">{{ a.issue_id }}</span>
							<span v-if="a.detail" class="pjx-dim"> {{ a.detail }}</span>
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
.pjx-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px; }
.pjx-statcard { display: flex; align-items: center; gap: 12px; border: 1px solid var(--outline-gray-1); border-radius: 10px; padding: 14px; background: var(--surface-white); }
.pjx-statcard__ic { width: 34px; height: 34px; border-radius: 8px; display: grid; place-items: center; background: var(--surface-gray-2); color: var(--ink-gray-6); flex: none; }
.pjx-statcard__n { font-size: 16px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-statcard__s { font-size: 12px; color: var(--ink-gray-5); }
.pjx-sumgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pjx-panel { border: 1px solid var(--outline-gray-1); border-radius: 10px; padding: 14px; background: var(--surface-white); }
.pjx-panel__h { font-size: 14px; font-weight: 600; color: var(--ink-gray-9); margin-bottom: 8px; }
.pjx-legend { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ink-gray-8); }
.pjx-legend__dot { width: 10px; height: 10px; border-radius: 3px; flex: none; }
.pjx-actfeed { display: flex; flex-direction: column; }
.pjx-actrow { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--outline-gray-1); cursor: pointer; font-size: 13px; }
.pjx-actrow:hover { background: var(--surface-gray-1); }
.pjx-actrow__t { flex: 1; color: var(--ink-gray-7); }
.pjx-actrow__w { color: var(--ink-gray-4); font-size: 11px; flex: none; }
@media (max-width: 900px) { .pjx-cards { grid-template-columns: repeat(2, 1fr); } .pjx-sumgrid { grid-template-columns: 1fr; } }
</style>
