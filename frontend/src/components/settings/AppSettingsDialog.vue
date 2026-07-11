<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
	Avatar,
	SettingsContent,
	SettingsDialog,
	SettingsNavGroup,
	SettingsNavItem,
	SettingsPanel,
	SettingsSidebar,
} from 'frappe-ui'
import Icon from '../Icon.vue'
import ProfileSettings from './ProfileSettings.vue'
import PreferenceSettings from './PreferenceSettings.vue'
import ProjectSettings from './ProjectSettings.vue'
import { store, userById } from '@/data/store'

const open = defineModel({ type: Boolean, default: false })
const route = useRoute()
const router = useRouter()
const tab = ref('profile')
const me = computed(() => userById(store.user))
const projects = computed(() => store.projects.filter((p) => !p.is_archived))

// A deleted or archived project loses its panel — fall back to Profile, and
// leave its page if we're currently on it.
function onProjectGone(key) {
	tab.value = 'profile'
	if (route.params.key === key) router.push('/')
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
			<SettingsNavGroup v-if="projects.length" label="Projects">
				<SettingsNavItem v-for="p in projects" :key="p.key" :value="`project:${p.key}`">
					<template #prefix>
						<Icon :name="p.icon || 'folder'" :size="15" class="shrink-0 text-ink-gray-6" />
					</template>
					{{ p.project_name }}
				</SettingsNavItem>
			</SettingsNavGroup>
		</SettingsSidebar>
		<SettingsContent>
			<SettingsPanel value="profile"><ProfileSettings /></SettingsPanel>
			<SettingsPanel value="preferences"><PreferenceSettings /></SettingsPanel>
			<SettingsPanel v-for="p in projects" :key="p.key" :value="`project:${p.key}`">
				<!-- v-if keeps inactive project panels unmounted so each only loads its detail when opened -->
				<ProjectSettings v-if="tab === `project:${p.key}`" :project="p.key" @deleted="onProjectGone(p.key)" />
			</SettingsPanel>
		</SettingsContent>
	</SettingsDialog>
</template>
