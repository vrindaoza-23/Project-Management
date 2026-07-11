<script setup>
import { ref, watch, computed, onMounted, onUnmounted, reactive } from 'vue'
import { createResource } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import SummaryView from './SummaryView.vue'
import ListView from './ListView.vue'
import BacklogView from './BacklogView.vue'
import BoardView from './BoardView.vue'
import SprintBar from '@/components/SprintBar.vue'
import GanttView from './GanttView.vue'
import CalendarView from './CalendarView.vue'
import ReportsView from './ReportsView.vue'
import DashboardView from './DashboardView.vue'
import DocsView from './DocsView.vue'
import TimesheetsView from './TimesheetsView.vue'
import FinanceView from './FinanceView.vue'
import ChangeLogView from './ChangeLogView.vue'
import { store, projectByKey } from '@/data/store'
import { openPalette, openDrawer, openCreate, ui } from '@/data/ui'
import { onRealtime, joinProjectRoom } from '@/socket'
import { tweaks } from '@/composables/useTweaks'
import { exportIssuesCsv } from '@/utils/csv'

const props = defineProps({ projectKey: { type: String, required: true } })

const activeTab = ref('summary')
const presence = reactive({}) // issue name -> [user ids]
const integration = createResource({ url: 'projex.api.integration_status', auto: true })
// Views are five ways to look at one thing (Tasks) — they live inside the Tasks
// surface, not as top-level tabs.
const TASK_VIEWS = [
	{ id: 'list', label: 'List', icon: 'list-checks' },
	{ id: 'board', label: 'Board', icon: 'columns-3' },
	{ id: 'calendar', label: 'Calendar', icon: 'calendar' },
	{ id: 'gantt', label: 'Gantt', icon: 'gantt-chart' },
	{ id: 'backlog', label: 'Backlog', icon: 'layers' },
]
const TASK_VIEW_IDS = TASK_VIEWS.map((v) => v.id)
// Primary destinations. Surface id === content tab id, except Tasks (which opens
// whichever view you last used).
const SURFACES = [
	{ id: 'summary', label: 'Overview' },
	{ id: 'tasks', label: 'Tasks' },
	{ id: 'dashboard', label: 'Dashboard' },
	{ id: 'timesheets', label: 'Timesheets' },
	{ id: 'docs', label: 'Docs' },
]
// Secondary destinations fold into the "More" menu; Finance is manager-only.
const MORE_ITEMS = [
	{ id: 'reports', label: 'Reports', icon: 'bar-chart-3' },
	{ id: 'finance', label: 'Finance', icon: 'wallet', managerOnly: true },
	{ id: 'activity', label: 'Activity', icon: 'history' },
]
const MORE_IDS = MORE_ITEMS.map((m) => m.id)

const lastTaskView = ref('list')
const activeSurface = computed(() => (TASK_VIEW_IDS.includes(activeTab.value) ? 'tasks' : activeTab.value))
const moreActive = computed(() => MORE_IDS.includes(activeTab.value))
watch(activeTab, (v) => {
	if (TASK_VIEW_IDS.includes(v)) lastTaskView.value = v
})
function selectSurface(id) {
	activeTab.value = id === 'tasks' ? lastTaskView.value : id
}
// People list for the Assignee filter — current user first (labelled "Me").
const assigneeOptions = computed(() => {
	const me = store.user
	const opts = store.users.map((u) => ({ value: u.name, label: u.full_name || u.name }))
	opts.sort((a, b) => (a.value === me ? -1 : b.value === me ? 1 : 0))
	if (opts.length && opts[0].value === me) opts[0] = { ...opts[0], label: `Me (${opts[0].label})` }
	return opts
})

const DEFAULT_COLS = { labels: true, pts: true, due: true, updated: true, assignees: true }
const view = reactive({ statusFilter: [], assignees: [], sortBy: 'rank', groupBy: 'status', sprintScope: 'active', search: '', cols: { ...DEFAULT_COLS } })

const board = createResource({
	url: 'projex.api.get_issues',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})

// Cycles/sprints for the sprint-aware Board scope selector + header.
const pickers = createResource({
	url: 'projex.api.get_pickers',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
const cycles = computed(() => pickers.data?.cycles || [])
const canManageCycles = computed(() => !!pickers.data?.can_manage)
const activeCycle = computed(() => cycles.value.find((c) => c.state === 'Active') || null)
const scopedCycleName = computed(() => {
	const s = view.sprintScope
	if (s === 'all' || s === 'backlog') return null
	if (s === 'active') return activeCycle.value?.name || null
	return s
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
	Object.assign(view, { statusFilter: [], assignees: [], sortBy: 'rank', groupBy: 'status', sprintScope: 'active', search: '', cols: { ...DEFAULT_COLS } }, cfg)
	if (v.view_type) activeTab.value = v.view_type
}
async function deleteView(v) {
	await viewDeleter.submit({ name: v.name })
	views.reload()
}

watch(() => props.projectKey, () => { board.reload(); views.reload(); pickers.reload() })
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
	if (view.assignees.length) rows = rows.filter((i) => (i.assignees || []).some((a) => view.assignees.includes(a)))
	if (view.search.trim()) {
		const q = view.search.trim().toLowerCase()
		rows = rows.filter((i) => `${i.issue_id} ${i.title}`.toLowerCase().includes(q))
	}
	rows = [...rows]
	if (view.sortBy === 'priority') rows.sort((a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority])
	else if (view.sortBy === 'due') rows.sort((a, b) => (a.due_date || '9999').localeCompare(b.due_date || '9999'))
	else if (view.sortBy === 'recent') rows.sort((a, b) => (b.modified || '').localeCompare(a.modified || ''))
	else rows.sort((a, b) => (a.rank || '').localeCompare(b.rank || ''))
	return rows
})

// Board scope (sprint-aware): narrow the filtered issues to the chosen sprint.
const boardIssues = computed(() => {
	const rows = viewIssues.value
	if (view.sprintScope === 'all') return rows
	if (view.sprintScope === 'backlog') return rows.filter((i) => !i.cycle)
	const name = scopedCycleName.value
	if (!name) return view.sprintScope === 'active' ? [] : rows
	return rows.filter((i) => i.cycle === name)
})
// Issues in the scoped sprint (unfiltered) — for points + the Complete dialog.
const scopeIssues = computed(() => {
	const name = scopedCycleName.value
	if (!name) return []
	return (board.data?.issues || []).filter((i) => i.cycle === name)
})

const project = computed(() => projectByKey(props.projectKey))
const totalTasks = computed(() => board.data?.total ?? (board.data?.issues || []).length)
// Tasks carries a live count; the rest stay label-only.
const surfaces = computed(() =>
	SURFACES.map((s) => (s.id === 'tasks' ? { ...s, count: totalTasks.value } : s)),
)
const visibleMoreItems = computed(() => MORE_ITEMS.filter((m) => !m.managerOnly || canManageCycles.value))
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
			:title="project?.project_name || projectKey"
			:title-icon="project?.icon || 'folder'"
			:surfaces="surfaces"
			:active-surface="activeSurface"
			:more-items="visibleMoreItems"
			:more-active="moreActive"
			:presence="headerPresence"
			@surface="selectSurface"
			@search="openPalette"
			@new="openCreate(projectKey)"
		/>
		<ViewControls
			v-if="activeSurface === 'tasks'"
			:statuses="board.data?.statuses || []"
			:state="view"
			:views="TASK_VIEWS"
			:active-view="activeTab"
			:show-filters="activeTab === 'list' || activeTab === 'board'"
			:show-group="activeTab === 'list'"
			:saved-views="views.data || []"
			:assignee-options="assigneeOptions"
			@view="activeTab = $event"
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
				:cols="view.cols"
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
			<template v-else-if="activeTab === 'board'">
				<SprintBar
					v-model:scope="view.sprintScope"
					:project-key="projectKey"
					:cycles="cycles"
					:active-cycle="activeCycle"
					:can-manage="canManageCycles"
					:statuses="board.data?.statuses || []"
					:scope-issues="scopeIssues"
					@changed="() => { board.reload(); pickers.reload() }"
				/>
				<BoardView
					:issues="boardIssues"
					:statuses="board.data?.statuses || []"
					:presence="issuePresence"
					@changed="board.reload()"
					@open="openDrawer"
				/>
			</template>
			<CalendarView
				v-else-if="activeTab === 'calendar'"
				:issues="board.data?.issues || []"
				:statuses="board.data?.statuses || []"
				@open="openDrawer"
			/>
			<DashboardView v-else-if="activeTab === 'dashboard'" :project-key="projectKey" @open="openDrawer" />
			<ReportsView v-else-if="activeTab === 'reports'" :project-key="projectKey" @open="openDrawer" />
			<TimesheetsView v-else-if="activeTab === 'timesheets'" :project-key="projectKey" />
			<FinanceView v-else-if="activeTab === 'finance'" :project-key="projectKey" />
			<DocsView v-else-if="activeTab === 'docs'" :project-key="projectKey" />
			<ChangeLogView v-else-if="activeTab === 'activity'" :project-key="projectKey" @open="openDrawer" />
			<GanttView v-else :project-key="projectKey" @open="openDrawer" />
		</div>
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
