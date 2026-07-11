<script setup>
import { ref, watch, computed } from 'vue'
import { createResource, Button, FormControl, SettingsHeader, SettingsBody } from 'frappe-ui'
import SelectField from '../SelectField.vue'
import { PROJECT_COLORS } from './projectColors'
import { store, reloadBootstrap } from '@/data/store'
import { bumpRefresh } from '@/data/ui'
import { notify, notifyError, confirm, promptText } from '@/utils/feedback'

const props = defineProps({
	project: { type: String, required: true },
	data: { type: Object, required: true }, // get_project_detail payload
})
// `deleted` fires when the project leaves the sidebar (deleted or archived).
const emit = defineEmits(['reload', 'deleted'])

const updater = createResource({ url: 'projex.api.update_project' })
const deleter = createResource({ url: 'projex.api.delete_project' })
const archiver = createResource({ url: 'projex.api.archive_project' })
const duplicator = createResource({ url: 'projex.api.duplicate_project' })

const STATUS = ['Active', 'Planning', 'On hold', 'Completed']

const gen = ref({})
watch(
	() => props.data,
	(d) => {
		if (d?.project) gen.value = { ...d.project }
	},
	{ immediate: true },
)

const canManage = computed(() => props.data?.project?.can_manage)
const isArchived = computed(() => !!props.data?.project?.is_archived)
const teamOptions = computed(() => {
	const ws = props.data?.project?.workspace
	return [
		{ value: '', label: 'No team' },
		...store.teams.filter((t) => !ws || t.workspace === ws).map((t) => ({ value: t.name, label: t.team_name })),
	]
})
const userOptions = computed(() => store.users.map((u) => ({ value: u.name, label: u.full_name || u.name })))

async function save() {
	await updater.submit({
		project: props.project,
		fields: JSON.stringify({
			project_name: gen.value.project_name,
			icon: gen.value.icon,
			color: gen.value.color,
			status: gen.value.status,
			lead: gen.value.lead,
			team: gen.value.team || null,
		}),
	})
	await reloadBootstrap()
	bumpRefresh()
	emit('reload')
	notify.success('Project settings saved')
}

async function confirmDelete() {
	const label = gen.value.project_name || props.project
	const ok = await confirm({
		title: `Delete project “${label}”`,
		message: 'All of its tasks, labels and cycles will be permanently deleted. This cannot be undone.',
		confirmLabel: 'Delete project',
		theme: 'red',
	})
	if (!ok) return
	try {
		await deleter.submit({ project: props.project })
		await reloadBootstrap()
		notify.success(`Project “${label}” deleted`)
		emit('deleted', props.project)
	} catch (e) {
		notifyError(e, 'Could not delete project')
	}
}

async function toggleArchive() {
	const next = isArchived.value ? 0 : 1
	await archiver.submit({ project: props.project, archived: next })
	await reloadBootstrap()
	if (next) emit('deleted', props.project) // archived projects leave the sidebar
	else emit('reload')
}

async function duplicate() {
	const name = await promptText({
		title: 'Duplicate project',
		label: 'New project name',
		value: `${gen.value.project_name || props.project} copy`,
		confirmLabel: 'Next',
	})
	if (!name) return
	const key = (
		await promptText({
			title: 'Duplicate project',
			label: 'Key for the new project',
			placeholder: 'e.g. ABC',
			confirmLabel: 'Next',
		})
	)?.toUpperCase()
	if (!key) return
	const withIssues = await confirm({
		title: 'Copy tasks too?',
		message: 'Copy all tasks into the new project as a template (reset to the first status)? Choose Cancel to copy structure only — labels, cycles and members.',
		confirmLabel: 'Copy tasks',
		cancelLabel: 'Structure only',
	})
	try {
		const res = await duplicator.submit({
			project: props.project, new_name: name, new_key: key,
			include_issues: withIssues ? 1 : 0, reset_status: 1,
		})
		await reloadBootstrap()
		bumpRefresh()
		notify.success(`Created “${name}” (${res.key})${res.issues_copied ? ` with ${res.issues_copied} tasks` : ''}`)
	} catch (e) {
		notifyError(e, 'Could not duplicate project')
	}
}
</script>

<template>
	<SettingsHeader title="General" :description="`${data.project?.project_name || project} · ${data.project?.key || project}`">
		<template #actions>
			<Button v-if="canManage" variant="solid" theme="gray" :loading="updater.loading" @click="save">Save changes</Button>
		</template>
	</SettingsHeader>
	<SettingsBody>
		<div class="flex col g-3" style="padding-top: 8px">
			<div v-if="!canManage" class="t-sm ink-5">You have read-only access to this project's settings.</div>
			<div class="flex col g-1">
				<span class="t-xs ink-5">Name</span>
				<FormControl v-model="gen.project_name" type="text" :disabled="!canManage" placeholder="Project name" />
				<span class="t-2xs ink-5">Edit the name to rename the project, then “Save changes”. The project key ({{ data.project?.key }}) is fixed.</span>
			</div>
			<div class="flex col g-1">
				<span class="t-xs ink-5">Status</span>
				<SelectField
					:options="STATUS.map((s) => ({ value: s, label: s }))"
					:model-value="gen.status"
					@change="(v) => (gen.status = v)"
				/>
			</div>
			<div class="flex col g-1">
				<span class="t-xs ink-5">Lead</span>
				<SelectField :options="userOptions" :model-value="gen.lead" @change="(v) => (gen.lead = v)" />
			</div>
			<div class="flex col g-1">
				<span class="t-xs ink-5">Team</span>
				<SelectField :options="teamOptions" :model-value="gen.team || ''" placeholder="No team" @change="(v) => (gen.team = v || null)" />
			</div>
			<div class="flex col g-1">
				<span class="t-xs ink-5">Color</span>
				<div class="flex g-2">
					<button v-for="c in PROJECT_COLORS" :key="c" class="pjx-sw" :class="{ on: gen.color === c }" :style="{ background: c }" @click="gen.color = c" />
				</div>
			</div>

			<div v-if="canManage" class="pjx-zone">
				<div class="flex col g-1" style="flex: 1">
					<span class="t-sm" style="font-weight: 600">Duplicate project</span>
					<span class="t-xs ink-5">Create a copy — as a reusable template, with or without its tasks.</span>
				</div>
				<Button variant="subtle" theme="gray" :loading="duplicator.loading" @click="duplicate">Duplicate…</Button>
			</div>

			<div v-if="canManage" class="pjx-zone">
				<div class="flex col g-1" style="flex: 1">
					<span class="t-sm" style="font-weight: 600">{{ isArchived ? 'Unarchive project' : 'Archive project' }}</span>
					<span class="t-xs ink-5">{{ isArchived ? 'Restore this project to the sidebar.' : 'Hide from the sidebar without deleting anything. Reversible.' }}</span>
				</div>
				<Button variant="subtle" theme="gray" :loading="archiver.loading" @click="toggleArchive">{{ isArchived ? 'Unarchive' : 'Archive' }}</Button>
			</div>

			<div v-if="canManage" class="pjx-danger">
				<div class="flex col g-1" style="flex: 1">
					<span class="t-sm" style="font-weight: 600; color: var(--ink-red-3)">Delete project</span>
					<span class="t-xs ink-5">Permanently removes this project and all of its tasks. This can't be undone.</span>
				</div>
				<Button theme="red" variant="subtle" :loading="deleter.loading" @click="confirmDelete">Delete project…</Button>
			</div>
		</div>
	</SettingsBody>
</template>

<style scoped>
.pjx-sw {
	width: 24px;
	height: 24px;
	border-radius: 9999px;
	border: 2px solid transparent;
	cursor: pointer;
}
.pjx-sw.on {
	border-color: var(--ink-gray-9);
}
.pjx-danger {
	display: flex;
	align-items: center;
	gap: 12px;
	margin-top: 8px;
	padding: 12px;
	border: 1px solid var(--outline-red-1, var(--outline-gray-2));
	border-radius: 8px;
	background: var(--surface-red-1, var(--surface-gray-1));
}
.pjx-zone {
	display: flex;
	align-items: center;
	gap: 12px;
	margin-top: 8px;
	padding: 12px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 8px;
	background: var(--surface-gray-1);
}
</style>
