<script setup>
import { computed, ref } from 'vue'
import {
	ListView,
	ListHeader,
	ListGroupHeader,
	ListRow,
	ListRows,
	ListEmptyState,
	ListSelectBanner,
	Dropdown,
	Button,
} from 'frappe-ui'
import GroupAddRow from '@/components/GroupAddRow.vue'
import Icon from '@/components/Icon.vue'
import StatusDot from '@/components/StatusDot.vue'
import PriorityBars from '@/components/PriorityBars.vue'
import LabelChip from '@/components/LabelChip.vue'
import AvatarStack from '@/components/AvatarStack.vue'
import LivePill from '@/components/LivePill.vue'
import QuickAdd from '@/components/QuickAdd.vue'
import { dueLabel, dueTone, relativeTime } from '@/utils/format'
import { confirm } from '@/utils/feedback'

const props = defineProps({
	projectKey: { type: String, required: true },
	issues: { type: Array, default: () => [] },
	statuses: { type: Array, default: () => [] },
	groupBy: { type: String, default: 'status' },
	cols: { type: Object, default: () => ({ labels: true, pts: true, due: true, updated: true, assignees: true }) },
	presence: { type: Object, default: () => ({}) },
	loading: { type: Boolean, default: false },
})
const emit = defineEmits(['open', 'created', 'bulk-update', 'bulk-delete'])

const statusById = computed(() => Object.fromEntries(props.statuses.map((s) => [s.name, s])))
const PRIORITY_ORDER = ['Urgent', 'High', 'Medium', 'Low', 'None']

// Column config for the frappe-ui ListView (Task fixed; the rest toggle from the
// toolbar's Columns control). `width` feeds the grid template.
const columns = computed(() => {
	const c = [{ label: 'Task', key: 'title', width: 'minmax(280px, 2fr)' }]
	if (props.cols.labels) c.push({ label: 'Labels', key: 'labels', width: '180px' })
	if (props.cols.pts) c.push({ label: 'Pts', key: 'estimate', width: '56px', align: 'right' })
	if (props.cols.due) c.push({ label: 'Due', key: 'due_date', width: '92px', align: 'right' })
	if (props.cols.updated) c.push({ label: 'Updated', key: 'modified', width: '92px', align: 'right' })
	if (props.cols.assignees) c.push({ label: 'Assignees', key: 'assignees', width: '112px', align: 'right' })
	return c
})

function open(name) {
	emit('open', name)
}
const listOptions = computed(() => ({
	selectable: true,
	showTooltip: false,
	rowHeight: '46px',
	onRowClick: (row) => open(row.name),
	emptyState: { title: 'No tasks yet', description: 'Create one above to get started.' },
}))

// Group issues by the active groupBy into the ListView's grouped-rows shape.
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
const groupedRows = computed(() =>
	groups.value.map((g) => ({ group: g.label, key: g.key, status: g.status, priority: g.priority, rows: g.items })),
)

// Context the group's inline add-row stamps onto new tasks.
function addFields(group) {
	if (props.groupBy === 'status' && group.status) return { status: group.status.name }
	if (props.groupBy === 'priority' && group.priority) return { priority: group.priority }
	return {}
}

// ---- bulk actions: selection is owned by ListView; we mirror it for the banner ----
const listRef = ref(null)
const selected = ref([])
function onSelections(set) {
	selected.value = [...set]
}
function clearSelection() {
	listRef.value?.toggleAllRows(false)
	selected.value = []
}
function bulkStatus(s) { emit('bulk-update', { names: selected.value, fields: { status: s.name } }); clearSelection() }
function bulkPriority(p) { emit('bulk-update', { names: selected.value, fields: { priority: p } }); clearSelection() }
async function bulkDelete() {
	const n = selected.value.length
	const ok = await confirm({
		title: `Delete ${n} task${n === 1 ? '' : 's'}`,
		message: 'This cannot be undone.',
		confirmLabel: 'Delete',
		theme: 'red',
	})
	if (!ok) return
	emit('bulk-delete', { names: selected.value })
	clearSelection()
}
const statusActions = computed(() => props.statuses.map((s) => ({ label: s.status_name, onClick: () => bulkStatus(s) })))
const priorityActions = PRIORITY_ORDER.map((p) => ({ label: p, onClick: () => bulkPriority(p) }))
</script>

<template>
	<div class="pjx-list">
		<ListView
			ref="listRef"
			class="pjx-tasklist"
			:columns="columns"
			:rows="groupedRows"
			row-key="name"
			:options="listOptions"
			@update:selections="onSelections"
		>
			<template #group-header="{ group }">
				<span class="pjx-grouphead">
					<StatusDot v-if="group.status" :status="group.status" />
					<PriorityBars v-else-if="group.priority" :priority="group.priority" />
					<span class="pjx-grouphead__name">{{ group.group }}</span>
					<span class="pjx-grouphead__count">{{ group.rows.length }}</span>
				</span>
			</template>

			<template #cell="{ column, row }">
				<div class="pjx-tc" :class="{ 'pjx-tc--r': column.align === 'right' }">
					<template v-if="column.key === 'title'">
						<PriorityBars :priority="row.priority" />
						<StatusDot v-if="groupBy !== 'status'" :status="statusById[row.status]" />
						<span class="pjx-id">{{ row.issue_id }}</span>
						<span class="pjx-title">{{ row.title }}</span>
						<span v-if="row.sub_total" class="pjx-meta"><Icon name="list-checks" :size="13" />{{ row.sub_done }}/{{ row.sub_total }}</span>
						<span v-if="row.comment_count" class="pjx-meta"><Icon name="message-square" :size="13" />{{ row.comment_count }}</span>
						<LivePill :users="presence[row.name] || []" />
					</template>
					<template v-else-if="column.key === 'labels'">
						<LabelChip v-for="l in row.labels.slice(0, 2)" :key="l.label" :label="l" />
						<span v-if="row.labels.length > 2" class="pjx-dim t-xs">+{{ row.labels.length - 2 }}</span>
					</template>
					<template v-else-if="column.key === 'estimate'">
						<span v-if="row.estimate" class="pjx-pts">{{ row.estimate }}</span>
						<span v-else class="pjx-dim">–</span>
					</template>
					<template v-else-if="column.key === 'due_date'">
						<span v-if="row.due_date" class="pjx-due" :data-tone="dueTone(row.due_date)">{{ dueLabel(row.due_date) }}</span>
						<span v-else class="pjx-dim">–</span>
					</template>
					<template v-else-if="column.key === 'modified'">
						<span class="pjx-dim t-xs">{{ relativeTime(row.modified) }}</span>
					</template>
					<template v-else-if="column.key === 'assignees'">
						<AvatarStack v-if="row.assignees.length" :users="row.assignees" :size="22" />
						<span v-else class="pjx-noass">–</span>
					</template>
				</div>
			</template>

			<!-- Override the default layout only to put our bulk actions in the
			     native selection banner. group-header/cell slots still apply. -->
			<template #default="{ showGroupedRows, selectable }">
				<ListHeader class="pjx-listhead" />
				<template v-if="groupedRows.length">
					<!-- Groups rendered by hand (instead of ListGroups) so each one can
					     end in an inline add-row and get roomier spacing. -->
					<div v-if="showGroupedRows">
						<div v-for="g in groupedRows" :key="g.key">
							<ListGroupHeader :group="g" />
							<div v-if="!g.collapsed" class="pjx-grouprows">
								<ListRow v-for="row in g.rows" :key="row.name" :row="row" />
								<GroupAddRow :project-key="projectKey" :fields="addFields(g)" @created="emit('created')" />
							</div>
						</div>
					</div>
					<ListRows v-else />
				</template>
				<ListEmptyState v-else />
				<ListSelectBanner v-if="selectable">
					<template #actions>
						<div class="pjx-bulkacts">
							<Dropdown :options="statusActions">
								<Button variant="ghost" theme="gray">
									<template #prefix><Icon name="circle-dot" :size="14" /></template>Status
								</Button>
							</Dropdown>
							<Dropdown :options="priorityActions">
								<Button variant="ghost" theme="gray">
									<template #prefix><Icon name="bar-chart-3" :size="14" /></template>Priority
								</Button>
							</Dropdown>
							<Button variant="ghost" theme="gray" @click="bulkDelete">
								<template #prefix><Icon name="trash-2" :size="14" /></template>Delete
							</Button>
						</div>
					</template>
				</ListSelectBanner>
			</template>
		</ListView>

		<QuickAdd v-if="groupedRows.length" :project-key="projectKey" @created="emit('created')" />
	</div>
</template>

<style scoped>
/* Keep the column header visible while .pjx-view scrolls. The two ListView
   wrappers create their own overflow contexts, which would break sticky, so
   scrolling (both axes) is deferred to .pjx-view. */
.pjx-list > :first-child { overflow-x: visible; }
.pjx-list :deep(.pjx-tasklist) { overflow-y: visible; }
.pjx-listhead { position: sticky; top: 0; z-index: 10; }
/* The config ListView doesn't size custom #cell content, so set it explicitly
   (otherwise it inherits the 16px browser default and reads too big). */
.pjx-tc { display: flex; align-items: center; gap: 8px; min-width: 0; width: 100%; font-size: 13px; }
.pjx-tc :deep(.pjx-title) { font-size: 13px; }
.pjx-tc--r { justify-content: flex-end; }
/* Roomier than ListGroupRows' stock mt-2/mb-5 so groups read as distinct bands. */
.pjx-grouprows { margin: 4px 0 28px; }
.pjx-grouphead { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; }
.pjx-grouphead__name { font-weight: 600; color: var(--ink-gray-8); }
.pjx-grouphead__count { color: var(--ink-gray-5); font-variant-numeric: tabular-nums; }
.pjx-bulkacts { display: flex; align-items: center; gap: 4px; }
</style>
