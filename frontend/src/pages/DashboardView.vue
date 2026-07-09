<script setup>
import { computed, watch } from 'vue'
import { createResource, Button, Avatar } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import PriorityBars from '@/components/PriorityBars.vue'
import { openReportBug } from '@/data/ui'
import { dueLabel, isToday } from '@/utils/format'

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

const TYPE_COLOR = { Task: 'var(--gray-500)', Bug: 'var(--red-500)', Story: 'var(--green-600)', Epic: 'var(--purple-500)' }
const PRIO_COLOR = { Urgent: 'var(--red-500)', High: 'var(--orange-500)', Medium: 'var(--amber-500)', Low: 'var(--blue-500)', None: 'var(--gray-400)' }
function pct(n, total) {
	return total ? Math.round((n / total) * 100) : 0
}
const totalType = computed(() => byType.value.reduce((s, x) => s + x.count, 0))
const maxPrio = computed(() => Math.max(1, ...byPriority.value.map((p) => p.count)))
</script>

<template>
	<div class="pjx-dash">
		<div class="pjx-dash__bar">
			<h3 class="pjx-dash__title">Issues dashboard</h3>
			<Button variant="solid" theme="blue" @click="openReportBug(projectKey)">
				<template #prefix><Icon name="bug" :size="14" /></template>Report bug
			</Button>
		</div>

		<div class="pjx-cards">
			<div class="pjx-statcard"><span class="pjx-statcard__ic"><Icon name="layers" :size="18" /></span>
				<div><div class="pjx-statcard__n">{{ d.total ?? 0 }}</div><div class="pjx-statcard__s">total issues</div></div></div>
			<div class="pjx-statcard"><span class="pjx-statcard__ic"><Icon name="circle-dot" :size="18" /></span>
				<div><div class="pjx-statcard__n">{{ openCount }}</div><div class="pjx-statcard__s">open</div></div></div>
			<div class="pjx-statcard"><span class="pjx-statcard__ic" style="background: var(--surface-red-2, #fde8e8); color: var(--red-600)"><Icon name="bug" :size="18" /></span>
				<div><div class="pjx-statcard__n">{{ openBugs.length }}</div><div class="pjx-statcard__s">open bugs</div></div></div>
			<div class="pjx-statcard"><span class="pjx-statcard__ic" style="background: var(--surface-green-2, #e6f4ea); color: var(--green-600)"><Icon name="circle-check-big" :size="18" /></span>
				<div><div class="pjx-statcard__n">{{ cat.completed || 0 }}</div><div class="pjx-statcard__s">completed</div></div></div>
		</div>

		<div class="pjx-dgrid">
			<div class="pjx-panel">
				<div class="pjx-panel__h">By type</div>
				<div v-for="t in byType" :key="t.label" class="pjx-mrow">
					<span class="pjx-mrow__dot" :style="{ background: TYPE_COLOR[t.label] || 'var(--gray-500)' }" />
					<span style="flex: 1">{{ t.label }}</span>
					<span class="pjx-dim">{{ t.count }}</span>
					<div class="pjx-mrow__bar"><span :style="{ width: pct(t.count, totalType) + '%', background: TYPE_COLOR[t.label] }" /></div>
				</div>
				<div v-if="!byType.length" class="pjx-dim t-sm">No issues yet.</div>
			</div>

			<div class="pjx-panel">
				<div class="pjx-panel__h">By priority</div>
				<div v-for="p in byPriority" :key="p.label" class="pjx-mrow">
					<span style="flex: 1">{{ p.label }}</span>
					<span class="pjx-dim">{{ p.count }}</span>
					<div class="pjx-mrow__bar"><span :style="{ width: pct(p.count, maxPrio) + '%', background: PRIO_COLOR[p.label] }" /></div>
				</div>
				<div v-if="!byPriority.length" class="pjx-dim t-sm">No issues yet.</div>
			</div>

			<div class="pjx-panel pjx-panel--wide">
				<div class="pjx-panel__h">Open bugs</div>
				<div v-for="b in openBugs" :key="b.name" class="pjx-bugrow" @click="emit('open', b.name)">
					<PriorityBars :priority="b.priority" />
					<span class="pjx-id">{{ b.issue_id }}</span>
					<span class="pjx-bugrow__t">{{ b.title }}</span>
					<span v-if="b.due_date" class="pjx-due" :class="{ 'is-today': isToday(b.due_date) }">{{ dueLabel(b.due_date) }}</span>
				</div>
				<div v-if="!openBugs.length" class="pjx-dim t-sm" style="padding: 10px 2px">No open bugs. 🎉</div>
			</div>

			<div class="pjx-panel">
				<div class="pjx-panel__h">
					Workload &amp; capacity
					<span class="pjx-dim t-xs" style="font-weight: 400">— open story points per member (avg {{ d.workload_avg_points ?? 0 }})</span>
				</div>
				<div v-for="w in workload" :key="w.user" class="pjx-wl">
					<Avatar :label="w.name_full" size="sm" />
					<span class="pjx-wl__name">{{ w.name_full }}</span>
					<span v-if="w.level === 'over'" class="pjx-wl__flag over">Overloaded</span>
					<span v-else-if="w.level === 'under'" class="pjx-wl__flag under">{{ w.open ? 'Light' : 'Idle' }}</span>
					<div class="pjx-wl__bar">
						<span :class="w.level" :style="{ width: ((d.workload_max_points ? w.points / d.workload_max_points : 0) * 100) + '%' }" />
					</div>
					<span class="pjx-wl__n">{{ w.points }} pt · {{ w.open }}</span>
				</div>
				<div v-if="!workload.length" class="pjx-dim t-sm">No project members yet.</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-dash { padding: 16px; overflow-y: auto; }
.pjx-dash__bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.pjx-dash__title { font-size: 16px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px; }
.pjx-statcard { display: flex; align-items: center; gap: 12px; border: 1px solid var(--outline-gray-1); border-radius: 10px; padding: 14px; background: var(--surface-white); }
.pjx-statcard__ic { width: 34px; height: 34px; border-radius: 8px; display: grid; place-items: center; background: var(--surface-gray-2); color: var(--ink-gray-6); flex: none; }
.pjx-statcard__n { font-size: 20px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-statcard__s { font-size: 12px; color: var(--ink-gray-5); }
.pjx-dgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pjx-panel { border: 1px solid var(--outline-gray-1); border-radius: 10px; padding: 14px; background: var(--surface-white); }
.pjx-panel--wide { grid-column: 1 / -1; }
.pjx-panel__h { font-size: 14px; font-weight: 600; color: var(--ink-gray-9); margin-bottom: 10px; }
.pjx-mrow { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; color: var(--ink-gray-8); }
.pjx-mrow__dot { width: 10px; height: 10px; border-radius: 3px; flex: none; }
.pjx-mrow__bar { width: 120px; height: 6px; border-radius: 4px; background: var(--surface-gray-2); overflow: hidden; flex: none; }
.pjx-mrow__bar span { display: block; height: 100%; border-radius: 4px; }
.pjx-wl { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; color: var(--ink-gray-8); }
.pjx-wl__name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pjx-wl__bar { width: 110px; height: 6px; border-radius: 4px; background: var(--surface-gray-2); overflow: hidden; flex: none; }
.pjx-wl__bar span { display: block; height: 100%; border-radius: 4px; background: var(--blue-500); }
.pjx-wl__bar span.over { background: var(--red-500); }
.pjx-wl__bar span.under { background: var(--amber-500); }
.pjx-wl__n { width: 64px; text-align: right; font-variant-numeric: tabular-nums; color: var(--ink-gray-6); flex: none; }
.pjx-wl__flag { font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 999px; flex: none; }
.pjx-wl__flag.over { background: var(--surface-red-2, #fee2e2); color: var(--ink-red-3, #c5221f); }
.pjx-wl__flag.under { background: var(--surface-amber-2, #fef3c7); color: var(--ink-amber-3, #b06000); }
.pjx-bugrow { display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 7px; cursor: pointer; font-size: 13px; }
.pjx-bugrow:hover { background: var(--surface-gray-1); }
.pjx-bugrow__t { flex: 1; color: var(--ink-gray-8); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 900px) { .pjx-cards { grid-template-columns: repeat(2, 1fr); } .pjx-dgrid { grid-template-columns: 1fr; } }
</style>
