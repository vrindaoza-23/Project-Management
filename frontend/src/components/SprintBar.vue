<script setup>
import { ref, computed } from 'vue'
import { Select, Button } from 'frappe-ui'
import Icon from './Icon.vue'
import StartSprintDialog from './StartSprintDialog.vue'
import CompleteSprintDialog from './CompleteSprintDialog.vue'
import { sumPoints, donePoints } from '@/utils/scrum'

const props = defineProps({
	projectKey: { type: String, required: true },
	scope: { type: String, default: 'active' }, // 'active' | 'all' | 'backlog' | <cycle name>
	cycles: { type: Array, default: () => [] },
	activeCycle: { type: Object, default: null },
	canManage: { type: Boolean, default: false },
	statuses: { type: Array, default: () => [] },
	scopeIssues: { type: Array, default: () => [] }, // issues in the resolved sprint
})
const emit = defineEmits(['update:scope', 'changed'])

const startOpen = ref(false)
const completeOpen = ref(false)

const options = computed(() => {
	const opts = []
	if (props.activeCycle) opts.push({ label: 'Active sprint', value: 'active' })
	opts.push({ label: 'All issues', value: 'all' })
	opts.push({ label: 'Backlog (no sprint)', value: 'backlog' })
	for (const c of props.cycles) {
		opts.push({ label: `${c.cycle_name} · ${c.state}`, value: c.name })
	}
	return opts
})

// The concrete cycle the current scope points at (null for all/backlog).
const cycle = computed(() => {
	if (props.scope === 'all' || props.scope === 'backlog') return null
	if (props.scope === 'active') return props.activeCycle || null
	return props.cycles.find((c) => c.name === props.scope) || null
})

const upcomingOptions = computed(() =>
	props.cycles.filter((c) => c.state === 'Upcoming').map((c) => ({ value: c.name, label: c.cycle_name })),
)
const completedSet = computed(
	() => new Set(props.statuses.filter((s) => ['completed', 'cancelled'].includes(s.category)).map((s) => s.name)),
)
const committed = computed(() => sumPoints(props.scopeIssues))
const donePts = computed(() => donePoints(props.scopeIssues, completedSet.value))
const pct = computed(() => (committed.value ? Math.round((donePts.value / committed.value) * 100) : 0))

function fmtRange(c) {
	const f = (d) => (d ? new Date(d + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : null)
	if (c.start_date && c.end_date) return `${f(c.start_date)} – ${f(c.end_date)}`
	return 'No dates set'
}
const daysLeft = computed(() => {
	const c = cycle.value
	if (!c?.end_date) return null
	const end = new Date(c.end_date + 'T23:59:59')
	return Math.ceil((end - new Date()) / 86400000)
})

function afterChange() {
	emit('changed')
}
</script>

<template>
	<div class="pjx-sprintbar">
		<div class="pjx-sprintbar__row">
			<Icon name="calendar-range" :size="14" class="ink-5" />
			<div class="pjx-sprintbar__sel">
				<Select :model-value="scope" :options="options" @update:model-value="(v) => emit('update:scope', v)" />
			</div>

			<template v-if="cycle">
				<span class="pjx-state" :data-theme="cycle.state === 'Active' ? 'green' : cycle.state === 'Upcoming' ? 'blue' : 'gray'">{{ cycle.state }}</span>
				<span v-if="cycle.start_date || cycle.end_date" class="pjx-sprintbar__dates">{{ fmtRange(cycle) }}</span>
				<span v-if="daysLeft !== null && cycle.state === 'Active'" class="pjx-sprintbar__days" :class="{ 'is-over': daysLeft < 0 }">
					{{ daysLeft < 0 ? `${-daysLeft}d overdue` : daysLeft === 0 ? 'Last day' : `${daysLeft} days left` }}
				</span>
				<span class="pjx-sprintbar__meter">
					<span class="pjx-sprintbar__pbar"><span :style="{ width: pct + '%' }" /></span>
					<span class="pjx-sprintbar__pts">{{ donePts }}/{{ committed }} pts</span>
				</span>
				<span style="flex: 1" />
				<Button v-if="canManage && cycle.state === 'Upcoming'" variant="solid" theme="green" size="sm" @click="startOpen = true">Start sprint</Button>
				<Button v-else-if="canManage && cycle.state === 'Active'" variant="subtle" theme="gray" size="sm" @click="completeOpen = true">Complete sprint</Button>
			</template>
			<template v-else>
				<span style="flex: 1" />
			</template>
		</div>

		<div v-if="cycle?.goal" class="pjx-sprintbar__goal"><Icon name="target" :size="13" /> {{ cycle.goal }}</div>

		<StartSprintDialog :open="startOpen" :cycle="cycle" @close="startOpen = false" @started="afterChange" />
		<CompleteSprintDialog
			:open="completeOpen"
			:cycle="cycle"
			:issues="scopeIssues"
			:statuses="statuses"
			:upcoming="upcomingOptions"
			@close="completeOpen = false"
			@completed="afterChange"
		/>
	</div>
</template>

<style scoped>
.pjx-sprintbar {
	padding: 8px 16px;
	border-bottom: 1px solid var(--outline-gray-1);
}
.pjx-sprintbar__row {
	display: flex;
	align-items: center;
	gap: 10px;
}
.pjx-sprintbar__sel {
	width: 200px;
}
.pjx-state {
	font-size: 11px;
	font-weight: 600;
	padding: 2px 8px;
	border-radius: 9999px;
	background: var(--surface-gray-3);
	color: var(--ink-gray-7);
}
.pjx-state[data-theme='green'] { background: var(--surface-green-2, #e6f4ea); color: var(--ink-green-3, #137333); }
.pjx-state[data-theme='blue'] { background: var(--surface-blue-2, #e8f0fe); color: var(--ink-blue-3, #1a73e8); }
.pjx-sprintbar__dates { font-size: 12px; color: var(--ink-gray-5); }
.pjx-sprintbar__days { font-size: 12px; font-weight: 600; color: var(--ink-amber-3, #b06000); }
.pjx-sprintbar__days.is-over { color: var(--ink-red-3, #c5221f); }
.pjx-sprintbar__meter { display: flex; align-items: center; gap: 8px; }
.pjx-sprintbar__pbar { width: 120px; height: 6px; border-radius: 3px; background: var(--surface-gray-2); overflow: hidden; }
.pjx-sprintbar__pbar span { display: block; height: 100%; background: var(--green-600); }
.pjx-sprintbar__pts { font-size: 12px; color: var(--ink-gray-5); white-space: nowrap; }
.pjx-sprintbar__goal { display: flex; align-items: center; gap: 6px; margin-top: 6px; font-size: 12px; color: var(--ink-gray-6); }
</style>
