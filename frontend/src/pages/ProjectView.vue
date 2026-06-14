<script setup>
import { ref, watch, computed, onMounted, onUnmounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import SummaryView from './SummaryView.vue'
import ListView from './ListView.vue'
import BacklogView from './BacklogView.vue'
import BoardView from './BoardView.vue'
import GanttView from './GanttView.vue'
import CalendarView from './CalendarView.vue'
import ReportsView from './ReportsView.vue'
import DashboardView from './DashboardView.vue'
import DocsView from './DocsView.vue'
import ChangeLogView from './ChangeLogView.vue'
import ProjectSettingsDialog from '@/components/ProjectSettingsDialog.vue'
import { store, projectByKey } from '@/data/store'
import { openPalette, openDrawer, openCreate, ui } from '@/data/ui'
import { onRealtime, joinProjectRoom } from '@/socket'
import { tweaks } from '@/composables/useTweaks'
import { exportIssuesCsv } from '@/utils/csv'

const props = defineProps({ projectKey: { type: String, required: true } })
const router = useRouter()

function onProjectDeleted() {
	settingsOpen.value = false
	router.push('/')
}

const activeTab = ref('summary')
const settingsOpen = ref(false)
const presence = reactive({}) // issue name -> [user ids]
const integration = createResource({ url: 'projex.api.integration_status', auto: true })
const TABS = [
	{ id: 'summary', label: 'Summary' },
	{ id: 'list', label: 'List' },
	{ id: 'backlog', label: 'Backlog' },
	{ id: 'board', label: 'Board' },
	{ id: 'calendar', label: 'Calendar' },
	{ id: 'gantt', label: 'Gantt' },
	{ id: 'dashboard', label: 'Dashboard' },
	{ id: 'reports', label: 'Reports' },
	{ id: 'docs', label: 'Docs' },
	{ id: 'activity', label: 'Activity' },
]
const SIMPLE_TABS = ['summary', 'reports']

const view = reactive({ statusFilter: [], assigneeMe: false, sortBy: 'rank', groupBy: 'status' })

const board = createResource({
	url: 'projex.api.get_issues',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})

// ---- saved views (backend: save_view / get_views / delete_view) ----
const views = createResource({
	url: 'projex.api.get_views',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
const viewSaver = createResource({ url: 'projex.api.save_view' })
const viewDeleter = createResource({ url: 'projex.api.delete_view' })
const bulkUpdater = createResource({ url: 'projex.api.bulk_update_issues' })
const bulkDeleter = createResource({ url: 'projex.api.bulk_delete_issues' })

async function bulkUpdate({ names, fields }) {
	await bulkUpdater.submit({ names: JSON.stringify(names), fields: JSON.stringify(fields) })
	board.reload()
}
async function bulkDelete({ names }) {
	await bulkDeleter.submit({ names: JSON.stringify(names) })
	board.reload()
}

async function saveCurrentView(name) {
	await viewSaver.submit({
		project: props.projectKey,
		view_name: name,
		view_type: activeTab.value,
		config: JSON.stringify({ ...view }),
	})
	views.reload()
}
function applyView(v) {
	let cfg = {}
	try { cfg = JSON.parse(v.config || '{}') } catch (e) { cfg = {} }
	Object.assign(view, { statusFilter: [], assigneeMe: false, sortBy: 'rank', groupBy: 'status' }, cfg)
	if (v.view_type) activeTab.value = v.view_type
}
async function deleteView(v) {
	await viewDeleter.submit({ name: v.name })
	views.reload()
}

watch(() => props.projectKey, () => { board.reload(); views.reload() })
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
			:saved-views="views.data || []"
			@update="Object.assign(view, $event)"
			@export="exportIssuesCsv(viewIssues, board.data?.statuses || [], projectKey)"
			@save-view="saveCurrentView"
			@apply-view="applyView"
			@delete-view="deleteView"
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
				@bulk-update="bulkUpdate"
				@bulk-delete="bulkDelete"
			/>
			<BacklogView
				v-else-if="activeTab === 'backlog'"
				:project-key="projectKey"
				:issues="board.data?.issues || []"
				:statuses="board.data?.statuses || []"
				@changed="board.reload()"
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
			<DashboardView v-else-if="activeTab === 'dashboard'" :project-key="projectKey" @open="openDrawer" />
			<ReportsView v-else-if="activeTab === 'reports'" :project-key="projectKey" @open="openDrawer" />
			<DocsView v-else-if="activeTab === 'docs'" :project-key="projectKey" />
			<ChangeLogView v-else-if="activeTab === 'activity'" :project-key="projectKey" @open="openDrawer" />
			<GanttView v-else :project-key="projectKey" @open="openDrawer" />
		</div>
		<ProjectSettingsDialog
			:open="settingsOpen"
			:project="projectKey"
			@close="settingsOpen = false"
			@changed="board.reload()"
			@deleted="onProjectDeleted"
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
