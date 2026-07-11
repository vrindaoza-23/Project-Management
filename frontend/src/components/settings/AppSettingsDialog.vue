<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
	Avatar,
	SettingsContent,
	SettingsDialog,
	SettingsNavGroup,
	SettingsNavItem,
	SettingsPanel,
	SettingsSidebar,
	createResource,
} from 'frappe-ui'
import Icon from '../Icon.vue'
import SelectField from '../SelectField.vue'
import ProfileSettings from './ProfileSettings.vue'
import PreferenceSettings from './PreferenceSettings.vue'
import IntegrationsSettings from './IntegrationsSettings.vue'
import ProjectGeneralSettings from './ProjectGeneralSettings.vue'
import ProjectMembersSettings from './ProjectMembersSettings.vue'
import ProjectLabelsSettings from './ProjectLabelsSettings.vue'
import ProjectCyclesSettings from './ProjectCyclesSettings.vue'
import ProjectErpSettings from './ProjectErpSettings.vue'
import WorkspaceGeneralSettings from './WorkspaceGeneralSettings.vue'
import WorkspaceMembersSettings from './WorkspaceMembersSettings.vue'
import WorkspaceTeamsSettings from './WorkspaceTeamsSettings.vue'
import { store, userById } from '@/data/store'
import { ui } from '@/data/ui'

const open = defineModel({ type: Boolean, default: false })
const route = useRoute()
const router = useRouter()
const tab = ref('profile')
const me = computed(() => userById(store.user))

// Each settings section is a nav item; WHICH project/workspace it edits is the
// switcher above its group — scales to any number, unlike a per-entity list.
const WORKSPACE_SECTIONS = [
	{ value: 'workspace-general', label: 'General', icon: 'settings', component: WorkspaceGeneralSettings },
	{ value: 'workspace-members', label: 'Members', icon: 'users', component: WorkspaceMembersSettings },
	{ value: 'workspace-teams', label: 'Teams', icon: 'users', component: WorkspaceTeamsSettings },
]
const PROJECT_SECTIONS = [
	{ value: 'project-general', label: 'General', icon: 'settings', component: ProjectGeneralSettings },
	{ value: 'project-members', label: 'Members', icon: 'users', component: ProjectMembersSettings },
	{ value: 'project-labels', label: 'Labels', icon: 'tag', component: ProjectLabelsSettings },
	{ value: 'project-cycles', label: 'Cycles', icon: 'calendar-range', component: ProjectCyclesSettings },
	{ value: 'project-erpnext', label: 'ERPNext', icon: 'link-2', component: ProjectErpSettings },
]

// Only workspaces the user can actually open (get_workspace_detail gates reads
// to members + privileged users). is_member comes from bootstrap.
const workspaces = computed(() => store.workspaces.filter((w) => w.is_member))
const workspaceOptions = computed(() => workspaces.value.map((w) => ({ value: w.name, label: w.workspace_name })))
const projects = computed(() => store.projects.filter((p) => !p.is_archived))
const projectOptions = computed(() => projects.value.map((p) => ({ value: p.key, label: p.project_name })))

// --- workspace switcher + shared detail ---
const workspaceKey = ref('')
const wsLoadedKey = ref('')
const wsDetail = createResource({ url: 'projex.api.get_workspace_detail' })
function loadWorkspace() {
	const k = workspaceKey.value
	if (!k) return
	wsDetail.submit({ workspace: k }).then(() => (wsLoadedKey.value = k))
}
watch(workspaceKey, loadWorkspace)

// --- project switcher + shared detail ---
const projectKey = ref('')
const projLoadedKey = ref('')
const projDetail = createResource({ url: 'projex.api.get_project_detail' })
function loadProject() {
	const k = projectKey.value
	if (!k) return
	projDetail.submit({ project: k }).then(() => (projLoadedKey.value = k))
}
watch(projectKey, loadProject)

// Opening is context-aware: pre-select the workspace/project on screen, else keep
// the last selection, else the first available. Refresh even if the key is unchanged.
watch(open, (v) => {
	if (!v) return
	const wsValid = (k) => !!k && workspaces.value.some((w) => w.name === k)
	const wsTarget = wsValid(ui.currentWorkspace) ? ui.currentWorkspace : wsValid(workspaceKey.value) ? workspaceKey.value : workspaces.value[0]?.name || ''
	if (wsTarget !== workspaceKey.value) workspaceKey.value = wsTarget
	else loadWorkspace()

	const projValid = (k) => !!k && projects.value.some((p) => p.key === k)
	const projTarget = projValid(route.params.key) ? route.params.key : projValid(projectKey.value) ? projectKey.value : projects.value[0]?.key || ''
	if (projTarget !== projectKey.value) projectKey.value = projTarget
	else loadProject()
})

// A deleted/archived project loses its panels — move to the next, leave its page.
function onProjectGone(key) {
	if (route.params.key === key) router.push('/')
	const rest = projects.value.filter((p) => p.key !== key)
	projectKey.value = rest[0]?.key || ''
	if (!projectKey.value) tab.value = 'profile'
}
function onWorkspaceGone(key) {
	const rest = workspaces.value.filter((w) => w.name !== key)
	workspaceKey.value = rest[0]?.name || ''
	if (!workspaceKey.value) tab.value = 'profile'
}
</script>

<template>
	<SettingsDialog v-model="open" v-model:tab="tab">
		<SettingsSidebar>
			<SettingsNavGroup label="User settings">
				<SettingsNavItem value="profile">
					<template #prefix>
						<Avatar size="xs" :image="me?.user_image" :label="me?.full_name || store.user" class="shrink-0" />
					</template>
					Profile
				</SettingsNavItem>
				<SettingsNavItem value="preferences">
					<template #prefix>
						<span class="lucide-sliders-horizontal size-4 shrink-0 text-ink-gray-6" />
					</template>
					Preferences
				</SettingsNavItem>
			</SettingsNavGroup>

			<SettingsNavGroup label="Integrations">
				<SettingsNavItem value="integrations">
					<template #prefix>
						<Icon name="plug" :size="15" class="shrink-0 text-ink-gray-6" />
					</template>
					Integrations
				</SettingsNavItem>
			</SettingsNavGroup>

			<SettingsNavGroup v-if="workspaces.length" label="Workspace settings">
				<div class="px-1 pb-1">
					<SelectField
						:options="workspaceOptions"
						:model-value="workspaceKey"
						placeholder="Select workspace"
						@change="(v) => v && (workspaceKey = v)"
					/>
				</div>
				<SettingsNavItem v-for="s in WORKSPACE_SECTIONS" :key="s.value" :value="s.value">
					<template #prefix>
						<Icon :name="s.icon" :size="15" class="shrink-0 text-ink-gray-6" />
					</template>
					{{ s.label }}
				</SettingsNavItem>
			</SettingsNavGroup>

			<SettingsNavGroup v-if="projects.length" label="Project settings">
				<div class="px-1 pb-1">
					<SelectField
						:options="projectOptions"
						:model-value="projectKey"
						placeholder="Select project"
						@change="(v) => v && (projectKey = v)"
					/>
				</div>
				<SettingsNavItem v-for="s in PROJECT_SECTIONS" :key="s.value" :value="s.value">
					<template #prefix>
						<Icon :name="s.icon" :size="15" class="shrink-0 text-ink-gray-6" />
					</template>
					{{ s.label }}
				</SettingsNavItem>
			</SettingsNavGroup>
		</SettingsSidebar>

		<SettingsContent>
			<SettingsPanel value="profile"><ProfileSettings /></SettingsPanel>
			<SettingsPanel value="preferences"><PreferenceSettings /></SettingsPanel>
			<SettingsPanel value="integrations"><IntegrationsSettings v-if="tab === 'integrations'" /></SettingsPanel>

			<SettingsPanel v-for="s in WORKSPACE_SECTIONS" :key="s.value" :value="s.value">
				<component
					:is="s.component"
					v-if="tab === s.value && wsDetail.data && wsLoadedKey === workspaceKey"
					:key="workspaceKey"
					:workspace="workspaceKey"
					:data="wsDetail.data"
					@reload="loadWorkspace"
					@deleted="onWorkspaceGone"
				/>
			</SettingsPanel>

			<SettingsPanel v-for="s in PROJECT_SECTIONS" :key="s.value" :value="s.value">
				<!-- Mount only the active section once its project's detail has loaded;
				     re-key on switch so per-panel state (invite links, forms) resets. -->
				<component
					:is="s.component"
					v-if="tab === s.value && projDetail.data && projLoadedKey === projectKey"
					:key="projectKey"
					:project="projectKey"
					:data="projDetail.data"
					@reload="loadProject"
					@deleted="onProjectGone"
				/>
			</SettingsPanel>
		</SettingsContent>
	</SettingsDialog>
</template>
