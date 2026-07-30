<script setup>
import { h, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
	Sidebar,
	SidebarHeader,
	SidebarItem,
	SidebarLabel,
	SidebarCollapseToggle,
	Dropdown,
	ContextMenu,
	createResource,
} from 'frappe-ui'
import Icon from './Icon.vue'
import { store, reloadBootstrap, userName } from '@/data/store'
import { ui, openCreateProject, openCreateWorkspace, openCreate, openAppSettings } from '@/data/ui'
import { tweaks, setTweak } from '@/composables/useTweaks'
import { notify, notifyError, promptText, confirm } from '@/utils/feedback'

const route = useRoute()
const router = useRouter()
const favToggler = createResource({ url: 'projex.api.toggle_favorite' })
const archiver = createResource({ url: 'projex.api.archive_project' })
const deleter = createResource({ url: 'projex.api.delete_project' })

// Collapse state (persisted) drives frappe-ui's <Sidebar v-model:collapsed>.
const collapsed = computed({
	get: () => ui.sidebarCollapsed,
	set: (v) => {
		ui.sidebarCollapsed = v
		localStorage.setItem('pjx:sidebar-collapsed', v ? '1' : '0')
	},
})

function isActive(path) {
	return route.path === path
}

const favoriteProjects = computed(() =>
	store.projects.filter((p) => (store.favorites || []).includes(p.name)),
)
async function doToggleFav(key) {
	await favToggler.submit({ project: key })
	reloadBootstrap()
}
function toggleFav(key, e) {
	e.preventDefault()
	e.stopPropagation()
	doToggleFav(key)
}
function isFav(key) {
	return (store.favorites || []).includes(key)
}

// If the project the user is currently viewing leaves the sidebar (archived or
// deleted), fall back to the default route so ProjectView doesn't 404.
function leaveIfActive(p) {
	if (route.params.key === p.key) router.push('/inbox')
}

async function archiveProject(p) {
	try {
		await archiver.submit({ project: p.name, archived: 1 })
		leaveIfActive(p)
		await reloadBootstrap()
		notify.success(`“${p.project_name}” archived`)
	} catch (e) {
		notifyError(e, 'Could not archive project')
	}
}

async function deleteProject(p) {
	const ok = await confirm({
		title: `Delete project “${p.project_name}”`,
		message: 'All of its tasks, labels and cycles will be permanently deleted. This cannot be undone.',
		confirmLabel: 'Delete project',
		theme: 'red',
	})
	if (!ok) return
	try {
		await deleter.submit({ project: p.name })
		leaveIfActive(p)
		await reloadBootstrap()
		notify.success(`“${p.project_name}” deleted`)
	} catch (e) {
		notifyError(e, 'Could not delete project')
	}
}

// Shared row menu for both the hover "⋯" dropdown and the right-click context
// menu. Archive/Delete only appear where the user can manage the project.
const menuIcon = (name) => ({ render: () => h(Icon, { name, size: 15 }) })
function rowMenu(p) {
	const items = [
		{
			label: isFav(p.name) ? 'Remove from favorites' : 'Add to favorites',
			icon: menuIcon('star'),
			onClick: () => doToggleFav(p.name),
		},
	]
	if (p.can_manage) {
		items.push({ label: 'Archive', icon: menuIcon('archive'), onClick: () => archiveProject(p) })
		items.push({ label: 'Delete', icon: menuIcon('trash-2'), theme: 'red', onClick: () => deleteProject(p) })
	}
	return items
}

const currentWorkspace = computed(() =>
	store.workspaces.find((w) => w.name === ui.currentWorkspace) || store.workspaces[0],
)

// Projects shown in the sidebar: never archived, filtered to the active
// workspace if one is set.
const visibleProjects = computed(() => {
	const active = store.projects.filter((p) => !p.is_archived)
	if (!ui.currentWorkspace) return active
	return active.filter((p) => p.workspace === ui.currentWorkspace)
})

// Header dropdown, Helpdesk/CRM-style: Apps submenu, workspace switcher,
// create actions, log out.
const installedApps = createResource({ url: 'frappe.apps.get_apps', cache: 'apps', auto: true })
const session = createResource({
	url: 'logout',
	onSuccess: () => (window.location.href = '/login'),
})

const headerMenu = computed(() => [
	{
		group: 'apps',
		hideLabel: true,
		options: [
			{
				label: 'Apps',
				icon: 'lucide-layout-grid',
				condition: () => (installedApps.data || []).length > 0,
				submenu: (installedApps.data || []).map((app) => ({
					label: app.title,
					slots: appLogoSlot(app),
					onClick: () => (window.location.href = app.route),
				})),
			},
		],
	},
	{
		group: 'Workspaces',
		options: [
			...store.workspaces.map((w) => ({
				label: w.workspace_name,
				selected: w.name === ui.currentWorkspace,
				onClick: () => (ui.currentWorkspace = w.name),
			})),
			{
				label: 'All workspaces',
				selected: !ui.currentWorkspace,
				onClick: () => (ui.currentWorkspace = null),
			},
		],
	},
	{
		group: 'create',
		hideLabel: true,
		options: [
			{ label: 'New workspace', icon: 'lucide-plus', onClick: openCreateWorkspace },
			{ label: 'New team', icon: 'lucide-users', onClick: () => newTeam() },
		],
	},
	{
		group: 'session',
		hideLabel: true,
		options: [
			{ label: 'Settings', icon: 'lucide-settings', onClick: openAppSettings },
			{
				label: 'Dark mode',
				icon: 'lucide-moon',
				switch: true,
				switchValue: tweaks.dark,
				onClick: (v) => setTweak('dark', v),
			},
			{ label: 'Log out', icon: 'lucide-log-out', onClick: () => session.submit() },
		],
	},
])

function appLogoSlot(app) {
	if (!app.logo) return undefined
	return { prefix: () => h('img', { src: app.logo, class: 'size-4 rounded-sm', alt: '' }) }
}

// Group visible projects under their team; ungrouped projects fall into a
// trailing "No team" bucket. With no teams at all, there's a single bucket
// and no extra sub-headers are shown.
const collapsedTeams = ref({})
function toggleTeam(key) {
	collapsedTeams.value = { ...collapsedTeams.value, [key]: !collapsedTeams.value[key] }
}
const teamGroups = computed(() => {
	const teamsInScope = store.teams.filter(
		(t) => !ui.currentWorkspace || t.workspace === ui.currentWorkspace,
	)
	const byTeam = Object.fromEntries(teamsInScope.map((t) => [t.name, []]))
	const ungrouped = []
	for (const p of visibleProjects.value) {
		if (p.team && byTeam[p.team]) byTeam[p.team].push(p)
		else ungrouped.push(p)
	}
	const groups = teamsInScope
		.map((t) => ({ key: t.name, team: t, label: t.team_name, icon: t.icon || 'users', projects: byTeam[t.name] }))
		.filter((g) => g.projects.length)
	if (ungrouped.length) {
		groups.push({ key: '__none', team: null, label: 'No team', icon: 'folder', projects: ungrouped })
	}
	return groups
})

const teamCreator = createResource({ url: 'projex.api.create_team' })
async function newTeam() {
	const ws = currentWorkspace.value?.name
	if (!ws) {
		notify.warning('Create a workspace first')
		return
	}
	const name = await promptText({
		title: 'New team',
		label: 'Team name',
		placeholder: 'e.g. Platform',
		confirmLabel: 'Create team',
	})
	if (!name) return
	try {
		await teamCreator.submit({ workspace: ws, team_name: name })
		reloadBootstrap()
		notify.success(`Team “${name}” created`)
	} catch (e) {
		notifyError(e, 'Could not create team')
	}
}
</script>

<template>
	<Sidebar v-model:collapsed="collapsed" width="232px" collapsed-width="56px" class="pjx-side">
		<!-- Workspace switcher + session menu (Helpdesk/CRM-style header) -->
		<SidebarHeader
			:title="currentWorkspace?.workspace_name || 'Projex'"
			:subtitle="userName(store.user)"
			:menu-items="headerMenu"
		>
			<template #logo>
				<div class="pjx-side__mark">{{ (currentWorkspace?.workspace_name || 'P')[0] }}</div>
			</template>
		</SidebarHeader>

		<!-- Scrollable nav -->
		<div class="pjx-side__body">
			<SidebarItem label="New task" @click="openCreate(route.params.key || '')">
				<template #prefix><Icon name="square-pen" :size="16" /></template>
				<template #suffix><span class="kbd">c</span></template>
			</SidebarItem>
			<SidebarItem label="Inbox" to="/inbox" :active="isActive('/inbox')">
				<template #prefix><Icon name="inbox" :size="16" /></template>
				<template #suffix>
					<span v-if="store.counts.inbox" class="pjx-navbadge">{{ store.counts.inbox }}</span>
				</template>
			</SidebarItem>
			<SidebarItem label="My tasks" to="/my-tasks" :active="isActive('/my-tasks')">
				<template #prefix><Icon name="circle-check-big" :size="16" /></template>
			</SidebarItem>
			<SidebarItem v-if="store.canManageUsers" label="People" to="/users" :active="isActive('/users')">
				<template #prefix><Icon name="users" :size="16" /></template>
			</SidebarItem>

			<template v-if="favoriteProjects.length">
				<SidebarLabel divider>Favorites</SidebarLabel>
				<SidebarItem
					v-for="p in favoriteProjects"
					:key="p.name"
					:label="p.project_name"
					:to="`/projects/${p.key}`"
					:active="route.params.key === p.key"
				>
					<template #prefix><Icon :name="p.icon || 'folder'" :size="15" /></template>
				</SidebarItem>
			</template>

			<div class="pjx-side__labelrow">
				<SidebarLabel divider>Projects</SidebarLabel>
				<button v-if="!collapsed" class="pjx-side__add" title="New project" @click="openCreateProject">
					<Icon name="plus" :size="14" />
				</button>
			</div>
			<template v-for="g in teamGroups" :key="g.key">
				<SidebarItem
					v-if="!collapsed && (g.team || teamGroups.length > 1)"
					:label="g.label"
					@click="toggleTeam(g.key)"
				>
					<template #prefix>
						<Icon :name="collapsedTeams[g.key] ? 'chevron-right' : 'chevron-down'" :size="14" />
					</template>
					<template #suffix><span class="pjx-navbadge">{{ g.projects.length }}</span></template>
				</SidebarItem>
				<template v-if="collapsed || !collapsedTeams[g.key]">
					<ContextMenu v-for="p in g.projects" :key="p.name" :options="rowMenu(p)">
						<div class="pjx-side__row">
							<SidebarItem
								:label="p.project_name"
								:to="`/projects/${p.key}`"
								:active="route.params.key === p.key"
							>
								<template #prefix><Icon :name="p.icon || 'folder'" :size="15" /></template>
								<template #suffix>
									<span class="pjx-side__rowacts">
										<button
											class="pjx-star"
											:class="{ on: isFav(p.name) }"
											:title="isFav(p.name) ? 'Unstar' : 'Star'"
											@click="toggleFav(p.name, $event)"
										>
											<Icon name="star" :size="13" />
										</button>
										<Dropdown :options="rowMenu(p)" side="right" align="start">
											<button class="pjx-more" title="More" @pointerdown.stop @click.stop.prevent>
												<Icon name="ellipsis" :size="15" />
											</button>
										</Dropdown>
									</span>
								</template>
							</SidebarItem>
						</div>
					</ContextMenu>
				</template>
			</template>
			<SidebarItem
				v-if="!visibleProjects.length && !collapsed"
				label="Add your first project"
				@click="openCreateProject"
			>
				<template #prefix><Icon name="plus" :size="15" /></template>
			</SidebarItem>

			<SidebarItem class="pjx-side__sect" label="Roadmap" to="/roadmap" :active="isActive('/roadmap')">
				<template #prefix><Icon name="map" :size="16" /></template>
			</SidebarItem>
		</div>

		<!-- Footer: collapse toggle only — user identity lives in the header -->
		<div class="pjx-side__foot">
			<SidebarCollapseToggle />
		</div>
	</Sidebar>
</template>

<style scoped>
.pjx-side__mark {
	width: 100%;
	height: 100%;
	display: grid;
	place-items: center;
	background: var(--surface-gray-7);
	color: var(--surface-white);
	font-size: 14px;
	font-weight: 600;
}
.pjx-side__body {
	flex: 1;
	min-height: 0;
	overflow-x: hidden;
	overflow-y: auto;
	padding: 2px 8px 8px;
	display: flex;
	flex-direction: column;
	gap: 2px;
}
/* Section rhythm (Helpdesk-style): clear space above each section header and
   the trailing Roadmap group, so groups read apart from the flat row grid.
   Child-component roots carry the parent scope id, so no :deep needed. */
.pjx-side__body > [data-slot='sidebar-label'],
.pjx-side__labelrow,
.pjx-side__sect {
	margin-top: 12px;
}
.pjx-side__labelrow {
	display: flex;
	align-items: center;
}
.pjx-side__labelrow > :first-child {
	flex: 1;
}
.pjx-side__add {
	flex: none;
	width: 22px;
	height: 22px;
	display: grid;
	place-items: center;
	border: 0;
	background: transparent;
	color: var(--ink-gray-5);
	border-radius: 6px;
	cursor: pointer;
}
.pjx-side__add:hover {
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
}
.pjx-navbadge {
	min-width: 18px;
	height: 18px;
	padding: 0 5px;
	display: inline-grid;
	place-items: center;
	border-radius: 9999px;
	font-size: 11px;
	font-variant-numeric: tabular-nums;
	background: var(--surface-gray-3);
	color: var(--ink-gray-6);
}
/* The ContextMenu trigger wraps each project row; display:contents keeps the
   SidebarItem a direct flex child of the nav body so gap/spacing are unchanged. */
.pjx-side__row {
	display: contents;
}
.pjx-side__rowacts {
	display: inline-flex;
	align-items: center;
	gap: 1px;
}
.pjx-star,
.pjx-more {
	border: 0;
	background: transparent;
	cursor: pointer;
	color: var(--ink-gray-4);
	opacity: 0;
	border-radius: 4px;
	width: 22px;
	height: 22px;
	display: grid;
	place-items: center;
}
.pjx-more:hover {
	background: var(--surface-gray-3);
	color: var(--ink-gray-7);
}
/* Reveal the row actions on hover; the ⋯ also stays visible while its menu is
   open (reka sets data-state="open" on the trigger). */
:deep([data-slot='sidebar-item']:hover) .pjx-star,
:deep([data-slot='sidebar-item']:hover) .pjx-more,
.pjx-more[data-state='open'] {
	opacity: 1;
}
.pjx-star.on {
	opacity: 1;
	color: var(--amber-500);
}
.pjx-star.on :deep(svg) {
	fill: var(--amber-500);
}
.pjx-side__foot {
	margin-top: auto;
	padding: 4px 8px 8px;
}
</style>
