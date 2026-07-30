<script setup>
import { computed, nextTick, ref } from 'vue'
import { Dropdown, Button, Popover, TabButtons } from 'frappe-ui'
import Icon from './Icon.vue'
import MultiSelectPopover from './MultiSelectPopover.vue'
import NativeSelect from './NativeSelect.vue'
import { promptText } from '@/utils/feedback'

const props = defineProps({
	statuses: { type: Array, default: () => [] },
	state: { type: Object, required: true }, // { search, statusFilter:[], assignees:[], sortBy, groupBy, cols }
	views: { type: Array, default: () => [] }, // [{ id, label }] task-view switcher
	activeView: { type: String, default: '' },
	showFilters: { type: Boolean, default: true }, // search/filter/display apply (list & board)
	showGroup: { type: Boolean, default: true }, // group/columns apply (list only)
	savedViews: { type: Array, default: () => [] }, // [{ name, view_name, view_type, config }]
	assigneeOptions: { type: Array, default: () => [] }, // [{ value, label }]
	typeOptions: { type: Array, default: () => [] }, // [{ value, label }] issue types
})
const emit = defineEmits(['update', 'export', 'save-view', 'apply-view', 'delete-view', 'view'])

function set(patch) {
	emit('update', { ...props.state, ...patch })
}

const viewTabOptions = computed(() => props.views.map((v) => ({ label: v.label, value: v.id })))

// ── search: an icon until it's needed ──
const searchOpen = ref(false)
const searchEl = ref(null)
const searchVisible = computed(() => searchOpen.value || !!props.state.search)
async function openSearch() {
	searchOpen.value = true
	await nextTick()
	searchEl.value?.focus()
}
function onSearchBlur() {
	if (!props.state.search) searchOpen.value = false
}
function clearSearch() {
	set({ search: '' })
	searchOpen.value = false
}

// ── filters: chips appear only while active; "+ Filter" adds one ──
const statusOptions = computed(() => props.statuses.map((s) => ({ value: s.name, label: s.status_name })))
const pendingFilter = ref(null) // chip rendered (empty) while its editor is open
const statusChip = ref(null)
const assigneeChip = ref(null)
const typeChip = ref(null)

const FILTERS = [
	{ id: 'status', label: 'Status' },
	{ id: 'assignee', label: 'Assignee' },
	{ id: 'type', label: 'Type' },
]
const CHIP_REFS = { status: statusChip, assignee: assigneeChip, type: typeChip }
async function addFilter(kind) {
	pendingFilter.value = kind
	await nextTick()
	CHIP_REFS[kind].value?.openPanel()
}
function onChipClose(kind) {
	if (pendingFilter.value === kind) pendingFilter.value = null
}
function chipLabel(options, selected) {
	if (!selected?.length) return 'Any'
	if (selected.length === 1) return options.find((o) => o.value === selected[0])?.label || selected[0]
	return `${selected.length} selected`
}

// ── display: group/sort/columns/saved views/export behind one popover ──
const SORTS = [
	{ value: 'rank', label: 'Manual' },
	{ value: 'priority', label: 'Priority' },
	{ value: 'due', label: 'Due date' },
	{ value: 'recent', label: 'Recently updated' },
]
const GROUPS = [
	{ value: 'status', label: 'Status' },
	{ value: 'priority', label: 'Priority' },
	{ value: 'none', label: 'None' },
]
const COLS = [
	{ value: 'labels', label: 'Labels' },
	{ value: 'pts', label: 'Points' },
	{ value: 'due', label: 'Due date' },
	{ value: 'updated', label: 'Updated' },
	{ value: 'assignees', label: 'Assignees' },
]
const colVisible = (id) => props.state.cols?.[id] !== false
function toggleCol(id) {
	const cols = {}
	for (const c of COLS) cols[c.value] = c.value === id ? !colVisible(id) : colVisible(c.value)
	set({ cols })
}
// A dot on the trigger keeps non-default config visible without spending
// toolbar slots on Group/Sort/Columns labels.
const displayDirty = computed(
	() =>
		(props.showGroup && props.state.groupBy !== 'status') ||
		props.state.sortBy !== 'rank' ||
		(props.showGroup && COLS.some((c) => !colVisible(c.value))),
)

async function saveView() {
	const name = await promptText({
		title: 'Save view',
		label: 'View name',
		placeholder: 'e.g. My high-priority tasks',
	})
	if (name) emit('save-view', name)
}
</script>

<template>
	<div class="pjx-list__bar">
		<TabButtons
			v-if="views.length"
			type="subtle"
			:model-value="activeView"
			:options="viewTabOptions"
			@update:model-value="(v) => emit('view', v)"
		/>

		<template v-if="showFilters">
			<!-- active-filter chips: zero filters = zero chrome -->
			<MultiSelectPopover
				v-if="state.statusFilter?.length || pendingFilter === 'status'"
				ref="statusChip"
				bare
				:options="statusOptions"
				:model-value="state.statusFilter"
				@change="(v) => set({ statusFilter: v })"
				@close="onChipClose('status')"
			>
				<template #trigger>
					<span class="pjx-chip2">
						<span class="pjx-chip2__k">Status</span>
						<span class="pjx-chip2__v">{{ chipLabel(statusOptions, state.statusFilter) }}</span>
						<span class="pjx-chip2__x" title="Clear filter" @click.stop="set({ statusFilter: [] })"><Icon name="x" :size="12" /></span>
					</span>
				</template>
			</MultiSelectPopover>
			<MultiSelectPopover
				v-if="(state.assignees || []).length || pendingFilter === 'assignee'"
				ref="assigneeChip"
				bare
				:options="assigneeOptions"
				:model-value="state.assignees || []"
				@change="(v) => set({ assignees: v })"
				@close="onChipClose('assignee')"
			>
				<template #trigger>
					<span class="pjx-chip2">
						<span class="pjx-chip2__k">Assignee</span>
						<span class="pjx-chip2__v">{{ chipLabel(assigneeOptions, state.assignees || []) }}</span>
						<span class="pjx-chip2__x" title="Clear filter" @click.stop="set({ assignees: [] })"><Icon name="x" :size="12" /></span>
					</span>
				</template>
			</MultiSelectPopover>
			<MultiSelectPopover
				v-if="(state.typeFilter || []).length || pendingFilter === 'type'"
				ref="typeChip"
				bare
				:options="typeOptions"
				:model-value="state.typeFilter || []"
				@change="(v) => set({ typeFilter: v })"
				@close="onChipClose('type')"
			>
				<template #trigger>
					<span class="pjx-chip2">
						<span class="pjx-chip2__k">Type</span>
						<span class="pjx-chip2__v">{{ chipLabel(typeOptions, state.typeFilter || []) }}</span>
						<span class="pjx-chip2__x" title="Clear filter" @click.stop="set({ typeFilter: [] })"><Icon name="x" :size="12" /></span>
					</span>
				</template>
			</MultiSelectPopover>

			<div class="pjx-list__bar-right">
				<!-- search -->
				<label v-if="searchVisible" class="pjx-tsearch">
					<Icon name="search" :size="14" class="ink-5" />
					<input
						ref="searchEl"
						:value="state.search"
						type="text"
						placeholder="Search tasks…"
						@input="(e) => set({ search: e.target.value })"
						@blur="onSearchBlur"
						@keydown.esc="clearSearch"
					/>
				</label>
				<Button v-else variant="ghost" theme="gray" title="Search tasks" @click="openSearch">
					<template #icon><Icon name="search" :size="15" /></template>
				</Button>

				<!-- add filter -->
				<Dropdown :options="FILTERS.map((f) => ({ label: f.label, onClick: () => addFilter(f.id) }))">
					<Button variant="ghost" theme="gray">
						<template #prefix><Icon name="list-filter" :size="14" /></template>
						Filter
					</Button>
				</Dropdown>

				<!-- display -->
				<Popover>
					<template #trigger>
						<Button variant="ghost" theme="gray" class="pjx-displaybtn" :class="{ 'is-dirty': displayDirty }">
							<template #prefix><Icon name="sliders-horizontal" :size="14" /></template>
							Display
						</Button>
					</template>
					<div class="pjx-display">
						<div v-if="showGroup" class="pjx-display__row">
							<span class="pjx-display__lbl">Group by</span>
							<NativeSelect :options="GROUPS" :model-value="state.groupBy" @change="(v) => v && set({ groupBy: v })" />
						</div>
						<div class="pjx-display__row">
							<span class="pjx-display__lbl">Sort by</span>
							<NativeSelect :options="SORTS" :model-value="state.sortBy" @change="(v) => v && set({ sortBy: v })" />
						</div>
						<template v-if="showGroup">
							<div class="pjx-display__sep" />
							<div class="pjx-display__h">Columns</div>
							<button v-for="c in COLS" :key="c.value" type="button" class="pjx-display__opt" @click="toggleCol(c.value)">
								<span style="flex: 1; text-align: left">{{ c.label }}</span>
								<Icon v-if="colVisible(c.value)" name="check" :size="14" />
							</button>
						</template>
						<div class="pjx-display__sep" />
						<div class="pjx-display__h">Views</div>
						<button v-for="v in savedViews" :key="v.name" type="button" class="pjx-display__opt" @click="emit('apply-view', v)">
							<Icon name="bookmark" :size="13" class="ink-5" />
							<span style="flex: 1; text-align: left" class="truncate">{{ v.view_name }}</span>
							<span class="pjx-display__del" title="Delete view" @click.stop="emit('delete-view', v)"><Icon name="trash-2" :size="13" /></span>
						</button>
						<button type="button" class="pjx-display__opt" @click="saveView">
							<Icon name="plus" :size="13" class="ink-5" />
							<span style="flex: 1; text-align: left">Save current view…</span>
						</button>
						<div class="pjx-display__sep" />
						<button type="button" class="pjx-display__opt" @click="emit('export')">
							<Icon name="download" :size="13" class="ink-5" />
							<span style="flex: 1; text-align: left">Export CSV</span>
						</button>
					</div>
				</Popover>
			</div>
		</template>
	</div>
</template>

<style scoped>
/* Collapsible quick-filter search — only rendered while in use. */
.pjx-tsearch {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	height: 28px;
	padding: 0 10px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 8px;
	background: var(--surface-white);
}
.pjx-tsearch:focus-within {
	border-color: var(--outline-gray-3);
}
.pjx-tsearch input {
	width: 150px;
	border: 0;
	outline: 0;
	background: transparent;
	font-family: var(--font-sans);
	font-size: 13px;
	color: var(--ink-gray-9);
}
.pjx-tsearch input::placeholder {
	color: var(--ink-gray-4);
}
/* Active-filter chip (the MultiSelectPopover trigger). */
.pjx-chip2 {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	font-size: 13px;
	white-space: nowrap;
}
.pjx-chip2__k {
	color: var(--ink-gray-5);
}
.pjx-chip2__v {
	color: var(--ink-gray-8);
	font-weight: 500;
}
.pjx-chip2__x {
	display: inline-flex;
	align-items: center;
	color: var(--ink-gray-4);
	border-radius: 4px;
	padding: 1px;
}
.pjx-chip2__x:hover {
	color: var(--ink-gray-8);
	background: var(--surface-gray-3);
}
/* Non-default display config: a quiet dot on the trigger. */
.pjx-displaybtn.is-dirty::after {
	content: '';
	width: 5px;
	height: 5px;
	border-radius: 999px;
	background: var(--ink-gray-6);
	margin-left: 2px;
}
/* Display panel */
.pjx-display {
	width: 240px;
	padding: 4px;
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.pjx-display__row {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 4px 6px;
}
.pjx-display__row :deep(.pjx-nsel__wrap) {
	flex: 1;
}
.pjx-display__lbl {
	width: 64px;
	flex: none;
	font-size: 13px;
	color: var(--ink-gray-6);
}
.pjx-display__h {
	font-size: 11px;
	font-weight: 500;
	color: var(--ink-gray-5);
	padding: 4px 6px 2px;
}
.pjx-display__sep {
	height: 1px;
	background: var(--outline-gray-1);
	margin: 4px -4px;
}
.pjx-display__opt {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	height: 30px;
	padding: 0 6px;
	border: 0;
	background: transparent;
	border-radius: 6px;
	cursor: pointer;
	font-size: 13px;
	color: var(--ink-gray-8);
}
.pjx-display__opt:hover {
	background: var(--surface-gray-2);
}
.pjx-display__del {
	display: inline-flex;
	color: var(--ink-gray-4);
	border-radius: 4px;
	padding: 2px;
}
.pjx-display__del:hover {
	color: var(--ink-red-3);
	background: var(--surface-gray-3);
}
</style>
