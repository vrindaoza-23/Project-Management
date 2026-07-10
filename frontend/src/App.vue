<script setup>
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { createResource, FrappeUIProvider } from 'frappe-ui'
import AppSidebar from '@/components/AppSidebar.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import TaskDrawer from '@/components/TaskDrawer.vue'
import CreateIssueDialog from '@/components/CreateIssueDialog.vue'
import CreateProjectDialog from '@/components/CreateProjectDialog.vue'
import CreateWorkspaceDialog from '@/components/CreateWorkspaceDialog.vue'
import TweaksPanel from '@/components/TweaksPanel.vue'
import ConfirmHost from '@/components/ConfirmHost.vue'
import Icon from '@/components/Icon.vue'
import { notifyError } from '@/utils/feedback'
import { initStore, reloadBootstrap } from '@/data/store'
import { ui, togglePalette, closePalette, closeDrawer, bumpRefresh, openCreate, closeCreate, toggleSidebar } from '@/data/ui'
import { useTweaks } from '@/composables/useTweaks'
import { useKeyboard } from '@/composables/useKeyboard'

const router = useRouter()
const route = useRoute()

initStore()

// If the app was opened from an invite link (?invite=token), join the project
// then strip the token from the URL.
onMounted(async () => {
	const params = new URLSearchParams(window.location.search)
	const token = params.get('invite')
	if (!token) return
	try {
		const res = await createResource({ url: 'projex.api.accept_invite' }).submit({ token })
		reloadBootstrap()
		if (res?.key) router.replace(`/projects/${res.key}`)
		else router.replace('/')
	} catch (e) {
		notifyError(e, 'This invite link is invalid or has expired.')
		router.replace('/')
	}
})
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
	<FrappeUIProvider>
		<div class="fu-app">
			<div class="pjx-app" :class="{ 'is-sidebar-collapsed': ui.sidebarCollapsed }">
				<AppSidebar />
				<router-view />
			</div>
			<button v-if="ui.sidebarCollapsed" class="pjx-reopen" title="Open sidebar" @click="toggleSidebar">
				<Icon name="panel-left" :size="16" />
			</button>
			<CommandPalette :open="ui.paletteOpen" @close="closePalette" @new="openCreate(route.params.key || '')" />
			<TaskDrawer :name="ui.openIssue" @close="closeDrawer" @changed="bumpRefresh" />
			<CreateIssueDialog
				:open="ui.createOpen"
				:default-project="ui.createProject"
				:default-type="ui.createType"
				@close="closeCreate"
				@created="bumpRefresh"
			/>
			<CreateProjectDialog :open="ui.createProjectOpen" @close="ui.createProjectOpen = false" />
			<CreateWorkspaceDialog :open="ui.createWorkspaceOpen" @close="ui.createWorkspaceOpen = false" />
			<TweaksPanel />
			<ConfirmHost />
		</div>
	</FrappeUIProvider>
</template>
