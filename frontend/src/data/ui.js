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
	settingsProject: null, // project key when settings dialog is open
	currentWorkspace: null, // selected workspace filter (null = all)
})

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
export function openSettings(project) {
	ui.settingsProject = project
}
export function closeSettings() {
	ui.settingsProject = null
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
