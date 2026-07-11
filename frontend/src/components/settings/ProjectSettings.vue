<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import {
	createResource,
	Button,
	DatePicker,
	FormControl,
	TabButtons,
	SettingsHeader,
	SettingsBody,
} from 'frappe-ui'
import Icon from '../Icon.vue'
import SelectField from '../SelectField.vue'
import NativeSelect from '../NativeSelect.vue'
import ProjectMembersSettings from './ProjectMembersSettings.vue'
import { store, reloadBootstrap } from '@/data/store'
import { bumpRefresh } from '@/data/ui'
import { notify, notifyError, confirm, promptText } from '@/utils/feedback'

const props = defineProps({ project: { type: String, required: true } })
// `deleted` fires when the project leaves the sidebar (deleted or archived) so
// the settings dialog can drop this panel and route away if it's on screen.
const emit = defineEmits(['deleted'])

const tab = ref('general')
const TABS = [
	{ id: 'general', label: 'General' },
	{ id: 'members', label: 'Members' },
	{ id: 'labels', label: 'Labels' },
	{ id: 'cycles', label: 'Cycles' },
	{ id: 'erpnext', label: 'ERPNext' },
]

const detail = createResource({ url: 'projex.api.get_project_detail' })
const updater = createResource({ url: 'projex.api.update_project' })
const labelCreate = createResource({ url: 'projex.api.create_label' })
const labelDelete = createResource({ url: 'projex.api.delete_label' })
const cycleCreate = createResource({ url: 'projex.api.create_cycle' })
const cycleDelete = createResource({ url: 'projex.api.delete_cycle' })
const linkSaver = createResource({ url: 'projex.api.set_project_links' })
const erpOptions = createResource({ url: 'projex.api.erpnext_link_options' })
const deleter = createResource({ url: 'projex.api.delete_project' })
const archiver = createResource({ url: 'projex.api.archive_project' })
const duplicator = createResource({ url: 'projex.api.duplicate_project' })

// editable copies
const gen = ref({})
const newLabel = ref({ name: '', color: 'var(--blue-500)' })
const newCycle = ref({ name: '', start: '', end: '', state: 'Upcoming' })
const erp = ref({ customer: '', project: '' })

const STATUS = ['Active', 'Planning', 'On hold', 'Completed']
const COLORS = ['var(--blue-500)', 'var(--violet-500)', 'var(--green-600)', 'var(--orange-500)', 'var(--teal-600)', 'var(--red-500)', 'var(--amber-500)']

function load() {
	detail.submit({ project: props.project }).then((d) => {
		gen.value = { ...d.project }
		erp.value = { customer: d.project.erpnext_customer || '', project: d.project.erpnext_project || '' }
	})
}
onMounted(load)
watch(tab, (t) => {
	if (t === 'erpnext' && detail.data?.project?.can_manage && !erpOptions.data) {
		erpOptions.submit({ project: props.project })
	}
})

const canManage = computed(() => detail.data?.project?.can_manage)
const erpInstalled = computed(() => erpOptions.data?.erpnext !== false)
const erpProjectOptions = computed(() => [{ value: '', label: '— None —' }, ...(erpOptions.data?.projects || [])])
const erpCustomerOptions = computed(() => [{ value: '', label: '— None —' }, ...(erpOptions.data?.customers || [])])
const teamOptions = computed(() => {
	const ws = detail.data?.project?.workspace
	return [
		{ value: '', label: 'No team' },
		...store.teams.filter((t) => !ws || t.workspace === ws).map((t) => ({ value: t.name, label: t.team_name })),
	]
})
const userOptions = computed(() => store.users.map((u) => ({ value: u.name, label: u.full_name || u.name })))

async function saveGeneral() {
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
	notify.success('Project settings saved')
}

async function addLabel() {
	if (!newLabel.value.name.trim()) return
	await labelCreate.submit({ project: props.project, label_name: newLabel.value.name.trim(), color: newLabel.value.color })
	newLabel.value = { name: '', color: 'var(--blue-500)' }
	load()
}
async function removeLabel(name) {
	await labelDelete.submit({ name })
	load()
}

async function addCycle() {
	if (!newCycle.value.name.trim()) return
	await cycleCreate.submit({
		project: props.project,
		cycle_name: newCycle.value.name.trim(),
		start_date: newCycle.value.start || null,
		end_date: newCycle.value.end || null,
		state: newCycle.value.state,
	})
	newCycle.value = { name: '', start: '', end: '', state: 'Upcoming' }
	load()
}
async function removeCycle(name) {
	await cycleDelete.submit({ name })
	load()
}

async function saveErp() {
	await linkSaver.submit({
		project: props.project,
		erpnext_customer: erp.value.customer || null,
		erpnext_project: erp.value.project || null,
	})
	notify.success('ERPNext links saved')
}

// Header primary action depends on the active tab; tabs that mutate inline
// (members/labels/cycles) don't need one.
const primaryAction = computed(() => {
	if (!canManage.value) return null
	if (tab.value === 'general') return { label: 'Save changes', loading: updater.loading, run: saveGeneral }
	if (tab.value === 'erpnext') return { label: 'Save links', loading: linkSaver.loading, run: saveErp }
	return null
})

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

const isArchived = computed(() => !!detail.data?.project?.is_archived)
async function toggleArchive() {
	const next = isArchived.value ? 0 : 1
	await archiver.submit({ project: props.project, archived: next })
	if (detail.data?.project) detail.data.project.is_archived = next
	await reloadBootstrap()
	if (next) emit('deleted', props.project) // archived projects leave the sidebar; route away
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
	<SettingsHeader>
		<div class="flex items-start justify-between gap-4">
			<div class="flex min-w-0 flex-col gap-1">
				<h2 class="text-lg font-semibold text-ink-gray-8">
					{{ detail.data?.project?.project_name || project }}
				</h2>
				<p class="text-base text-ink-gray-6">Project settings · {{ project }}</p>
			</div>
			<Button
				v-if="primaryAction"
				variant="solid"
				theme="gray"
				:loading="primaryAction.loading"
				@click="primaryAction.run"
			>
				{{ primaryAction.label }}
			</Button>
		</div>
		<div style="margin-top: 14px">
			<TabButtons v-model="tab" :options="TABS.map((t) => ({ label: t.label, value: t.id }))" />
		</div>
	</SettingsHeader>
	<SettingsBody>
		<div v-if="!canManage" class="t-sm ink-5" style="padding: 8px 0">
			You have read-only access to this project's settings.
		</div>

		<!-- GENERAL -->
		<div v-show="tab === 'general'" class="flex col g-3" style="padding-top: 8px">
			<div class="flex col g-1">
				<span class="t-xs ink-5">Name</span>
				<FormControl v-model="gen.project_name" type="text" :disabled="!canManage" placeholder="Project name" />
				<span class="t-2xs ink-5">Edit the name to rename the project, then “Save changes”. The project key ({{ detail.data?.project?.key }}) is fixed.</span>
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
					<button v-for="c in COLORS" :key="c" class="pjx-sw" :class="{ on: gen.color === c }" :style="{ background: c }" @click="gen.color = c" />
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

		<!-- MEMBERS -->
		<ProjectMembersSettings
			v-if="tab === 'members' && detail.data"
			style="padding-top: 8px"
			:project="project"
			:members="detail.data?.members || []"
			:can-manage="canManage"
			@changed="load"
		/>

		<!-- LABELS -->
		<div v-show="tab === 'labels'" class="flex col g-3" style="padding-top: 8px">
			<div class="flex wrap g-2">
				<span v-for="l in detail.data?.labels || []" :key="l.name" class="pjx-label">
					<span class="pjx-label__dot" :style="{ background: l.color }" />
					{{ l.label_name }}
					<button v-if="canManage" class="pjx-chip__x" @click="removeLabel(l.name)"><Icon name="x" :size="11" /></button>
				</span>
				<span v-if="!(detail.data?.labels || []).length" class="pjx-dim t-xs">No project labels yet.</span>
			</div>
			<div v-if="canManage" class="flex g-2 items-end">
				<div class="flex col g-1" style="flex: 1">
					<span class="t-xs ink-5">New label</span>
					<FormControl v-model="newLabel.name" type="text" placeholder="e.g. frontend" />
				</div>
				<div class="flex g-1">
					<button v-for="c in COLORS" :key="c" class="pjx-sw sm" :class="{ on: newLabel.color === c }" :style="{ background: c }" @click="newLabel.color = c" />
				</div>
				<Button variant="subtle" theme="gray" @click="addLabel">Add</Button>
			</div>
		</div>

		<!-- CYCLES -->
		<div v-show="tab === 'cycles'" class="flex col g-3" style="padding-top: 8px">
			<div v-for="c in detail.data?.cycles || []" :key="c.name" class="pjx-mrow">
				<Icon name="calendar-range" :size="15" class="ink-5" />
				<span style="flex: 1">{{ c.cycle_name }}</span>
				<span class="pjx-dim t-xs">{{ c.state }}</span>
				<Button v-if="canManage" variant="ghost" theme="gray" @click="removeCycle(c.name)">
					<template #icon><Icon name="x" :size="14" /></template>
				</Button>
			</div>
			<div v-if="canManage" class="flex col g-2">
				<div class="flex g-2">
					<FormControl v-model="newCycle.name" type="text" placeholder="Cycle name" style="flex: 1" />
					<DatePicker v-model="newCycle.start" placeholder="Start date" />
					<DatePicker v-model="newCycle.end" placeholder="End date" />
				</div>
				<div><Button variant="subtle" theme="gray" @click="addCycle">Add cycle</Button></div>
			</div>
		</div>

		<!-- ERPNEXT -->
		<div v-show="tab === 'erpnext'" class="flex col g-3" style="padding-top: 8px">
			<template v-if="erpInstalled">
				<p class="t-sm ink-5">Link an ERPNext Project to roll up cost, revenue and gross margin into the Finance tab, and to log billable time.</p>
				<label class="flex col g-1">
					<span class="t-xs ink-5">ERPNext Project</span>
					<NativeSelect v-model="erp.project" :options="erpProjectOptions" placeholder="Select an ERPNext Project" />
				</label>
				<label class="flex col g-1">
					<span class="t-xs ink-5">ERPNext Customer <span class="ink-4">(optional)</span></span>
					<NativeSelect v-model="erp.customer" :options="erpCustomerOptions" placeholder="Select a Customer" />
				</label>
				<p v-if="!canManage" class="t-xs ink-4">Only a project admin can change these links.</p>
			</template>
			<p v-else class="t-sm ink-5">ERPNext is not installed, so project accounting and billable timesheets are unavailable. The flow-time metrics on the Timesheets tab work without it.</p>
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
.pjx-sw {
	width: 24px;
	height: 24px;
	border-radius: 9999px;
	border: 2px solid transparent;
	cursor: pointer;
}
.pjx-sw.sm {
	width: 20px;
	height: 20px;
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
