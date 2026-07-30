import { reactive } from 'vue'

// Cross-component UI state (palette + drawer).
export const ui = reactive({
	paletteOpen: false,
	openIssue: null, // issue name when the Task Drawer is open
	refreshTick: 0, // bump to ask the active board to reload
	createOpen: false, // create-issue dialog
	createProject: '',
	createType: 'Task', // default issue type for the create dialog
	createProjectOpen: false, // create-project dialog
	createWorkspaceOpen: false, // create-workspace dialog
	appSettingsOpen: false, // app settings dialog (profile, preferences, projects)
	appSettingsTab: null, // tab to open the settings dialog on (null = keep last/default)
	appSettingsUser: null, // person to preselect in People access (deep-link from People)
	currentWorkspace: null, // selected workspace filter (null = all)
	sidebarCollapsed: localStorage.getItem('pjx:sidebar-collapsed') === '1',
})

export function toggleSidebar() {
	ui.sidebarCollapsed = !ui.sidebarCollapsed
	localStorage.setItem('pjx:sidebar-collapsed', ui.sidebarCollapsed ? '1' : '0')
}

export function bumpRefresh() {
	ui.refreshTick++
}

export function openCreate(defaultProject = '', type = 'Task') {
	ui.createProject = defaultProject
	ui.createType = type
	ui.createOpen = true
}
export function openReportBug(defaultProject = '') {
	openCreate(defaultProject, 'Bug')
}
export function closeCreate() {
	ui.createOpen = false
}

export function openCreateProject() {
	ui.createProjectOpen = true
}
export function openCreateWorkspace() {
	ui.createWorkspaceOpen = true
}
export function openAppSettings(tab = null, user = null) {
	ui.appSettingsTab = tab
	ui.appSettingsUser = user
	ui.appSettingsOpen = true
}

export function openPalette() {
	ui.paletteOpen = true
}
export function closePalette() {
	ui.paletteOpen = false
}
export function togglePalette() {
	ui.paletteOpen = !ui.paletteOpen
}

export function openDrawer(name) {
	ui.openIssue = name
}
export function closeDrawer() {
	ui.openIssue = null
}
