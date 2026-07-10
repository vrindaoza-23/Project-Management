<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Dropdown, Sidebar, SidebarItem, SidebarLabel, SidebarCollapseToggle, createResource } from 'frappe-ui'
import Icon from './Icon.vue'
import { store, reloadBootstrap } from '@/data/store'
import { ui, openCreateProject, openCreateWorkspace, openCreate } from '@/data/ui'
import { notify, notifyError, promptText } from '@/utils/feedback'

const route = useRoute()
const favToggler = createResource({ url: 'projex.api.toggle_favorite' })

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
async function toggleFav(key, e) {
	e.preventDefault()
	e.stopPropagation()
	await favToggler.submit({ project: key })
	reloadBootstrap()
}
function isFav(key) {
	return (store.favorites || []).includes(key)
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

const workspaceOptions = computed(() => [
	...store.workspaces.map((w) => ({
		label: w.workspace_name,
		onClick: () => (ui.currentWorkspace = w.name),
	})),
	{ label: 'All workspaces', onClick: () => (ui.currentWorkspace = null) },
	{ label: '+ New workspace', onClick: openCreateWorkspace },
	{ label: '+ New team', onClick: () => newTeam() },
])

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
		<!-- Workspace switcher -->
		<div class="pjx-side__head">
			<Dropdown :options="workspaceOptions" placement="right-start">
				<button class="pjx-ws" :class="{ 'is-collapsed': collapsed }">
					<span class="pjx-side__wsmark">{{ (currentWorkspace?.workspace_name || 'P')[0] }}</span>
					<template v-if="!collapsed">
						<span class="pjx-ws__meta">
							<span class="pjx-ws__name truncate">{{ currentWorkspace?.workspace_name || 'Projex' }}</span>
							<span class="pjx-ws__sub">{{ store.users.length }} members</span>
						</span>
						<Icon name="chevrons-up-down" :size="14" class="ink-5" />
					</template>
				</button>
			</Dropdown>
		</div>

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
			<SidebarItem v-if="store.canManageUsers" label="Users" to="/users" :active="isActive('/users')">
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
					<SidebarItem
						v-for="p in g.projects"
						:key="p.name"
						:label="p.project_name"
						:to="`/projects/${p.key}`"
						:active="route.params.key === p.key"
					>
						<template #prefix><Icon :name="p.icon || 'folder'" :size="15" /></template>
						<template #suffix>
							<button
								class="pjx-star"
								:class="{ on: isFav(p.name) }"
								:title="isFav(p.name) ? 'Unstar' : 'Star'"
								@click="toggleFav(p.name, $event)"
							>
								<Icon name="star" :size="13" />
							</button>
						</template>
					</SidebarItem>
				</template>
			</template>
			<SidebarItem
				v-if="!visibleProjects.length && !collapsed"
				label="Add your first project"
				@click="openCreateProject"
			>
				<template #prefix><Icon name="plus" :size="15" /></template>
			</SidebarItem>

			<SidebarLabel divider>&nbsp;</SidebarLabel>
			<SidebarItem label="Roadmap" to="/roadmap" :active="isActive('/roadmap')">
				<template #prefix><Icon name="map" :size="16" /></template>
			</SidebarItem>
		</div>

		<!-- Footer: collapse toggle + current user -->
		<div class="pjx-side__foot">
			<SidebarCollapseToggle />
			<div class="pjx-side__me">
				<Icon name="user" :size="18" class="ink-6" />
				<div v-if="!collapsed" class="flex col" style="flex: 1; min-width: 0; line-height: 1.2">
					<span class="t-sm fw-medium truncate">{{ store.user }}</span>
					<span class="t-2xs ink-5 flex items-center g-1"><span class="pjx-livedot" /> Active</span>
				</div>
			</div>
		</div>
	</Sidebar>
</template>

<style scoped>
.pjx-side__head {
	padding: 8px;
}
.pjx-ws {
	display: flex;
	align-items: center;
	gap: 10px;
	width: 100%;
	height: 40px;
	padding: 0 8px;
	border: 0;
	background: transparent;
	border-radius: 8px;
	cursor: pointer;
}
.pjx-ws:hover {
	background: var(--surface-gray-2);
}
.pjx-ws.is-collapsed {
	justify-content: center;
	padding: 0;
}
.pjx-ws__meta {
	display: flex;
	flex-direction: column;
	flex: 1;
	min-width: 0;
	line-height: 1.25;
	text-align: left;
}
.pjx-ws__name {
	font-size: 13px;
	font-weight: 600;
	color: var(--ink-gray-9);
}
.pjx-ws__sub {
	font-size: 11px;
	color: var(--ink-gray-5);
}
.pjx-side__body {
	flex: 1;
	min-height: 0;
	overflow-x: hidden;
	overflow-y: auto;
	padding: 2px 8px 8px;
	display: flex;
	flex-direction: column;
	gap: 1px;
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
.pjx-star {
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
:deep([data-slot='sidebar-item']:hover) .pjx-star {
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
	border-top: 1px solid var(--outline-gray-1);
	padding: 6px 8px 8px;
}
.pjx-side__me {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 6px 8px;
	border-radius: 8px;
}
.pjx-livedot {
	width: 6px;
	height: 6px;
	border-radius: 9999px;
	background: var(--green-500);
	display: inline-block;
}
</style>
