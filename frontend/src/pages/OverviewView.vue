<script setup>
import { computed, watch } from 'vue'
import { createResource, Avatar, Badge, DonutChart } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import KpiStrip from '@/components/KpiStrip.vue'
import PriorityBars from '@/components/PriorityBars.vue'
import { openDrawer } from '@/data/ui'
import { relativeTime, dueLabel, isToday } from '@/utils/format'
import { cssColor } from '@/utils/chartColors'

// One analytics surface for a project: the KPIs that get glanced at daily, a
// single status chart, the activity feed, and the two operational panels
// (workload, open bugs). Replaces the old Overview + Dashboard + Reports trio,
// which each led with a boxed stat-card row and repeated the status donut.
const props = defineProps({ projectKey: { type: String, required: true } })
const emit = defineEmits(['open', 'navigate'])

// Bursts of bulk "created"/"recurred" collapse to one count row server-side,
// so the phrasing reads "created 6 tasks" instead of six identical lines.
const NOUN = { created: 'tasks', recurred: 'tasks' }
const countLabel = (a) => `${a.count} ${NOUN[a.action] || 'items'}`

const summary = createResource({
	url: 'projex.api.get_project_summary',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
const dash = createResource({
	url: 'projex.api.get_issues_dashboard',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
watch(() => props.projectKey, () => {
	summary.reload()
	dash.reload()
})

const d = computed(() => dash.data || {})
const cat = computed(() => d.value.by_category || {})
const openBugs = computed(() => d.value.open_bugs || [])
const workload = computed(() => d.value.workload || [])

// Footer rollup for the Open bugs panel: the priority mix of what's listed,
// highest-first, skipping empty buckets. Gives the panel a bottom edge to
// balance the tall status donut beside it, and surfaces the mix at a glance.
const bugMix = computed(() => {
	const counts = {}
	for (const b of openBugs.value) counts[b.priority] = (counts[b.priority] || 0) + 1
	return ['Urgent', 'High', 'Medium', 'Low', 'None']
		.filter((p) => counts[p])
		.map((p) => `${counts[p]} ${p.toLowerCase()}`)
		.join(' · ')
})
const openCount = computed(() => (cat.value.backlog || 0) + (cat.value.unstarted || 0) + (cat.value.started || 0))

// Flush KPI strip. Values are honest counts; zero reads fine here ("0 open
// bugs" is good news), so nothing is suppressed.
const kpis = computed(() => [
	{ label: 'Open', value: openCount.value },
	{ label: 'In progress', value: cat.value.started || 0 },
	{ label: 'Completed', value: cat.value.completed || 0 },
	{ label: 'Due next 7 days', value: summary.data?.cards?.due_soon ?? 0 },
	{ label: 'Open bugs', value: openBugs.value.length },
])

// Per-theme shade ramps. The base shade (first entry) matches each theme's
// single canonical color, so a theme used by one status looks unchanged.
const THEME_RAMP = {
	gray: ['var(--gray-400)', 'var(--gray-600)', 'var(--gray-300)', 'var(--gray-700)'],
	blue: ['var(--blue-500)', 'var(--blue-300)', 'var(--blue-700)'],
	amber: ['var(--amber-500)', 'var(--amber-300)', 'var(--amber-700)'],
	green: ['var(--green-600)', 'var(--green-400)', 'var(--green-800)'],
	red: ['var(--red-500)', 'var(--red-300)', 'var(--red-700)'],
	purple: ['var(--purple-500)', 'var(--purple-300)', 'var(--purple-700)'],
}
const breakdown = computed(() => (summary.data?.status_breakdown || []).filter((s) => s.count > 0))
// In the donut, hue is the only channel — so statuses sharing a theme (the
// neutral Backlog/Todo/Canceled all default to gray) would collapse to one
// indistinguishable slice. Walk each theme's statuses across distinct shades of
// that hue, in the API's status order, so every slice + legend entry is unique.
const sliceColor = computed(() => {
	const used = {}
	const map = {}
	for (const s of breakdown.value) {
		const theme = s.color_theme || 'gray'
		const ramp = THEME_RAMP[theme] || THEME_RAMP.gray
		const i = (used[theme] = (used[theme] ?? -1) + 1)
		map[s.status_name] = cssColor(ramp[i % ramp.length])
	}
	return map
})
// DonutChart sorts rows by value descending, so the colors array must follow
// that order, not the API order.
const statusChart = computed(() => ({
	data: breakdown.value.map((s) => ({ status: s.status_name, count: s.count })),
	title: 'Status',
	colors: [...breakdown.value].sort((a, b) => b.count - a.count).map((s) => sliceColor.value[s.status_name]),
	categoryColumn: 'status',
	valueColumn: 'count',
}))

// Server returns a curated digest (bursts collapsed, capped) — the full log
// lives in More → Activity. Keeps the panel from stretching past the donut.
const activity = computed(() => summary.data?.activity || [])
</script>

<template>
	<div class="ov">
		<KpiStrip :items="kpis" />

		<!-- status + open bugs: the "what needs attention now" row -->
		<div class="ov-grid">
			<section class="ov-panel ov-panel--chart">
				<template v-if="breakdown.length">
					<DonutChart :config="statusChart" />
				</template>
				<template v-else>
					<h3 class="ov-h">Status</h3>
					<div class="ov-empty">No work items yet.</div>
				</template>
			</section>

			<section class="ov-panel">
				<h3 class="ov-h">Open bugs</h3>
				<div v-for="b in openBugs" :key="b.name" class="ov-bug" @click="emit('open', b.name)">
					<PriorityBars :priority="b.priority" />
					<span class="ov-id">{{ b.issue_id }}</span>
					<span class="ov-bug__t">{{ b.title }}</span>
					<span v-if="b.due_date" class="ov-due" :class="{ 'is-today': isToday(b.due_date) }">{{ dueLabel(b.due_date) }}</span>
				</div>
				<div v-if="!openBugs.length" class="ov-empty">No open bugs.</div>
				<div v-else class="ov-foot">
					<span class="ov-foot__mix">{{ bugMix }}</span>
					<button class="ov-more" @click="emit('navigate', 'list', { typeFilter: ['Bug'] })">
						View all bugs
						<Icon name="chevron-right" :size="14" />
					</button>
				</div>
			</section>
		</div>

		<!-- workload + recent activity: team & churn -->
		<div class="ov-grid">
			<section class="ov-panel">
				<h3 class="ov-h">
					Workload
					<span class="ov-h__sub">Open story points per member (avg {{ d.workload_avg_points ?? 0 }})</span>
				</h3>
				<div v-for="w in workload" :key="w.user" class="ov-wl">
					<Avatar :label="w.name_full" size="sm" />
					<span class="ov-wl__name">{{ w.name_full }}</span>
					<Badge v-if="w.level === 'over'" theme="red" variant="subtle" size="sm">Overloaded</Badge>
					<Badge v-else-if="w.level === 'under'" theme="orange" variant="subtle" size="sm">{{ w.open ? 'Light' : 'Idle' }}</Badge>
					<div class="ov-wl__bar">
						<span :class="w.level" :style="{ width: ((d.workload_max_points ? w.points / d.workload_max_points : 0) * 100) + '%' }" />
					</div>
					<span class="ov-wl__n">{{ w.points }} pt · {{ w.open }}</span>
				</div>
				<div v-if="!workload.length" class="ov-empty">No project members yet.</div>
			</section>

			<section class="ov-panel">
				<h3 class="ov-h">Recent activity</h3>
				<div class="ov-feed">
					<div
						v-for="a in activity"
						:key="a.name"
						class="ov-act"
						:class="{ 'is-link': a.issue }"
						@click="a.issue && openDrawer(a.issue)"
					>
						<Avatar :label="a.actor_name" size="sm" />
						<span class="ov-act__t">
							<strong>{{ a.actor_name }}</strong> {{ a.action }}
							<template v-if="a.count > 1"><strong class="ov-count">{{ countLabel(a) }}</strong></template>
							<template v-else>
								<span v-if="a.issue_id" class="ov-id">{{ a.issue_id }}</span>
								<span v-if="a.detail" class="ov-dim">{{ a.detail }}</span>
							</template>
						</span>
						<span class="ov-act__w">{{ relativeTime(a.creation) }}</span>
					</div>
					<div v-if="!activity.length" class="ov-blank">
						<Icon name="activity" :size="18" />
						<span>No activity yet</span>
					</div>
				</div>
				<button v-if="activity.length" class="ov-more" @click="emit('navigate', 'activity')">
					View all activity
					<Icon name="chevron-right" :size="14" />
				</button>
			</section>
		</div>
	</div>
</template>

<style scoped>
.ov { padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; letter-spacing: 0.02em; }

.ov-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
/* Espresso dashboard widgets sit on bordered white surfaces, not flush. */
.ov-panel { min-width: 0; border: 1px solid var(--outline-gray-1); border-radius: 10px; background: var(--surface-white); padding: 16px 18px; }
.ov-panel--chart { min-height: 260px; display: flex; flex-direction: column; justify-content: center; }
.ov-h { font-size: 15px; font-weight: 600; color: var(--ink-gray-8); letter-spacing: 0.005em; margin-bottom: 12px; }
.ov-h__sub { font-size: 13px; font-weight: 400; color: var(--ink-gray-5); letter-spacing: 0.02em; margin-inline-start: 6px; }
.ov-empty { font-size: 13px; color: var(--ink-gray-5); padding: 8px 0; }

/* shared bits */
.ov-id { font-size: 12px; color: var(--ink-gray-5); font-variant-numeric: tabular-nums; }
.ov-dim { color: var(--ink-gray-5); }

/* activity feed */
.ov-feed { display: flex; flex-direction: column; }
.ov-act { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--outline-gray-1); font-size: 13px; }
.ov-act:last-child { border-bottom: 0; }
.ov-act.is-link { cursor: pointer; }
.ov-act.is-link:hover { background: var(--surface-gray-1); }
.ov-act__t { flex: 1; min-width: 0; color: var(--ink-gray-7); }
.ov-act__t .ov-id { margin: 0 5px; }
.ov-act__w { flex: none; color: var(--ink-gray-4); font-size: 11px; }
.ov-blank { display: flex; align-items: center; gap: 8px; color: var(--ink-gray-5); font-size: 13px; padding: 24px 0; }
.ov-count { color: var(--ink-gray-7); }
.ov-foot { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--outline-gray-1); font-size: 12px; color: var(--ink-gray-5); }
.ov-foot .ov-more { margin-top: 0; }
.ov-more { display: inline-flex; align-items: center; gap: 2px; margin-top: 8px; padding: 0; background: none; border: 0; cursor: pointer; font-size: 12px; color: var(--ink-gray-5); }
.ov-more:hover { color: var(--ink-gray-8); }

/* workload */
.ov-wl { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; color: var(--ink-gray-8); }
.ov-wl__name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ov-wl__bar { width: 110px; height: 6px; border-radius: 4px; background: var(--surface-gray-2); overflow: hidden; flex: none; }
.ov-wl__bar span { display: block; height: 100%; border-radius: 4px; background: var(--blue-500); }
.ov-wl__bar span.over { background: var(--red-500); }
.ov-wl__bar span.under { background: var(--amber-500); }
.ov-wl__n { width: 64px; text-align: right; font-variant-numeric: tabular-nums; color: var(--ink-gray-6); flex: none; font-size: 12px; }

/* open bugs */
.ov-bug { display: flex; align-items: center; gap: 10px; padding: 7px 8px; margin: 0 -8px; border-radius: 7px; cursor: pointer; font-size: 13px; }
.ov-bug:hover { background: var(--surface-gray-1); }
.ov-bug__t { flex: 1; min-width: 0; color: var(--ink-gray-8); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ov-due { flex: none; font-size: 12px; color: var(--ink-gray-5); }
.ov-due.is-today { color: var(--ink-amber-3); }

@media (max-width: 900px) {
	.ov-grid { grid-template-columns: 1fr; }
}
</style>
