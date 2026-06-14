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

// Projects shown in the sidebar, filtered to the active workspace if one is set.
const visibleProjects = computed(() => {
	if (!ui.currentWorkspace) return store.projects
	return store.projects.filter((p) => p.workspace === ui.currentWorkspace)
})

const workspaceOptions = computed(() => [
	...store.workspaces.map((w) => ({
		label: w.workspace_name,
		onClick: () => (ui.currentWorkspace = w.name),
	})),
	{ label: 'All workspaces', onClick: () => (ui.currentWorkspace = null) },
	{ label: '+ New workspace', onClick: openCreateWorkspace },
])
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
				<router-link
					v-for="p in visibleProjects"
					:key="p.name"
					:to="`/projects/${p.key}`"
					class="nav pjx-navrow pjx-projrow"
					:class="{ active: route.params.key === p.key }"
					style="padding-left: 22px"
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
