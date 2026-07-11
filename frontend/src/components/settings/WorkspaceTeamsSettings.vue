<script setup>
import { ref, computed } from 'vue'
import { createResource, Button, FormControl, SettingsHeader, SettingsBody } from 'frappe-ui'
import Icon from '../Icon.vue'
import { reloadBootstrap } from '@/data/store'
import { notify, notifyError, confirm, promptText } from '@/utils/feedback'

const props = defineProps({
	workspace: { type: String, required: true },
	data: { type: Object, required: true }, // get_workspace_detail payload
})
const emit = defineEmits(['reload'])

const teamCreate = createResource({ url: 'projex.api.create_team' })
const teamUpdate = createResource({ url: 'projex.api.update_team' })
const teamDelete = createResource({ url: 'projex.api.delete_team' })

const newTeam = ref('')
const canManage = computed(() => props.data?.workspace?.can_manage)
const teams = computed(() => props.data?.teams || [])

async function reloadAll() {
	await reloadBootstrap() // teams drive the sidebar grouping too
	emit('reload')
}

async function addTeam() {
	if (!newTeam.value.trim()) return
	try {
		await teamCreate.submit({ workspace: props.workspace, team_name: newTeam.value.trim() })
		newTeam.value = ''
		await reloadAll()
	} catch (e) {
		notifyError(e, 'Could not create team')
	}
}
async function renameTeam(t) {
	const name = await promptText({
		title: 'Rename team',
		label: 'Team name',
		value: t.team_name,
		confirmLabel: 'Save',
	})
	if (!name || name === t.team_name) return
	await teamUpdate.submit({ team: t.name, fields: JSON.stringify({ team_name: name }) })
	await reloadAll()
}
async function removeTeam(t) {
	const ok = await confirm({
		title: `Delete team “${t.team_name}”`,
		message: 'Its projects are kept — they just become ungrouped.',
		confirmLabel: 'Delete team',
		theme: 'red',
	})
	if (!ok) return
	await teamDelete.submit({ team: t.name })
	await reloadAll()
	notify.success(`Team “${t.team_name}” deleted`)
}
</script>

<template>
	<SettingsHeader title="Teams" :description="data.workspace?.workspace_name || workspace" />
	<SettingsBody>
		<div class="flex col g-3" style="padding-top: 8px">
			<div v-if="!canManage" class="t-sm ink-5">You have read-only access to this workspace's teams.</div>
			<p class="t-sm ink-5">Teams group projects inside this workspace. A project can belong to one team, or none.</p>
			<div v-for="t in teams" :key="t.name" class="pjx-mrow">
				<Icon :name="t.icon || 'users'" :size="15" class="ink-5" />
				<span style="flex: 1">{{ t.team_name }}</span>
				<template v-if="canManage">
					<Button variant="ghost" theme="gray" title="Rename" @click="renameTeam(t)">
						<template #icon><Icon name="pencil" :size="14" /></template>
					</Button>
					<Button variant="ghost" theme="gray" title="Delete" @click="removeTeam(t)">
						<template #icon><Icon name="trash-2" :size="14" /></template>
					</Button>
				</template>
			</div>
			<span v-if="!teams.length" class="pjx-dim t-xs">No teams yet.</span>
			<div v-if="canManage" class="flex g-2 items-end">
				<div class="flex col g-1" style="flex: 1">
					<span class="t-xs ink-5">New team</span>
					<FormControl v-model="newTeam" type="text" placeholder="e.g. Platform" @keyup.enter="addTeam" />
				</div>
				<Button variant="subtle" theme="gray" :loading="teamCreate.loading" :disabled="!newTeam.trim()" @click="addTeam">Add team</Button>
			</div>
		</div>
	</SettingsBody>
</template>

<style scoped>
.pjx-mrow {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 6px 0;
	border-bottom: 1px solid var(--outline-gray-1);
	font-size: 13px;
	color: var(--ink-gray-8);
}
</style>
