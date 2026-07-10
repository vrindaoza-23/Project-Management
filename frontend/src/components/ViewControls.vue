<script setup>
import { computed, h } from 'vue'
import { Dropdown, Button } from 'frappe-ui'
import Icon from './Icon.vue'
import MultiSelectPopover from './MultiSelectPopover.vue'
import { promptText } from '@/utils/feedback'

// frappe-ui Menu renders a component passed as `icon`; use our Icon so any
// lucide name works without relying on statically-generated CSS classes.
const menuIcon = (name) => ({ render: () => h(Icon, { name, size: 15 }) })

const props = defineProps({
	statuses: { type: Array, default: () => [] },
	state: { type: Object, required: true }, // { statusFilter:[], assignees:[], sortBy, groupBy }
	showGroup: { type: Boolean, default: true },
	savedViews: { type: Array, default: () => [] }, // [{ name, view_name, view_type, config }]
	assigneeOptions: { type: Array, default: () => [] }, // [{ value, label }]
})
const emit = defineEmits(['update', 'export', 'save-view', 'apply-view', 'delete-view'])

// Build the Views dropdown: each saved view applies on click (trash deletes it),
// plus a divider and "Save current view…".
const viewOptions = computed(() => {
	const apply = props.savedViews.map((v) => ({
		label: v.view_name,
		onClick: () => emit('apply-view', v),
	}))
	const remove = props.savedViews.map((v) => ({
		label: 'Delete: ' + v.view_name,
		icon: menuIcon('trash-2'),
		onClick: () => emit('delete-view', v),
	}))
	return [
		{
			label: 'Save current view…',
			icon: menuIcon('plus'),
			onClick: async () => {
				const name = await promptText({
					title: 'Save view',
					label: 'View name',
					placeholder: 'e.g. My high-priority tasks',
				})
				if (name) emit('save-view', name)
			},
		},
		...(apply.length ? [{ group: 'Saved', items: apply }] : []),
		...(remove.length ? [{ group: 'Manage', items: remove }] : []),
	]
})

const statusOptions = computed(() => props.statuses.map((s) => ({ value: s.name, label: s.status_name })))
const SORTS = [
	{ id: 'rank', label: 'Manual' },
	{ id: 'priority', label: 'Priority' },
	{ id: 'due', label: 'Due date' },
	{ id: 'recent', label: 'Recently updated' },
]
const GROUPS = [
	{ id: 'status', label: 'Status' },
	{ id: 'priority', label: 'Priority' },
	{ id: 'none', label: 'None' },
]

function set(patch) {
	emit('update', { ...props.state, ...patch })
}
const sortLabel = computed(() => SORTS.find((s) => s.id === props.state.sortBy)?.label || 'Manual')
const groupLabel = computed(() => GROUPS.find((g) => g.id === props.state.groupBy)?.label || 'Status')
</script>

<template>
	<div class="pjx-list__bar">
		<div class="pjx-chips">
			<MultiSelectPopover
				bare
				:options="statusOptions"
				:model-value="state.statusFilter"
				@change="(v) => set({ statusFilter: v })"
			>
				<template #trigger>
					<span class="pjx-fbtn">
						<span class="pjx-fbtn__k">Status</span>
						<span class="pjx-fbtn__v">{{ state.statusFilter.length ? state.statusFilter.length + ' selected' : 'Any' }}</span>
					</span>
				</template>
			</MultiSelectPopover>
			<MultiSelectPopover
				bare
				:options="assigneeOptions"
				:model-value="state.assignees || []"
				@change="(v) => set({ assignees: v })"
			>
				<template #trigger>
					<span class="pjx-fbtn">
						<span class="pjx-fbtn__k">Assignee</span>
						<span class="pjx-fbtn__v">{{ (state.assignees || []).length ? (state.assignees.length + ' selected') : 'Anyone' }}</span>
					</span>
				</template>
			</MultiSelectPopover>
		</div>
		<div class="pjx-list__bar-right">
			<Dropdown :options="viewOptions">
				<Button variant="ghost" theme="gray">
					<template #prefix><Icon name="bookmark" :size="14" /></template>
					Views
					<template #suffix><Icon name="chevron-down" :size="13" /></template>
				</Button>
			</Dropdown>
			<Dropdown
				v-if="showGroup"
				:options="GROUPS.map((g) => ({ label: g.label, onClick: () => set({ groupBy: g.id }) }))"
			>
				<Button variant="ghost" theme="gray">
					<span class="ink-5">Group</span>&nbsp;{{ groupLabel }}
					<template #suffix><Icon name="chevron-down" :size="13" /></template>
				</Button>
			</Dropdown>
			<Dropdown :options="SORTS.map((s) => ({ label: s.label, onClick: () => set({ sortBy: s.id }) }))">
				<Button variant="ghost" theme="gray">
					<span class="ink-5">Sort</span>&nbsp;{{ sortLabel }}
					<template #suffix><Icon name="chevron-down" :size="13" /></template>
				</Button>
			</Dropdown>
			<Button variant="ghost" theme="gray" title="Export visible tasks to CSV" @click="emit('export')">
				<template #prefix><Icon name="download" :size="14" /></template>
				Export
			</Button>
		</div>
	</div>
</template>

<style scoped>
/* Filter triggers styled as quiet ghost controls to match the right side. */
.pjx-fbtn {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	font-size: 14px;
	white-space: nowrap;
}
.pjx-fbtn__k {
	color: var(--ink-gray-5);
}
.pjx-fbtn__v {
	color: var(--ink-gray-8);
}
</style>
