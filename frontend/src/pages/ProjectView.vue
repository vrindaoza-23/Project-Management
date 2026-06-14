<script setup>
import { ref, watch, computed, onMounted, onUnmounted, reactive } from 'vue'
import { createResource } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import SummaryView from './SummaryView.vue'
import ListView from './ListView.vue'
import BoardView from './BoardView.vue'
import GanttView from './GanttView.vue'
import CalendarView from './CalendarView.vue'
import ReportsView from './ReportsView.vue'
import ProjectSettingsDialog from '@/components/ProjectSettingsDialog.vue'
import { store, projectByKey } from '@/data/store'
import { openPalette, openDrawer, openCreate, ui } from '@/data/ui'
import { onRealtime, joinProjectRoom } from '@/socket'
import { tweaks } from '@/composables/useTweaks'

const props = defineProps({ projectKey: { type: String, required: true } })

const activeTab = ref('summary')
const settingsOpen = ref(false)
const presence = reactive({}) // issue name -> [user ids]
const integration = createResource({ url: 'projex.api.integration_status', auto: true })
const TABS = [
	{ id: 'summary', label: 'Summary' },
	{ id: 'list', label: 'List' },
	{ id: 'board', label: 'Board' },
	{ id: 'calendar', label: 'Calendar' },
	{ id: 'gantt', label: 'Gantt' },
	{ id: 'reports', label: 'Reports' },
]
const SIMPLE_TABS = ['summary', 'reports']

const view = reactive({ statusFilter: [], assigneeMe: false, sortBy: 'rank', groupBy: 'status' })

const board = createResource({
	url: 'projex.api.get_issues',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})

watch(() => props.projectKey, () => board.reload())
watch(() => ui.refreshTick, () => board.reload())

// ---- realtime ----
let unsub = []
function subscribe() {
	teardown()
	joinProjectRoom(props.projectKey)
	const reload = () => board.reload()
	unsub = [
		onRealtime('projex:issue_updated', reload),
		onRealtime('projex:issue_created', reload),
		onRealtime('projex:issue_deleted', reload),
		onRealtime('projex:presence', ({ issue, users }) => {
			presence[issue] = users || []
		}),
	]
}
function teardown() {
	unsub.forEach((fn) => fn && fn())
	unsub = []
}
onMounted(subscribe)
watch(() => props.projectKey, subscribe)
onUnmounted(teardown)

// ---- filter + sort applied client-side ----
const PRIORITY_RANK = { Urgent: 0, High: 1, Medium: 2, Low: 3, None: 4 }
const viewIssues = computed(() => {
	let rows = board.data?.issues || []
	if (view.statusFilter.length) rows = rows.filter((i) => view.statusFilter.includes(i.status))
	if (view.assigneeMe) rows = rows.filter((i) => (i.assignees || []).includes(store.user))
	rows = [...rows]
	if (view.sortBy === 'priority') rows.sort((a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority])
	else if (view.sortBy === 'due') rows.sort((a, b) => (a.due_date || '9999').localeCompare(b.due_date || '9999'))
	else if (view.sortBy === 'recent') rows.sort((a, b) => (b.modified || '').localeCompare(a.modified || ''))
	else rows.sort((a, b) => (a.rank || '').localeCompare(b.rank || ''))
	return rows
})

const project = computed(() => projectByKey(props.projectKey))
const crumbs = computed(() => [
	{ label: 'Projects', icon: 'folder' },
	{ label: project.value?.project_name || props.projectKey, icon: project.value?.icon || 'folder' },
])
const headerPresence = computed(() => {
	if (!tweaks.presence) return []
	const set = new Set()
	Object.values(presence).forEach((arr) => arr.forEach((u) => set.add(u)))
	return [...set]
})
const issuePresence = computed(() => (tweaks.presence ? presence : {}))
</script>

<template>
	<div class="pjx-main">
		<PageHeader
			:crumbs="crumbs"
			:tabs="TABS"
			:active-tab="activeTab"
			:presence="headerPresence"
			:show-settings="true"
			@tab="activeTab = $event"
			@search="openPalette"
			@new="openCreate(projectKey)"
			@settings="settingsOpen = true"
		/>
		<ViewControls
			v-if="activeTab === 'list' || activeTab === 'board'"
			:statuses="board.data?.statuses || []"
			:state="view"
			:show-group="activeTab === 'list'"
			@update="Object.assign(view, $event)"
		/>
		<div
			v-if="board.data?.truncated && (activeTab === 'list' || activeTab === 'board')"
			class="pjx-trunc"
		>
			Showing the first {{ (board.data.issues || []).length }} of {{ board.data.total }} tasks. Filter to narrow results.
		</div>
		<div class="pjx-view">
			<SummaryView v-if="activeTab === 'summary'" :project-key="projectKey" />
			<ListView
				v-else-if="activeTab === 'list'"
				:project-key="projectKey"
				:issues="viewIssues"
				:statuses="board.data?.statuses || []"
				:group-by="view.groupBy"
				:presence="issuePresence"
				:loading="board.loading"
				@created="board.reload()"
				@open="openDrawer"
			/>
			<BoardView
				v-else-if="activeTab === 'board'"
				:issues="viewIssues"
				:statuses="board.data?.statuses || []"
				:presence="issuePresence"
				@changed="board.reload()"
				@open="openDrawer"
			/>
			<CalendarView
				v-else-if="activeTab === 'calendar'"
				:issues="board.data?.issues || []"
				:statuses="board.data?.statuses || []"
				@open="openDrawer"
			/>
			<ReportsView v-else-if="activeTab === 'reports'" :project-key="projectKey" />
			<GanttView v-else :project-key="projectKey" @open="openDrawer" />
		</div>
		<ProjectSettingsDialog
			:open="settingsOpen"
			:project="projectKey"
			@close="settingsOpen = false"
			@changed="board.reload()"
		/>
	</div>
</template>

<style scoped>
.pjx-trunc {
	margin: 8px 16px 0;
	padding: 6px 12px;
	border-radius: 8px;
	background: var(--surface-amber-1);
	color: var(--ink-amber-3);
	font-size: 12px;
}
</style>
