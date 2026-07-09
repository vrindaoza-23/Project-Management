<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { createResource, Dropdown, Button, DatePicker, FormControl } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import PriorityBars from '@/components/PriorityBars.vue'
import AvatarStack from '@/components/AvatarStack.vue'
import StatusDot from '@/components/StatusDot.vue'
import StartSprintDialog from '@/components/StartSprintDialog.vue'
import CompleteSprintDialog from '@/components/CompleteSprintDialog.vue'
import { dueLabel, isToday, ageChip } from '@/utils/format'
import { sumPoints, donePoints } from '@/utils/scrum'

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
const reports = createResource({
	url: 'projex.api.get_project_reports',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
const updater = createResource({ url: 'projex.api.update_issue' })
const cycleCreate = createResource({ url: 'projex.api.create_cycle' })
const cycleState = createResource({ url: 'projex.api.update_cycle' })

watch(() => props.projectKey, () => { pickers.reload(); reports.reload() })

const STATE_THEME = { Active: 'green', Upcoming: 'blue', Completed: 'gray' }
const canManage = computed(() => !!pickers.data?.can_manage)
const completedStatuses = computed(
	() => new Set(props.statuses.filter((s) => ['completed', 'cancelled'].includes(s.category)).map((s) => s.name)),
)
const cycles = computed(() => pickers.data?.cycles || [])

// Capacity hint: average completed points across past sprints with any work.
const avgVelocity = computed(() => {
	const v = (reports.data?.velocity || []).filter((x) => x.issues > 0)
	if (!v.length) return 0
	return Math.round(v.reduce((s, x) => s + (x.points || 0), 0) / v.length)
})

const backlog = computed(() => props.issues.filter((i) => !i.cycle))
const sprints = computed(() =>
	cycles.value.map((c) => {
		const items = props.issues.filter((i) => i.cycle === c.name)
		return { ...c, items, total: sumPoints(items), done: donePoints(items, completedStatuses.value) }
	}),
)
const upcomingOptions = computed(() =>
	cycles.value.filter((c) => c.state === 'Upcoming').map((c) => ({ value: c.name, label: c.cycle_name })),
)

function statusMeta(name) {
	return props.statuses.find((s) => s.name === name)
}
function age(i) {
	return ageChip(i.status_changed_on, i.modified)
}

// "Move to" menu (kept as an accessible fallback to drag).
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

// --------------------------------------------------------------------------- //
// Pointer drag: move an issue between backlog and sprints (mirrors BoardView).
// Drop target is the nearest [data-cycle] container ('' = backlog).
// --------------------------------------------------------------------------- //
const THRESHOLD = 5
const overCycle = ref(null)
let drag = null

const suppressClick = ref(false)
function onPickup(issue, event) {
	const row = event.currentTarget.closest('.pjx-blrow')
	drag = { issue, srcEl: row, startX: event.clientX, startY: event.clientY, offX: 0, offY: 0, ghost: null, started: false }
	window.addEventListener('pointermove', onMove)
	window.addEventListener('pointerup', onUp, { once: true })
}
function onRowClick(issue) {
	// A drag just finished on this row → swallow the trailing click.
	if (suppressClick.value) {
		suppressClick.value = false
		return
	}
	emit('open', issue.name)
}
function onMove(e) {
	if (!drag) return
	if (!drag.started) {
		if (Math.hypot(e.clientX - drag.startX, e.clientY - drag.startY) < THRESHOLD) return
		drag.started = true
		document.body.classList.add('pjx-dragging')
		const rect = drag.srcEl.getBoundingClientRect()
		drag.offX = e.clientX - rect.left
		drag.offY = e.clientY - rect.top
		const g = drag.srcEl.cloneNode(true)
		g.classList.add('pjx-card--ghost')
		g.style.width = `${rect.width}px`
		document.body.appendChild(g)
		drag.ghost = g
		drag.srcEl.classList.add('pjx-card--dragsrc')
	}
	if (drag.ghost) drag.ghost.style.transform = `translate(${e.clientX - drag.offX}px, ${e.clientY - drag.offY}px) rotate(2deg)`
	overCycle.value = containerAt(e.clientX, e.clientY)
}
function containerAt(x, y) {
	const el = document.elementFromPoint(x, y)
	const c = el && el.closest('[data-cycle]')
	return c ? c.getAttribute('data-cycle') : null
}
async function onUp(e) {
	window.removeEventListener('pointermove', onMove)
	const d = drag
	drag = null
	if (!d) return
	if (!d.started) return // a click on the grip; the row's @click handles opening
	if (d.ghost) d.ghost.remove()
	d.srcEl.classList.remove('pjx-card--dragsrc')
	document.body.classList.remove('pjx-dragging')
	suppressClick.value = true // a real drag happened — don't let it open the task
	const target = containerAt(e.clientX, e.clientY)
	overCycle.value = null
	if (target === null) return
	const cycleName = target === '' ? null : target
	const issue = props.issues.find((i) => i.name === d.issue.name)
	if (issue) moveTo(issue, cycleName)
}
onBeforeUnmount(() => {
	window.removeEventListener('pointermove', onMove)
	if (drag && drag.ghost) drag.ghost.remove()
	document.body.classList.remove('pjx-dragging')
})

// New sprint
const adding = ref(false)
const draft = ref({ name: '', start: '', end: '', goal: '' })
async function addSprint() {
	if (!draft.value.name.trim()) return
	await cycleCreate.submit({
		project: props.projectKey,
		cycle_name: draft.value.name.trim(),
		start_date: draft.value.start || null,
		end_date: draft.value.end || null,
		state: 'Upcoming',
		goal: draft.value.goal || null,
	})
	draft.value = { name: '', start: '', end: '', goal: '' }
	adding.value = false
	pickers.reload()
}
async function revertToUpcoming(cycle) {
	await cycleState.submit({ name: cycle.name, fields: JSON.stringify({ state: 'Upcoming' }) })
	pickers.reload()
}

// Start / Complete dialogs
const startOpen = ref(false)
const completeOpen = ref(false)
const dialogCycle = ref(null)
function openStart(s) {
	dialogCycle.value = s
	startOpen.value = true
}
function openComplete(s) {
	dialogCycle.value = s
	completeOpen.value = true
}
function afterChange() {
	pickers.reload()
	emit('changed')
}
const completeIssues = computed(() =>
	dialogCycle.value ? props.issues.filter((i) => i.cycle === dialogCycle.value.name) : [],
)
</script>

<template>
	<div class="pjx-backlog">
		<!-- Sprints -->
		<section class="pjx-bl__col">
			<div class="pjx-bl__head">
				<h3 class="pjx-bl__title"><Icon name="calendar-range" :size="15" /> Sprints</h3>
				<div class="flex items-center g-2">
					<span v-if="avgVelocity" class="pjx-cap" title="Average completed points per past sprint">⚡ velocity ~{{ avgVelocity }} pts</span>
					<Button v-if="canManage" variant="subtle" theme="gray" size="sm" @click="adding = !adding">
						<template #prefix><Icon name="plus" :size="13" /></template>New sprint
					</Button>
				</div>
			</div>

			<div v-if="adding" class="pjx-bl__newsprint">
				<FormControl v-model="draft.name" type="text" placeholder="Sprint name (e.g. Sprint 4)" />
				<FormControl v-model="draft.goal" type="text" placeholder="Sprint goal (optional)" />
				<div class="flex g-2">
					<DatePicker v-model="draft.start" placeholder="Start date" />
					<DatePicker v-model="draft.end" placeholder="End date" />
				</div>
				<div class="flex g-2">
					<Button variant="solid" theme="blue" size="sm" :loading="cycleCreate.loading" @click="addSprint">Create</Button>
					<Button variant="ghost" theme="gray" size="sm" @click="adding = false">Cancel</Button>
				</div>
			</div>

			<div
				v-for="s in sprints"
				:key="s.name"
				class="pjx-sprint"
				:data-cycle="s.name"
				:class="{ 'is-over': overCycle === s.name }"
			>
				<div class="pjx-sprint__head">
					<span class="pjx-state" :data-theme="STATE_THEME[s.state] || 'gray'">{{ s.state }}</span>
					<span class="pjx-sprint__name">{{ s.cycle_name }}</span>
					<span class="pjx-sprint__pts">
						{{ s.done }}/{{ s.total }} pts
						<template v-if="avgVelocity && s.state !== 'Completed'">
							· <span :class="{ 'pjx-over': s.total > avgVelocity }">cap {{ avgVelocity }}</span>
						</template>
					</span>
					<Button v-if="canManage && s.state === 'Upcoming'" variant="subtle" theme="green" size="sm" @click="openStart(s)">Start</Button>
					<Button v-else-if="canManage && s.state === 'Active'" variant="subtle" theme="gray" size="sm" @click="openComplete(s)">Complete</Button>
					<Dropdown
						v-if="canManage"
						:options="[{ label: 'Move to upcoming', onClick: () => revertToUpcoming(s) }]"
					>
						<button class="pjx-iconbtn"><Icon name="ellipsis" :size="15" /></button>
					</Dropdown>
				</div>
				<div v-if="s.goal" class="pjx-sprint__goal"><Icon name="target" :size="12" /> {{ s.goal }}</div>
				<div v-if="s.items.length" class="pjx-sprint__pbar">
					<span :style="{ width: (s.total ? (s.done / s.total) * 100 : 0) + '%' }" />
				</div>
				<div class="pjx-bl__list">
					<div v-for="i in s.items" :key="i.name" class="pjx-blrow" @click="onRowClick(i)">
						<button class="pjx-grip" title="Drag to move" @pointerdown.stop="(e) => onPickup(i, e)" @click.stop>
							<Icon name="grip-vertical" :size="13" />
						</button>
						<PriorityBars :priority="i.priority" />
						<StatusDot :status="statusMeta(i.status)" :size="8" />
						<span class="pjx-id">{{ i.issue_id }}</span>
						<span class="pjx-blrow__t">{{ i.title }}</span>
						<span v-if="i.reopen_count" class="pjx-rwk" :title="`Reopened ${i.reopen_count}×`"><Icon name="undo-2" :size="12" />{{ i.reopen_count }}</span>
						<span class="pjx-age" :data-level="age(i).level" :title="`In status ${age(i).label}`">{{ age(i).label }}</span>
						<span v-if="i.due_date" class="pjx-due" :class="{ 'is-today': isToday(i.due_date) }">{{ dueLabel(i.due_date) }}</span>
						<span v-if="i.estimate" class="pjx-pts">{{ i.estimate }}</span>
						<AvatarStack v-if="i.assignees && i.assignees.length" :users="i.assignees" :size="18" />
						<Dropdown :options="moveOptions(i)">
							<button class="pjx-iconbtn" title="Move" @pointerdown.stop @click.stop><Icon name="arrow-right-left" :size="13" /></button>
						</Dropdown>
					</div>
					<div v-if="!s.items.length" class="pjx-bl__empty">Drag tasks here.</div>
				</div>
			</div>
			<div v-if="!sprints.length && !adding" class="pjx-bl__empty">No sprints yet — create one to start planning.</div>
		</section>

		<!-- Backlog -->
		<section class="pjx-bl__col">
			<div class="pjx-bl__head">
				<h3 class="pjx-bl__title"><Icon name="inbox" :size="15" /> Backlog</h3>
				<span class="pjx-sprint__pts">{{ backlog.length }} tasks · {{ sumPoints(backlog) }} pts</span>
			</div>
			<div class="pjx-bl__list pjx-bl__drop" data-cycle="" :class="{ 'is-over': overCycle === '' }">
				<div v-for="i in backlog" :key="i.name" class="pjx-blrow" @click="onRowClick(i)">
					<button class="pjx-grip" title="Drag to move" @pointerdown.stop="(e) => onPickup(i, e)" @click.stop>
						<Icon name="grip-vertical" :size="13" />
					</button>
					<PriorityBars :priority="i.priority" />
					<StatusDot :status="statusMeta(i.status)" :size="8" />
					<span class="pjx-id">{{ i.issue_id }}</span>
					<span class="pjx-blrow__t">{{ i.title }}</span>
					<span v-if="i.reopen_count" class="pjx-rwk" :title="`Reopened ${i.reopen_count}×`"><Icon name="undo-2" :size="12" />{{ i.reopen_count }}</span>
					<span class="pjx-age" :data-level="age(i).level" :title="`In status ${age(i).label}`">{{ age(i).label }}</span>
					<span v-if="i.estimate" class="pjx-pts">{{ i.estimate }}</span>
					<AvatarStack v-if="i.assignees && i.assignees.length" :users="i.assignees" :size="18" />
					<Dropdown :options="moveOptions(i)">
						<button class="pjx-iconbtn" title="Move to sprint" @pointerdown.stop @click.stop><Icon name="arrow-right" :size="13" /></button>
					</Dropdown>
				</div>
				<div v-if="!backlog.length" class="pjx-bl__empty">Backlog is empty.</div>
			</div>
		</section>

		<StartSprintDialog :open="startOpen" :cycle="dialogCycle" @close="startOpen = false" @started="afterChange" />
		<CompleteSprintDialog
			:open="completeOpen"
			:cycle="dialogCycle"
			:issues="completeIssues"
			:statuses="statuses"
			:upcoming="upcomingOptions"
			@close="completeOpen = false"
			@completed="afterChange"
		/>
	</div>
</template>

<style scoped>
.pjx-backlog { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; padding: 16px; overflow-y: auto; }
.pjx-bl__col { min-width: 0; }
.pjx-bl__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.pjx-bl__title { display: flex; align-items: center; gap: 7px; font-size: 14px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-cap { font-size: 12px; color: var(--ink-gray-5); }
.pjx-sprint { border: 1px solid var(--outline-gray-2); border-radius: 10px; margin-bottom: 12px; background: var(--surface-white); }
.pjx-sprint.is-over, .pjx-bl__drop.is-over { outline: 2px solid var(--outline-blue-2, var(--blue-400)); outline-offset: -2px; background: var(--surface-blue-1, rgba(59, 130, 246, 0.04)); border-radius: 10px; }
.pjx-sprint__head { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--outline-gray-1); }
.pjx-state { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; background: var(--surface-gray-3); color: var(--ink-gray-7); }
.pjx-state[data-theme='green'] { background: var(--surface-green-2); color: var(--ink-green-3); }
.pjx-state[data-theme='blue'] { background: var(--surface-blue-2); color: var(--ink-blue-3); }
.pjx-sprint__name { font-weight: 600; font-size: 13px; color: var(--ink-gray-9); flex: 1; }
.pjx-sprint__pts { font-size: 12px; color: var(--ink-gray-5); }
.pjx-over { color: var(--ink-amber-3); font-weight: 600; }
.pjx-sprint__goal { display: flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 12px; color: var(--ink-gray-6); border-bottom: 1px solid var(--outline-gray-1); }
.pjx-sprint__pbar { height: 4px; background: var(--surface-gray-2); }
.pjx-sprint__pbar span { display: block; height: 100%; background: var(--green-600); }
.pjx-bl__list { padding: 4px; }
.pjx-bl__drop { min-height: 60px; border-radius: 8px; }
.pjx-blrow { display: flex; align-items: center; gap: 8px; padding: 7px 8px; border-radius: 7px; cursor: pointer; font-size: 13px; }
.pjx-blrow:hover { background: var(--surface-gray-1); }
.pjx-grip { border: 0; background: transparent; padding: 0; margin-left: -4px; width: 16px; display: grid; place-items: center; cursor: grab; color: var(--ink-gray-4); opacity: 0; touch-action: none; }
.pjx-blrow:hover .pjx-grip { opacity: 1; }
.pjx-grip:active { cursor: grabbing; }
.pjx-blrow__t { flex: 1; color: var(--ink-gray-8); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pjx-pts { min-width: 20px; height: 18px; padding: 0 6px; display: inline-grid; place-items: center; border-radius: 5px; background: var(--surface-gray-2); font-size: 11px; font-weight: 600; color: var(--ink-gray-7); }
.pjx-iconbtn { border: 0; background: transparent; cursor: pointer; color: var(--ink-gray-5); width: 24px; height: 24px; display: grid; place-items: center; border-radius: 6px; }
.pjx-iconbtn:hover { background: var(--surface-gray-3); color: var(--ink-gray-8); }
.pjx-bl__empty { padding: 14px 10px; font-size: 13px; color: var(--ink-gray-4); }
.pjx-bl__newsprint { display: flex; flex-direction: column; gap: 8px; padding: 12px; border: 1px dashed var(--outline-gray-2); border-radius: 10px; margin-bottom: 12px; }
@media (max-width: 980px) { .pjx-backlog { grid-template-columns: 1fr; } }
</style>
