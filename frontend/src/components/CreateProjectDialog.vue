<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { createResource, call, Dialog, Button, FormControl } from 'frappe-ui'
import Icon from './Icon.vue'
import SelectField from './SelectField.vue'
import { store, reloadBootstrap } from '@/data/store'
import { notify } from '@/utils/feedback'

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
const template = ref('')
const startDate = ref(new Date().toISOString().slice(0, 10))
const error = ref('')
const keyEdited = ref(false)

const creator = createResource({ url: 'projex.api.create_project' })
const templates = createResource({ url: 'projex.project_templates.list_templates', auto: true })
const templateOptions = computed(() => [
	{ value: '', label: 'None — start blank' },
	...(templates.data || []).map((t) => ({ value: t.name, label: t.template_name })),
])

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
			template.value = ''
			startDate.value = new Date().toISOString().slice(0, 10)
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
		// Optionally lay out a delivery plan from a template before we navigate.
		if (template.value) {
			try {
				const r = await call('projex.project_templates.instantiate_template', {
					template: template.value,
					project: res.key,
					start_date: startDate.value,
				})
				const c = r.created
				notify.success(`Project created — added ${c.phases} phases, ${c.tasks} tasks, ${c.milestones} milestones`)
			} catch (e) {
				// Project exists; only the template step failed. Land in it and tell them.
				notify.warning('Project created, but the template could not be applied.')
			}
		}
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
				<div class="flex g-3 wrap">
					<div class="flex col g-1" style="min-width: 200px; flex: 1">
						<span class="t-xs ink-5">Delivery template</span>
						<SelectField
							:options="templateOptions"
							:model-value="template"
							placeholder="None — start blank"
							@change="(v) => (template = v || '')"
						/>
					</div>
					<div v-if="template" class="flex col g-1" style="min-width: 200px">
						<FormControl v-model="startDate" type="date" label="Start date" />
					</div>
				</div>
				<div v-if="template" class="t-xs ink-5">
					Phases, tasks and milestones from the template are created and dated from the start date.
				</div>
				<div v-if="error" class="t-sm ink-red">{{ error }}</div>
			</div>
		</template>
		<template #actions>
			<div class="flex" style="gap: 8px; justify-content: flex-end; width: 100%">
				<Button variant="subtle" theme="gray" @click="emit('close')">Cancel</Button>
				<Button variant="solid" theme="gray" :loading="creator.loading" @click="submit">Create project</Button>
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
