<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Dropdown } from 'frappe-ui'
import { createResource } from 'frappe-ui'
import Icon from './Icon.vue'
import { store, reloadBootstrap } from '@/data/store'
import { ui, openCreateProject, openCreateWorkspace, openCreate } from '@/data/ui'

const route = useRoute()
const projOpen = ref(true)
const favOpen = ref(true)
const favToggler = createResource({ url: 'projex.api.toggle_favorite' })

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
		window.alert('Create a workspace first')
		return
	}
	const name = (window.prompt('New team name') || '').trim()
	if (!name) return
	await teamCreator.submit({ workspace: ws, team_name: name })
	reloadBootstrap()
}
</script>

<template>
	<aside class="pjx-side">
		<Dropdown :options="workspaceOptions" placement="left-start">
			<div class="pjx-side__ws">
				<span class="pjx-side__wsmark">{{ (currentWorkspace?.workspace_name || 'P')[0] }}</span>
				<div class="flex col" style="flex: 1; min-width: 0; line-height: 1.25">
					<span class="t-sm fw-semibold truncate">{{ currentWorkspace?.workspace_name || 'Projex' }}</span>
					<span class="t-2xs ink-5">{{ store.users.length }} members</span>
				</div>
				<Icon name="chevrons-up-down" :size="14" class="ink-5" />
			</div>
		</Dropdown>

		<div class="pjx-side__group">
			<div class="nav pjx-navrow" style="cursor: pointer" @click="openCreate(route.params.key || '')">
				<Icon name="square-pen" :size="16" />
				<span class="truncate">New task</span>
				<span class="kbd" style="margin-left: auto">c</span>
			</div>
			<router-link to="/inbox" class="nav pjx-navrow" :class="{ active: isActive('/inbox') }">
				<Icon name="inbox" :size="16" />
				<span class="truncate">Inbox</span>
				<span v-if="store.counts.inbox" class="pjx-navbadge">{{ store.counts.inbox }}</span>
			</router-link>
			<router-link to="/my-tasks" class="nav pjx-navrow" :class="{ active: isActive('/my-tasks') }">
				<Icon name="circle-check-big" :size="16" />
				<span class="truncate">My tasks</span>
			</router-link>
			<router-link v-if="store.canManageUsers" to="/users" class="nav pjx-navrow" :class="{ active: isActive('/users') }">
				<Icon name="users" :size="16" />
				<span class="truncate">Users</span>
			</router-link>
		</div>

		<div v-if="favoriteProjects.length" class="pjx-side__group">
			<div class="pjx-side__head" @click="favOpen = !favOpen">
				<span>Favorites</span>
				<Icon :name="favOpen ? 'chevron-down' : 'chevron-right'" :size="13" />
			</div>
			<template v-if="favOpen">
				<router-link
					v-for="p in favoriteProjects"
					:key="p.name"
					:to="`/projects/${p.key}`"
					class="nav pjx-navrow"
					:class="{ active: route.params.key === p.key }"
					style="padding-left: 22px"
				>
					<span class="pjx-projicon"><Icon :name="p.icon || 'folder'" :size="12" /></span>
					<span class="truncate">{{ p.project_name }}</span>
				</router-link>
			</template>
		</div>

		<div class="pjx-side__group">
			<div class="pjx-side__head" @click="projOpen = !projOpen">
				<span>Projects</span>
				<button class="pjx-side__add" title="New project" @click.stop="openCreateProject">
					<Icon name="plus" :size="14" />
				</button>
			</div>
			<template v-if="projOpen">
				<template v-for="g in teamGroups" :key="g.key">
					<div
						v-if="g.team || teamGroups.length > 1"
						class="pjx-side__teamhead"
						@click="toggleTeam(g.key)"
					>
						<Icon :name="collapsedTeams[g.key] ? 'chevron-right' : 'chevron-down'" :size="11" />
						<Icon :name="g.icon" :size="12" />
						<span class="truncate">{{ g.label }}</span>
						<span class="pjx-side__teamcount">{{ g.projects.length }}</span>
					</div>
					<template v-if="!collapsedTeams[g.key]">
						<router-link
							v-for="p in g.projects"
							:key="p.name"
							:to="`/projects/${p.key}`"
							class="nav pjx-navrow pjx-projrow"
							:class="{ active: route.params.key === p.key }"
							:style="{ paddingLeft: g.team || teamGroups.length > 1 ? '34px' : '22px' }"
						>
							<span class="pjx-projicon"><Icon :name="p.icon || 'folder'" :size="12" /></span>
							<span class="truncate">{{ p.project_name }}</span>
							<button
								class="pjx-star"
								:class="{ on: isFav(p.name) }"
								:title="isFav(p.name) ? 'Unstar' : 'Star'"
								@click="toggleFav(p.name, $event)"
							>
								<Icon :name="isFav(p.name) ? 'star' : 'star'" :size="13" />
							</button>
						</router-link>
					</template>
				</template>
				<div v-if="!visibleProjects.length" class="nav" style="padding-left: 22px; cursor: default" @click="openCreateProject">
					<Icon name="plus" :size="14" class="ink-5" />
					<span class="t-sm ink-5">Add your first project</span>
				</div>
			</template>
		</div>

		<div class="pjx-side__group">
			<router-link to="/roadmap" class="nav pjx-navrow" :class="{ active: isActive('/roadmap') }">
				<Icon name="map" :size="16" />
				<span class="truncate">Roadmap</span>
			</router-link>
		</div>

		<div class="pjx-side__foot">
			<div class="pjx-side__me">
				<Icon name="user" :size="18" class="ink-6" />
				<div class="flex col" style="flex: 1; min-width: 0; line-height: 1.2">
					<span class="t-sm fw-medium truncate">{{ store.user }}</span>
					<span class="t-2xs ink-5 flex items-center g-1"><span class="pjx-livedot" /> Active</span>
				</div>
			</div>
		</div>
	</aside>
</template>

<style scoped>
.pjx-side__teamhead {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 4px 10px 4px 22px;
	margin-top: 2px;
	cursor: pointer;
	color: var(--ink-gray-6);
	font-size: 11px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	user-select: none;
}
.pjx-side__teamhead:hover {
	color: var(--ink-gray-8);
}
.pjx-side__teamcount {
	margin-left: auto;
	font-weight: 500;
	color: var(--ink-gray-4);
}
.pjx-side__add {
	border: 0;
	background: transparent;
	cursor: pointer;
	color: var(--ink-gray-5);
	border-radius: 5px;
	width: 20px;
	height: 20px;
	display: grid;
	place-items: center;
}
.pjx-side__add:hover {
	background: var(--surface-gray-3);
	color: var(--ink-gray-8);
}
.pjx-projrow .pjx-star {
	margin-left: auto;
	border: 0;
	background: transparent;
	cursor: pointer;
	color: var(--ink-gray-4);
	opacity: 0;
	border-radius: 4px;
	width: 20px;
	height: 20px;
	display: grid;
	place-items: center;
}
.pjx-projrow:hover .pjx-star {
	opacity: 1;
}
.pjx-projrow .pjx-star.on {
	opacity: 1;
	color: var(--amber-500);
	fill: var(--amber-500);
}
.pjx-projrow .pjx-star.on :deep(svg) {
	fill: var(--amber-500);
}
</style>
