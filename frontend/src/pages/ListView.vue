<script setup>
import { computed, ref, watch } from 'vue'
import { Dropdown, Button } from 'frappe-ui'
import { List, ListHeader, ListHeaderCell, ListGroup, ListRow, ListCell } from 'frappe-ui/list'
import Icon from '@/components/Icon.vue'
import StatusDot from '@/components/StatusDot.vue'
import PriorityBars from '@/components/PriorityBars.vue'
import LabelChip from '@/components/LabelChip.vue'
import AvatarStack from '@/components/AvatarStack.vue'
import LivePill from '@/components/LivePill.vue'
import QuickAdd from '@/components/QuickAdd.vue'
import { isToday, dueLabel, relativeTime } from '@/utils/format'
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

// Grid tracks shared by the header and every row (frappe-ui/list --list-columns).
const COLUMNS = ['18px', 'minmax(0,1fr)', '168px', '48px', '80px', '88px', '108px']
const listStyle = {
	'--list-gap': '12px',
	'--list-row-padding-x': '16px',
	'--list-row-height': '46px',
}

// The open task highlights via the List's active row.
const active = ref(null)
function open(name) {
	active.value = name
	emit('open', name)
}

// ---- multi-select / bulk actions (app-owned, so click still opens) ----
const selected = ref(new Set())
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
		<List :columns="COLUMNS" v-model:active="active" divider="full" :style="listStyle" class="pjx-tasklist">
			<ListHeader>
				<ListHeaderCell>
					<input type="checkbox" class="pjx-check is-on" :checked="allSelected" @change="toggleAll" />
				</ListHeaderCell>
				<ListHeaderCell>Task</ListHeaderCell>
				<ListHeaderCell>Labels</ListHeaderCell>
				<ListHeaderCell class="justify-end">Pts</ListHeaderCell>
				<ListHeaderCell class="justify-end">Due</ListHeaderCell>
				<ListHeaderCell class="justify-end">Updated</ListHeaderCell>
				<ListHeaderCell class="justify-end">Assignees</ListHeaderCell>
			</ListHeader>

			<ListGroup v-for="g in groups" :key="g.key">
				<template #header>
					<span class="pjx-grouphead">
						<StatusDot v-if="g.status" :status="g.status" />
						<PriorityBars v-else-if="g.priority" :priority="g.priority" />
						<span class="pjx-grouphead__name">{{ g.label }}</span>
						<span class="pjx-grouphead__count">{{ g.items.length }}</span>
					</span>
				</template>

				<ListRow
					v-for="it in g.items"
					:key="it.name"
					:value="it.name"
					:class="{ 'pjx-selected': isSelected(it.name) }"
					@click="open(it.name)"
				>
					<ListCell class="pjx-lead">
						<input
							type="checkbox"
							class="pjx-check"
							:class="{ 'is-on': isSelected(it.name) }"
							:checked="isSelected(it.name)"
							@click.stop
							@change="toggleRow(it.name)"
						/>
						<span class="pjx-leadprio"><PriorityBars :priority="it.priority" /></span>
					</ListCell>
					<ListCell class="pjx-titlecell">
						<StatusDot v-if="groupBy !== 'status'" :status="statusById[it.status]" />
						<span class="pjx-id">{{ it.issue_id }}</span>
						<span class="pjx-title">{{ it.title }}</span>
						<span v-if="it.sub_total" class="pjx-meta">
							<Icon name="list-checks" :size="13" />{{ it.sub_done }}/{{ it.sub_total }}
						</span>
						<span v-if="it.comment_count" class="pjx-meta">
							<Icon name="message-square" :size="13" />{{ it.comment_count }}
						</span>
						<LivePill :users="presence[it.name] || []" />
					</ListCell>
					<ListCell>
						<LabelChip v-for="l in it.labels.slice(0, 2)" :key="l.label" :label="l" />
						<span v-if="it.labels.length > 2" class="pjx-dim t-xs">+{{ it.labels.length - 2 }}</span>
					</ListCell>
					<ListCell class="justify-end">
						<span v-if="it.estimate" class="pjx-pts">{{ it.estimate }}</span>
						<span v-else class="pjx-dim">–</span>
					</ListCell>
					<ListCell class="justify-end">
						<span v-if="it.due_date" class="pjx-due" :class="{ 'is-today': isToday(it.due_date) }">{{ dueLabel(it.due_date) }}</span>
						<span v-else class="pjx-dim">–</span>
					</ListCell>
					<ListCell class="justify-end"><span class="pjx-dim t-xs">{{ relativeTime(it.modified) }}</span></ListCell>
					<ListCell class="justify-end">
						<AvatarStack v-if="it.assignees.length" :users="it.assignees" :size="22" />
						<span v-else class="pjx-noass">–</span>
					</ListCell>
				</ListRow>
			</ListGroup>
		</List>

		<QuickAdd v-if="groups.length" :project-key="projectKey" @created="emit('created')" />

		<div v-if="!loading && !groups.length" class="pjx-soon" style="height: 320px">
			<span class="pjx-soon__icon"><Icon name="inbox" :size="20" /></span>
			<div class="t-base ink-7" style="font-weight: 500">No tasks yet</div>
			<div class="t-sm ink-4">Create one above to get started.</div>
		</div>

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
/* Helpdesk-style calm rhythm: a subtle header band + generous group spacing. */
.pjx-tasklist :deep([data-slot='list-header']) {
	height: 40px;
	background: var(--surface-gray-1);
	border-radius: 8px;
	font-size: 12px;
	font-weight: 500;
	color: var(--ink-gray-6);
	margin-bottom: 2px;
}
.pjx-tasklist :deep([data-slot='list-group-header']) {
	height: 44px;
	font-size: 13px;
}
.pjx-grouphead { display: inline-flex; align-items: center; gap: 8px; }
.pjx-grouphead__name { font-weight: 600; color: var(--ink-gray-8); }
.pjx-grouphead__count { color: var(--ink-gray-5); font-variant-numeric: tabular-nums; }

/* Leading cell: priority bars by default, checkbox on hover or when selected. */
.pjx-lead { position: relative; gap: 8px; }
.pjx-check { cursor: pointer; accent-color: var(--surface-gray-7); }
.pjx-lead .pjx-check { display: none; }
:deep([data-slot='list-row']:hover) .pjx-lead .pjx-check,
.pjx-lead .pjx-check.is-on { display: inline-block; }
:deep([data-slot='list-row']:hover) .pjx-lead .pjx-leadprio,
.pjx-check.is-on + .pjx-leadprio { display: none; }
.pjx-selected { background: var(--surface-gray-2); }

.pjx-titlecell { gap: 9px; }

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
.pjx-bulkbar__count { font-size: 12px; font-weight: 600; color: var(--ink-gray-7); padding: 0 8px; }
.pjx-bulkbar__sep { width: 1px; height: 18px; background: var(--outline-gray-2); margin: 0 2px; }
.pjx-bulkbar-enter-active,
.pjx-bulkbar-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.pjx-bulkbar-enter-from,
.pjx-bulkbar-leave-to { opacity: 0; transform: translateY(8px); }
</style>
