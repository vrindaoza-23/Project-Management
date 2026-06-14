<script setup>
import { ref, computed, watch } from 'vue'
import { createResource, Dropdown, Button, DatePicker } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import PriorityBars from '@/components/PriorityBars.vue'
import AvatarStack from '@/components/AvatarStack.vue'
import StatusDot from '@/components/StatusDot.vue'
import { dueLabel, isToday } from '@/utils/format'

const props = defineProps({
	projectKey: { type: String, required: true },
	issues: { type: Array, default: () => [] },
	statuses: { type: Array, default: () => [] },
})
const emit = defineEmits(['open', 'changed'])

const pickers = createResource({
	url: 'projex.api.get_pickers',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
const updater = createResource({ url: 'projex.api.update_issue' })
const cycleCreate = createResource({ url: 'projex.api.create_cycle' })
const cycleState = createResource({ url: 'projex.api.update_cycle' })

watch(() => props.projectKey, () => pickers.reload())

const STATE_THEME = { Active: 'green', Upcoming: 'blue', Completed: 'gray' }
const completedStatuses = computed(
	() => new Set(props.statuses.filter((s) => ['completed', 'cancelled'].includes(s.category)).map((s) => s.name)),
)
const cycles = computed(() => pickers.data?.cycles || [])

function points(list) {
	return list.reduce((sum, i) => sum + (Number(i.estimate) || 0), 0)
}
function donePoints(list) {
	return list.filter((i) => completedStatuses.value.has(i.status)).reduce((s, i) => s + (Number(i.estimate) || 0), 0)
}

const backlog = computed(() => props.issues.filter((i) => !i.cycle))
const sprints = computed(() =>
	cycles.value.map((c) => {
		const items = props.issues.filter((i) => i.cycle === c.name)
		return { ...c, items, total: points(items), done: donePoints(items) }
	}),
)

// "Move to" menu for any issue: backlog or a sprint.
function moveOptions(issue) {
	const opts = [{ label: 'Backlog', icon: 'inbox', onClick: () => moveTo(issue, null) }]
	for (const c of cycles.value) {
		opts.push({ label: c.cycle_name, icon: 'calendar-range', onClick: () => moveTo(issue, c.name) })
	}
	return opts
}
async function moveTo(issue, cycleName) {
	if (issue.cycle === cycleName) return
	const prev = issue.cycle
	issue.cycle = cycleName // optimistic
	try {
		await updater.submit({ name: issue.name, fields: JSON.stringify({ cycle: cycleName }) })
		emit('changed')
	} catch (e) {
		issue.cycle = prev
		console.error('[projex] move to sprint failed', e)
	}
}

const adding = ref(false)
const draft = ref({ name: '', start: '', end: '' })
async function addSprint() {
	if (!draft.value.name.trim()) return
	await cycleCreate.submit({
		project: props.projectKey,
		cycle_name: draft.value.name.trim(),
		start_date: draft.value.start || null,
		end_date: draft.value.end || null,
		state: 'Upcoming',
	})
	draft.value = { name: '', start: '', end: '' }
	adding.value = false
	pickers.reload()
}
async function setState(cycle, state) {
	await cycleState.submit({ name: cycle.name, fields: JSON.stringify({ state }) })
	pickers.reload()
}
function statusMeta(name) {
	return props.statuses.find((s) => s.name === name)
}
</script>

<template>
	<div class="pjx-backlog">
		<!-- Sprints -->
		<section class="pjx-bl__col">
			<div class="pjx-bl__head">
				<h3 class="pjx-bl__title"><Icon name="calendar-range" :size="15" /> Sprints</h3>
				<Button variant="subtle" theme="gray" size="sm" @click="adding = !adding">
					<template #prefix><Icon name="plus" :size="13" /></template>New sprint
				</Button>
			</div>

			<div v-if="adding" class="pjx-bl__newsprint">
				<input v-model="draft.name" class="input" placeholder="Sprint name (e.g. Sprint 4)" />
				<div class="flex g-2">
					<DatePicker v-model="draft.start" placeholder="Start date" />
					<DatePicker v-model="draft.end" placeholder="End date" />
				</div>
				<div class="flex g-2">
					<Button variant="solid" theme="gray" size="sm" :loading="cycleCreate.loading" @click="addSprint">Create</Button>
					<Button variant="ghost" theme="gray" size="sm" @click="adding = false">Cancel</Button>
				</div>
			</div>

			<div v-for="s in sprints" :key="s.name" class="pjx-sprint">
				<div class="pjx-sprint__head">
					<span class="pjx-state" :data-theme="STATE_THEME[s.state] || 'gray'">{{ s.state }}</span>
					<span class="pjx-sprint__name">{{ s.cycle_name }}</span>
					<span class="pjx-sprint__pts">{{ s.done }}/{{ s.total }} pts</span>
					<Dropdown
						:options="[
							{ label: 'Start sprint', onClick: () => setState(s, 'Active') },
							{ label: 'Mark completed', onClick: () => setState(s, 'Completed') },
							{ label: 'Move to upcoming', onClick: () => setState(s, 'Upcoming') },
						]"
					>
						<button class="pjx-iconbtn"><Icon name="ellipsis" :size="15" /></button>
					</Dropdown>
				</div>
				<div v-if="s.items.length" class="pjx-sprint__pbar">
					<span :style="{ width: (s.total ? (s.done / s.total) * 100 : 0) + '%' }" />
				</div>
				<div class="pjx-bl__list">
					<div v-for="i in s.items" :key="i.name" class="pjx-blrow" @click="emit('open', i.name)">
						<PriorityBars :priority="i.priority" />
						<StatusDot :status="statusMeta(i.status)" :size="8" />
						<span class="pjx-id">{{ i.issue_id }}</span>
						<span class="pjx-blrow__t">{{ i.title }}</span>
						<span v-if="i.due_date" class="pjx-due" :class="{ 'is-today': isToday(i.due_date) }">{{ dueLabel(i.due_date) }}</span>
						<span v-if="i.estimate" class="pjx-pts">{{ i.estimate }}</span>
						<AvatarStack v-if="i.assignees && i.assignees.length" :users="i.assignees" :size="18" />
						<Dropdown :options="moveOptions(i)">
							<button class="pjx-iconbtn" title="Move" @click.stop><Icon name="arrow-right-left" :size="13" /></button>
						</Dropdown>
					</div>
					<div v-if="!s.items.length" class="pjx-bl__empty">No tasks in this sprint yet.</div>
				</div>
			</div>
			<div v-if="!sprints.length && !adding" class="pjx-bl__empty">No sprints yet — create one to start planning.</div>
		</section>

		<!-- Backlog -->
		<section class="pjx-bl__col">
			<div class="pjx-bl__head">
				<h3 class="pjx-bl__title"><Icon name="inbox" :size="15" /> Backlog</h3>
				<span class="pjx-sprint__pts">{{ backlog.length }} tasks · {{ points(backlog) }} pts</span>
			</div>
			<div class="pjx-bl__list">
				<div v-for="i in backlog" :key="i.name" class="pjx-blrow" @click="emit('open', i.name)">
					<PriorityBars :priority="i.priority" />
					<StatusDot :status="statusMeta(i.status)" :size="8" />
					<span class="pjx-id">{{ i.issue_id }}</span>
					<span class="pjx-blrow__t">{{ i.title }}</span>
					<span v-if="i.estimate" class="pjx-pts">{{ i.estimate }}</span>
					<AvatarStack v-if="i.assignees && i.assignees.length" :users="i.assignees" :size="18" />
					<Dropdown :options="moveOptions(i)">
						<button class="pjx-iconbtn" title="Move to sprint" @click.stop><Icon name="arrow-right" :size="13" /></button>
					</Dropdown>
				</div>
				<div v-if="!backlog.length" class="pjx-bl__empty">Backlog is empty.</div>
			</div>
		</section>
	</div>
</template>

<style scoped>
.pjx-backlog { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; padding: 16px; overflow-y: auto; }
.pjx-bl__col { min-width: 0; }
.pjx-bl__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.pjx-bl__title { display: flex; align-items: center; gap: 7px; font-size: 14px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-sprint { border: 1px solid var(--outline-gray-2); border-radius: 10px; margin-bottom: 12px; background: var(--surface-white); }
.pjx-sprint__head { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--outline-gray-1); }
.pjx-state { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; background: var(--surface-gray-3); color: var(--ink-gray-7); }
.pjx-state[data-theme='green'] { background: var(--surface-green-2, #e6f4ea); color: var(--ink-green-3, #137333); }
.pjx-state[data-theme='blue'] { background: var(--surface-blue-2, #e8f0fe); color: var(--ink-blue-3, #1a73e8); }
.pjx-sprint__name { font-weight: 600; font-size: 13px; color: var(--ink-gray-9); flex: 1; }
.pjx-sprint__pts { font-size: 12px; color: var(--ink-gray-5); }
.pjx-sprint__pbar { height: 4px; background: var(--surface-gray-2); }
.pjx-sprint__pbar span { display: block; height: 100%; background: var(--green-600); }
.pjx-bl__list { padding: 4px; }
.pjx-blrow { display: flex; align-items: center; gap: 8px; padding: 7px 8px; border-radius: 7px; cursor: pointer; font-size: 13px; }
.pjx-blrow:hover { background: var(--surface-gray-1); }
.pjx-blrow__t { flex: 1; color: var(--ink-gray-8); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pjx-pts { min-width: 20px; height: 18px; padding: 0 6px; display: inline-grid; place-items: center; border-radius: 5px; background: var(--surface-gray-2); font-size: 11px; font-weight: 600; color: var(--ink-gray-7); }
.pjx-iconbtn { border: 0; background: transparent; cursor: pointer; color: var(--ink-gray-5); width: 24px; height: 24px; display: grid; place-items: center; border-radius: 6px; }
.pjx-iconbtn:hover { background: var(--surface-gray-3); color: var(--ink-gray-8); }
.pjx-bl__empty { padding: 14px 10px; font-size: 13px; color: var(--ink-gray-4); }
.pjx-bl__newsprint { display: flex; flex-direction: column; gap: 8px; padding: 12px; border: 1px dashed var(--outline-gray-2); border-radius: 10px; margin-bottom: 12px; }
@media (max-width: 980px) { .pjx-backlog { grid-template-columns: 1fr; } }
</style>
