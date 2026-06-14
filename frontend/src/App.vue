<script setup>
import { useRouter, useRoute } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import TaskDrawer from '@/components/TaskDrawer.vue'
import CreateIssueDialog from '@/components/CreateIssueDialog.vue'
import CreateProjectDialog from '@/components/CreateProjectDialog.vue'
import CreateWorkspaceDialog from '@/components/CreateWorkspaceDialog.vue'
import TweaksPanel from '@/components/TweaksPanel.vue'
import { initStore } from '@/data/store'
import { ui, togglePalette, closePalette, closeDrawer, bumpRefresh, openCreate, closeCreate } from '@/data/ui'
import { useTweaks } from '@/composables/useTweaks'
import { useKeyboard } from '@/composables/useKeyboard'

const router = useRouter()
const route = useRoute()

initStore()
useTweaks()
useKeyboard({
	onPalette: togglePalette,
	onEscape: () => {
		closePalette()
		closeDrawer()
		closeCreate()
	},
	onGo: (where) => router.push('/' + where),
	onNew: () => openCreate(route.params.key || ''),
})
</script>

<template>
	<div class="fu-app">
		<div class="pjx-app">
			<AppSidebar />
			<router-view />
		</div>
		<CommandPalette :open="ui.paletteOpen" @close="closePalette" @new="openCreate(route.params.key || '')" />
		<TaskDrawer :name="ui.openIssue" @close="closeDrawer" @changed="bumpRefresh" />
		<CreateIssueDialog
			:open="ui.createOpen"
			:default-project="ui.createProject"
			@close="closeCreate"
			@created="bumpRefresh"
		/>
		<CreateProjectDialog :open="ui.createProjectOpen" @close="ui.createProjectOpen = false" />
		<CreateWorkspaceDialog :open="ui.createWorkspaceOpen" @close="ui.createWorkspaceOpen = false" />
		<TweaksPanel />
	</div>
</template>
