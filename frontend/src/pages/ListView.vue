<script setup>
import { computed, ref, watch } from 'vue'
import { Dropdown, Button } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import StatusDot from '@/components/StatusDot.vue'
import PriorityBars from '@/components/PriorityBars.vue'
import LabelChip from '@/components/LabelChip.vue'
import AvatarStack from '@/components/AvatarStack.vue'
import LivePill from '@/components/LivePill.vue'
import QuickAdd from '@/components/QuickAdd.vue'
import { isToday, dueLabel, relativeTime, ageChip } from '@/utils/format'
import { confirm } from '@/utils/feedback'

const props = defineProps({
	projectKey: { type: String, required: true },
	issues: { type: Array, default: () => [] },
	statuses: { type: Array, default: () => [] },
	groupBy: { type: String, default: 'status' },
	presence: { type: Object, default: () => ({}) },
	loading: { type: Boolean, default: false },
})
const emit = defineEmits(['open', 'created', 'bulk-update', 'bulk-delete'])

const statusById = computed(() => Object.fromEntries(props.statuses.map((s) => [s.name, s])))

const PRIORITY_ORDER = ['Urgent', 'High', 'Medium', 'Low', 'None']

// ---- multi-select / bulk actions ----
const selected = ref(new Set())
// Drop ids that have scrolled out of the current result set.
watch(
	() => props.issues,
	(rows) => {
		const live = new Set(rows.map((r) => r.name))
		selected.value.forEach((id) => { if (!live.has(id)) selected.value.delete(id) })
		selected.value = new Set(selected.value)
	},
)
const selectedCount = computed(() => selected.value.size)
const allSelected = computed(() => props.issues.length > 0 && selected.value.size === props.issues.length)
function isSelected(name) { return selected.value.has(name) }
function toggleRow(name) {
	const s = new Set(selected.value)
	s.has(name) ? s.delete(name) : s.add(name)
	selected.value = s
}
function toggleAll() {
	selected.value = allSelected.value ? new Set() : new Set(props.issues.map((i) => i.name))
}
function clearSelection() { selected.value = new Set() }
function names() { return [...selected.value] }
function bulkStatus(s) { emit('bulk-update', { names: names(), fields: { status: s.name } }); clearSelection() }
function bulkPriority(p) { emit('bulk-update', { names: names(), fields: { priority: p } }); clearSelection() }
async function bulkDelete() {
	const n = selectedCount.value
	const ok = await confirm({
		title: `Delete ${n} task${n === 1 ? '' : 's'}`,
		message: 'This cannot be undone.',
		confirmLabel: 'Delete',
		theme: 'red',
	})
	if (!ok) return
	emit('bulk-delete', { names: names() })
	clearSelection()
}
const statusActions = computed(() =>
	props.statuses.map((s) => ({ label: s.status_name, onClick: () => bulkStatus(s) })),
)
const priorityActions = PRIORITY_ORDER.map((p) => ({ label: p, onClick: () => bulkPriority(p) }))

// Group issues by the active groupBy; hide empty groups.
const groups = computed(() => {
	if (props.groupBy === 'none') {
		return props.issues.length ? [{ key: 'all', label: 'All issues', items: props.issues }] : []
	}
	if (props.groupBy === 'priority') {
		return PRIORITY_ORDER.map((p) => ({
			key: p, label: p, priority: p,
			items: props.issues.filter((i) => (i.priority || 'None') === p),
		})).filter((g) => g.items.length)
	}
	const ordered = [...props.statuses].sort((a, b) => (a.position || 0) - (b.position || 0))
	return ordered
		.map((s) => ({ key: s.name, label: s.status_name, status: s, items: props.issues.filter((i) => i.status === s.name) }))
		.filter((g) => g.items.length)
})
</script>

<template>
	<div class="pjx-list">
		<QuickAdd :project-key="projectKey" @created="emit('created')" />

		<div class="pjx-list__head">
			<span class="pjx-lead"
				><input type="checkbox" class="pjx-check is-on" :checked="allSelected" @change="toggleAll"
			/></span>
			<span>Task</span>
			<span>Labels</span>
			<span class="r">Pts</span>
			<span class="r">Due</span>
			<span class="r">Updated</span>
			<span class="r">Pending</span>
			<span class="r">Assignees</span>
		</div>

		<template v-if="loading">
			<div v-for="n in 6" :key="n" class="pjx-row" style="opacity: 0.5">
				<span class="pjx-cell"></span>
				<span class="pjx-cell pjx-titlecell">
					<span class="pjx-skel" style="width: 40%" />
				</span>
			</div>
		</template>

		<template v-else>
			<div v-for="g in groups" :key="g.key">
				<div class="pjx-grouphead">
					<StatusDot v-if="g.status" :status="g.status" />
					<PriorityBars v-else-if="g.priority" :priority="g.priority" />
					<span class="pjx-grouphead__name">{{ g.label }}</span>
					<span class="pjx-grouphead__count">{{ g.items.length }}</span>
				</div>

				<div
						v-for="it in g.items"
						:key="it.name"
						class="pjx-row"
						:class="{ 'is-selected': isSelected(it.name) }"
						@click="emit('open', it.name)"
					>
					<span class="pjx-cell pjx-lead">
						<input
							type="checkbox"
							class="pjx-check"
							:class="{ 'is-on': isSelected(it.name) }"
							:checked="isSelected(it.name)"
							@click.stop
							@change="toggleRow(it.name)"
						/>
						<span class="pjx-leadprio"><PriorityBars :priority="it.priority" /></span>
					</span>
					<span class="pjx-cell pjx-titlecell">
						<StatusDot :status="statusById[it.status]" />
						<span class="pjx-id">{{ it.issue_id }}</span>
						<span class="pjx-title">{{ it.title }}</span>
						<span v-if="it.sub_total" class="pjx-meta"
							><Icon name="list-checks" :size="13" />{{ it.sub_done }}/{{ it.sub_total }}</span
						>
						<span v-if="it.comment_count" class="pjx-meta"
							><Icon name="message-square" :size="13" />{{ it.comment_count }}</span
						>
						<LivePill :users="presence[it.name] || []" />
					</span>
					<span class="pjx-cell">
						<LabelChip v-for="l in it.labels.slice(0, 2)" :key="l.label" :label="l" />
						<span v-if="it.labels.length > 2" class="pjx-dim t-xs">+{{ it.labels.length - 2 }}</span>
					</span>
					<span class="pjx-cell r">
						<span v-if="it.estimate" class="pjx-pts">{{ it.estimate }}</span>
						<span v-else class="pjx-dim">–</span>
					</span>
					<span class="pjx-cell r">
						<span v-if="it.due_date" class="pjx-due" :class="{ 'is-today': isToday(it.due_date) }">{{
							dueLabel(it.due_date)
						}}</span>
						<span v-else class="pjx-dim">–</span>
					</span>
					<span class="pjx-cell r"><span class="pjx-dim t-xs">{{ relativeTime(it.modified) }}</span></span>
					<span class="pjx-cell r">
						<span class="pjx-age" :data-level="ageChip(it.status_changed_on, it.modified).level" :title="`In current status ${ageChip(it.status_changed_on, it.modified).label}`">{{ ageChip(it.status_changed_on, it.modified).label }}</span>
					</span>
					<span class="pjx-cell r">
						<AvatarStack v-if="it.assignees.length" :users="it.assignees" :size="22" />
						<span v-else class="pjx-noass">–</span>
					</span>
				</div>
			</div>

			<div v-if="!groups.length" class="pjx-soon" style="height: 320px">
				<span class="pjx-soon__icon"><Icon name="inbox" :size="20" /></span>
				<div class="t-base ink-7" style="font-weight: 500">No tasks yet</div>
				<div class="t-sm ink-4">Create one above to get started.</div>
			</div>
		</template>

		<Transition name="pjx-bulkbar">
			<div v-if="selectedCount" class="pjx-bulkbar">
				<span class="pjx-bulkbar__count">{{ selectedCount }} selected</span>
				<Dropdown :options="statusActions">
					<Button variant="ghost" theme="gray">
						<template #prefix><Icon name="circle-dot" :size="14" /></template>
						Status
					</Button>
				</Dropdown>
				<Dropdown :options="priorityActions">
					<Button variant="ghost" theme="gray">
						<template #prefix><Icon name="bar-chart-3" :size="14" /></template>
						Priority
					</Button>
				</Dropdown>
				<Button variant="ghost" theme="gray" @click="bulkDelete">
					<template #prefix><Icon name="trash-2" :size="14" /></template>
					Delete
				</Button>
				<span class="pjx-bulkbar__sep" />
				<Button variant="ghost" theme="gray" @click="clearSelection">Clear</Button>
			</div>
		</Transition>
	</div>
</template>

<style scoped>
/* Leading cell: priority bars by default, checkbox on hover or when selected. */
.pjx-lead {
	position: relative;
	display: inline-flex;
	align-items: center;
}
.pjx-check {
	cursor: pointer;
	accent-color: var(--surface-gray-7);
}
.pjx-lead .pjx-check {
	display: none;
}
.pjx-row:hover .pjx-lead .pjx-check,
.pjx-lead .pjx-check.is-on {
	display: inline-block;
}
.pjx-row:hover .pjx-lead .pjx-leadprio,
.pjx-check.is-on + .pjx-leadprio {
	display: none;
}
.pjx-row.is-selected {
	background: var(--surface-gray-2);
}

/* Floating bulk action bar */
.pjx-bulkbar {
	position: sticky;
	bottom: 16px;
	z-index: var(--z-raised);
	margin: 16px auto 0;
	width: fit-content;
	display: flex;
	align-items: center;
	gap: 4px;
	padding: 6px 10px;
	background: var(--surface-white);
	border: 1px solid var(--outline-gray-2);
	border-radius: 10px;
	box-shadow: 0 8px 28px rgba(0, 0, 0, 0.16);
}
.pjx-bulkbar__count {
	font-size: 12px;
	font-weight: 600;
	color: var(--ink-gray-7);
	padding: 0 8px;
}
.pjx-bulkbar__sep {
	width: 1px;
	height: 18px;
	background: var(--outline-gray-2);
	margin: 0 2px;
}
.pjx-bulkbar-enter-active,
.pjx-bulkbar-leave-active {
	transition: opacity 0.15s ease, transform 0.15s ease;
}
.pjx-bulkbar-enter-from,
.pjx-bulkbar-leave-to {
	opacity: 0;
	transform: translateY(8px);
}
</style>
