<script setup>
import { computed } from 'vue'
import { Dropdown, Button } from 'frappe-ui'
import Icon from './Icon.vue'
import MultiSelectPopover from './MultiSelectPopover.vue'

const props = defineProps({
	statuses: { type: Array, default: () => [] },
	state: { type: Object, required: true }, // { statusFilter:[], assigneeMe, sortBy, groupBy }
	showGroup: { type: Boolean, default: true },
})
const emit = defineEmits(['update'])

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
				:options="statusOptions"
				:model-value="state.statusFilter"
				@change="(v) => set({ statusFilter: v })"
			>
				<template #trigger>
					<span class="pjx-chip">
						<span class="pjx-chip__k">Status</span>
						<span class="pjx-chip__v">{{ state.statusFilter.length ? state.statusFilter.length + ' selected' : 'Any' }}</span>
					</span>
				</template>
			</MultiSelectPopover>
			<button
				class="pjx-chip"
				:class="{ 'pjx-chip--add': !state.assigneeMe }"
				@click="set({ assigneeMe: !state.assigneeMe })"
			>
				<span class="pjx-chip__k">Assignee</span>
				<span class="pjx-chip__v">{{ state.assigneeMe ? 'Me' : 'Anyone' }}</span>
			</button>
		</div>
		<div class="pjx-list__bar-right">
			<Dropdown
				v-if="showGroup"
				:options="GROUPS.map((g) => ({ label: g.label, onClick: () => set({ groupBy: g.id }) }))"
			>
				<Button variant="ghost" theme="gray">
					<span class="t-xs ink-5">Group:</span>&nbsp;{{ groupLabel }}
					<template #suffix><Icon name="chevron-down" :size="13" /></template>
				</Button>
			</Dropdown>
			<Dropdown :options="SORTS.map((s) => ({ label: s.label, onClick: () => set({ sortBy: s.id }) }))">
				<Button variant="ghost" theme="gray">
					<span class="t-xs ink-5">Sort:</span>&nbsp;{{ sortLabel }}
					<template #suffix><Icon name="chevron-down" :size="13" /></template>
				</Button>
			</Dropdown>
		</div>
	</div>
</template>
