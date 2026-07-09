<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { createResource, Dialog, Button, FormControl } from 'frappe-ui'
import Icon from './Icon.vue'
import SelectField from './SelectField.vue'
import { store, reloadBootstrap } from '@/data/store'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['close'])
const router = useRouter()

const name = ref('')
const key = ref('')
const icon = ref('folder')
const color = ref('var(--blue-500)')
const workspace = ref('')
const team = ref('')
const members = ref([])
const error = ref('')
const keyEdited = ref(false)

const creator = createResource({ url: 'projex.api.create_project' })

watch(
	() => props.open,
	(v) => {
		if (v) {
			name.value = ''
			key.value = ''
			icon.value = 'folder'
			color.value = 'var(--blue-500)'
			workspace.value = store.workspaces[0]?.name || ''
			team.value = ''
			members.value = []
			error.value = ''
			keyEdited.value = false
		}
	},
)

// Auto-suggest a key from the name until the user edits it manually.
watch(name, (n) => {
	if (!keyEdited.value) key.value = n.replace(/[^a-zA-Z]/g, '').slice(0, 3).toUpperCase()
})

const ICONS = ['folder', 'credit-card', 'sparkles', 'smartphone', 'megaphone', 'server', 'microscope', 'rocket', 'bug', 'box']
const COLORS = ['var(--blue-500)', 'var(--violet-500)', 'var(--green-600)', 'var(--orange-500)', 'var(--teal-600)', 'var(--red-500)']

const workspaceOptions = computed(() => store.workspaces.map((w) => ({ value: w.name, label: w.workspace_name })))
// Teams available for the chosen workspace (optional grouping).
const teamOptions = computed(() => [
	{ value: '', label: 'No team' },
	...store.teams
		.filter((t) => !workspace.value || t.workspace === workspace.value)
		.map((t) => ({ value: t.name, label: t.team_name })),
])
// Clear the team if it no longer belongs to the selected workspace.
watch(workspace, () => {
	if (team.value && !teamOptions.value.some((o) => o.value === team.value)) team.value = ''
})
const userOptions = computed(() => store.users.map((u) => ({ value: u.name, label: u.full_name || u.name })))

async function submit() {
	error.value = ''
	if (!name.value.trim()) return (error.value = 'Project name is required')
	if (!/^[A-Za-z]{2,4}$/.test(key.value)) return (error.value = 'Key must be 2-4 letters')
	try {
		const res = await creator.submit({
			payload: JSON.stringify({
				project_name: name.value.trim(),
				key: key.value.toUpperCase(),
				icon: icon.value,
				color: color.value,
				workspace: workspace.value || null,
				team: team.value || null,
				members: members.value.map((u) => ({ user: u, role: 'Member' })),
			}),
		})
		await reloadBootstrap()
		emit('close')
		router.push(`/projects/${res.key}`)
	} catch (e) {
		error.value = e?.messages?.[0] || 'Could not create project'
	}
}
</script>

<template>
	<Dialog :model-value="open" @update:model-value="(v) => !v && emit('close')">
		<template #body-title><h3 class="t-lg" style="font-weight: 600">New project</h3></template>
		<template #body-content>
			<div class="flex col g-3" style="padding-top: 4px">
				<div class="flex g-2">
					<div style="flex: 1">
						<FormControl v-model="name" type="text" label="Project name" placeholder="e.g. Billing v2" autofocus />
					</div>
					<div style="width: 96px">
						<FormControl v-model="key" type="text" label="Key" :maxlength="4" placeholder="BIL" style="text-transform: uppercase" @input="keyEdited = true" />
					</div>
				</div>
				<div class="flex col g-1">
					<span class="t-xs ink-5">Icon</span>
					<div class="flex wrap g-1">
						<button v-for="ic in ICONS" :key="ic" class="pjx-pick" :class="{ on: icon === ic }" @click="icon = ic">
							<Icon :name="ic" :size="16" />
						</button>
					</div>
				</div>
				<div class="flex col g-1">
					<span class="t-xs ink-5">Color</span>
					<div class="flex g-2">
						<button
							v-for="c in COLORS"
							:key="c"
							class="pjx-sw"
							:class="{ on: color === c }"
							:style="{ background: c }"
							@click="color = c"
						/>
					</div>
				</div>
				<div class="flex g-3 wrap">
					<div class="flex col g-1" style="min-width: 200px">
						<span class="t-xs ink-5">Workspace</span>
						<SelectField
							:options="workspaceOptions"
							:model-value="workspace"
							placeholder="None"
							@change="(v) => (workspace = v || '')"
						/>
					</div>
					<div class="flex col g-1" style="min-width: 200px">
						<span class="t-xs ink-5">Team</span>
						<SelectField
							:options="teamOptions"
							:model-value="team"
							placeholder="No team"
							@change="(v) => (team = v || '')"
						/>
					</div>
					<div class="flex col g-1" style="min-width: 200px">
						<span class="t-xs ink-5">Members</span>
						<SelectField v-model="members" :options="userOptions" multiple placeholder="Just me" />
					</div>
				</div>
				<div v-if="error" class="t-sm ink-red">{{ error }}</div>
			</div>
		</template>
		<template #actions>
			<div class="flex" style="gap: 8px; justify-content: flex-end; width: 100%">
				<Button variant="subtle" theme="gray" @click="emit('close')">Cancel</Button>
				<Button variant="solid" theme="blue" :loading="creator.loading" @click="submit">Create project</Button>
			</div>
		</template>
	</Dialog>
</template>

<style scoped>
.pjx-pick {
	width: 30px;
	height: 30px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 7px;
	background: var(--surface-white);
	display: grid;
	place-items: center;
	cursor: pointer;
	color: var(--ink-gray-7);
}
.pjx-pick.on {
	border-color: var(--ink-gray-9);
	background: var(--surface-gray-2);
}
.pjx-sw {
	width: 26px;
	height: 26px;
	border-radius: 9999px;
	border: 2px solid transparent;
	cursor: pointer;
}
.pjx-sw.on {
	border-color: var(--ink-gray-9);
}
</style>
