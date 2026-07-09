<script setup>
import { ref, watch, computed } from 'vue'
import { createResource, Dialog, Button, Avatar, DatePicker } from 'frappe-ui'
import Icon from './Icon.vue'
import SelectField from './SelectField.vue'
import NativeSelect from './NativeSelect.vue'
import { store, reloadBootstrap, userName } from '@/data/store'

const props = defineProps({ open: Boolean, project: { type: String, required: true } })
const emit = defineEmits(['close', 'changed', 'deleted'])

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
const memberAdd = createResource({ url: 'projex.api.add_member' })
const memberRemove = createResource({ url: 'projex.api.remove_member' })
const inviter = createResource({ url: 'projex.api.invite_user' })
const labelCreate = createResource({ url: 'projex.api.create_label' })
const labelDelete = createResource({ url: 'projex.api.delete_label' })
const cycleCreate = createResource({ url: 'projex.api.create_cycle' })
const cycleDelete = createResource({ url: 'projex.api.delete_cycle' })
const linkSaver = createResource({ url: 'projex.api.set_project_links' })
const erpOptions = createResource({ url: 'projex.api.erpnext_link_options' })
const deleter = createResource({ url: 'projex.api.delete_project' })
const archiver = createResource({ url: 'projex.api.archive_project' })
const duplicator = createResource({ url: 'projex.api.duplicate_project' })
const bulkInviter = createResource({ url: 'projex.api.bulk_invite' })
const linkLister = createResource({ url: 'projex.api.list_invite_links' })
const linkCreator = createResource({ url: 'projex.api.create_invite_link' })
const linkRevoker = createResource({ url: 'projex.api.revoke_invite_link' })

// editable copies
const gen = ref({})
const newMember = ref([])
const inviteEmail = ref('')
const bulkEmails = ref('')
const bulkResult = ref(null)
const inviteLinks = ref([])
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
watch(
	() => props.open,
	(v) => {
		if (v) {
			tab.value = 'general'
			bulkResult.value = null
			inviteLinks.value = []
			load()
		}
	},
)
watch(tab, (t) => {
	if (t === 'members' && detail.data?.project?.can_manage) loadLinks()
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
const memberIds = computed(() => (detail.data?.members || []).map((m) => m.user))
const assignableUsers = computed(() => userOptions.value.filter((u) => !memberIds.value.includes(u.value)))

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
	emit('changed')
}

async function addMembers() {
	for (const u of newMember.value) {
		await memberAdd.submit({ parent_doctype: 'Projex Project', parent: props.project, user: u, role: 'Member' })
	}
	newMember.value = []
	load()
}
async function removeMember(user) {
	await memberRemove.submit({ parent_doctype: 'Projex Project', parent: props.project, user })
	load()
}
async function invite() {
	if (!inviteEmail.value.trim()) return
	const res = await inviter.submit({ email: inviteEmail.value.trim(), project: props.project })
	await memberAdd.submit({ parent_doctype: 'Projex Project', parent: props.project, user: res.name, role: 'Member' })
	inviteEmail.value = ''
	await reloadBootstrap()
	load()
}

async function bulkInvite() {
	if (!bulkEmails.value.trim()) return
	const res = await bulkInviter.submit({ project: props.project, emails: bulkEmails.value })
	bulkResult.value = res.results || []
	bulkEmails.value = ''
	await reloadBootstrap()
	load()
}

async function loadLinks() {
	inviteLinks.value = (await linkLister.submit({ project: props.project })) || []
}
async function makeInviteLink() {
	await linkCreator.submit({ project: props.project, role: 'Member', expires_days: 7 })
	await loadLinks()
}
async function copyLink(url) {
	try {
		await navigator.clipboard.writeText(url)
		window.alert('Invite link copied to clipboard')
	} catch {
		window.prompt('Copy this invite link:', url)
	}
}
async function revokeLink(name) {
	await linkRevoker.submit({ name })
	await loadLinks()
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
}

// Footer primary action depends on the active tab; tabs that mutate inline
// (members/labels/cycles) don't need one, so the footer just shows Close there.
const primaryAction = computed(() => {
	if (!canManage.value) return null
	if (tab.value === 'general') return { label: 'Save changes', loading: updater.loading, run: saveGeneral }
	if (tab.value === 'erpnext') return { label: 'Save links', loading: linkSaver.loading, run: saveErp }
	return null
})

async function confirmDelete() {
	const label = gen.value.project_name || props.project
	const ok = window.confirm(
		`Delete project “${label}” and all of its tasks, labels and cycles?\n\nThis cannot be undone.`,
	)
	if (!ok) return
	await deleter.submit({ project: props.project })
	await reloadBootstrap()
	emit('deleted', props.project)
	emit('close')
}

const isArchived = computed(() => !!detail.data?.project?.is_archived)
async function toggleArchive() {
	const next = isArchived.value ? 0 : 1
	await archiver.submit({ project: props.project, archived: next })
	if (detail.data?.project) detail.data.project.is_archived = next
	await reloadBootstrap()
	if (next) {
		emit('deleted', props.project) // archived projects leave the sidebar; route away
		emit('close')
	}
}

async function duplicate() {
	const name = (window.prompt('Name for the duplicated project', `${gen.value.project_name || props.project} copy`) || '').trim()
	if (!name) return
	const key = (window.prompt('Key for the new project (e.g. ABC)') || '').trim().toUpperCase()
	if (!key) return
	const withIssues = window.confirm('Copy all tasks into the new project too?\n\nOK = copy tasks (as a template, reset to first status)\nCancel = structure only (labels, cycles, members)')
	const res = await duplicator.submit({
		project: props.project, new_name: name, new_key: key,
		include_issues: withIssues ? 1 : 0, reset_status: 1,
	})
	await reloadBootstrap()
	emit('changed')
	emit('close')
	window.alert(`Created “${name}” (${res.key})${res.issues_copied ? ` with ${res.issues_copied} tasks` : ''}.`)
}
</script>

<template>
	<Dialog :model-value="open" @update:model-value="(v) => !v && emit('close')" :options="{ size: '2xl' }">
		<template #body-title><h3 class="t-lg" style="font-weight: 600">Project settings · {{ project }}</h3></template>
		<template #body-content>
			<div class="tabs" style="margin-bottom: 14px">
				<div v-for="t in TABS" :key="t.id" class="tab" :class="{ active: tab === t.id }" @click="tab = t.id">
					{{ t.label }}
				</div>
			</div>

			<div v-if="!canManage" class="t-sm ink-5" style="padding: 8px 0">
				You have read-only access to this project's settings.
			</div>

			<!-- GENERAL -->
			<div v-show="tab === 'general'" class="flex col g-3">
				<label class="flex col g-1">
					<span class="t-xs ink-5">Name</span>
					<input v-model="gen.project_name" class="input" :disabled="!canManage" placeholder="Project name" />
					<span class="t-2xs ink-5">Edit the name to rename the project, then “Save changes”. The project key ({{ detail.data?.project?.key }}) is fixed.</span>
				</label>
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
			<div v-show="tab === 'members'" class="flex col g-3">
				<div v-for="m in detail.data?.members || []" :key="m.user" class="pjx-mrow">
					<Avatar :label="m.full_name" size="sm" />
					<span style="flex: 1">{{ m.full_name }}</span>
					<span class="pjx-dim t-xs">{{ m.role }}</span>
					<Button v-if="canManage" variant="ghost" theme="gray" @click="removeMember(m.user)">
						<template #icon><Icon name="x" :size="14" /></template>
					</Button>
				</div>
				<template v-if="canManage">
					<div class="flex g-2 items-end">
						<div class="flex col g-1" style="flex: 1">
							<span class="t-xs ink-5">Add existing members</span>
							<SelectField v-model="newMember" :options="assignableUsers" multiple placeholder="Pick users" />
						</div>
						<Button variant="subtle" theme="gray" :disabled="!newMember.length" @click="addMembers">Add</Button>
					</div>
					<div class="flex col g-1">
						<span class="t-xs ink-5">Invite by email — paste many (commas, spaces or new lines)</span>
						<textarea
							v-model="bulkEmails"
							class="input"
							rows="2"
							placeholder="ann@company.com, ben@company.com&#10;cara@company.com"
							style="resize: vertical; font-family: var(--font-sans)"
						/>
						<div class="flex g-2" style="justify-content: flex-end">
							<Button variant="subtle" theme="gray" :loading="bulkInviter.loading" :disabled="!bulkEmails.trim()" @click="bulkInvite">Send invites</Button>
						</div>
						<div v-if="bulkResult" class="flex col g-1" style="margin-top: 4px">
							<span v-for="r in bulkResult" :key="r.email" class="t-xs">
								<span :style="{ color: r.status === 'error' ? 'var(--ink-red-3)' : 'var(--ink-green-3)' }">●</span>
								{{ r.email }} — {{ r.status }}{{ r.message ? ': ' + r.message : '' }}
							</span>
						</div>
					</div>

					<div class="pjx-zone" style="flex-direction: column; align-items: stretch; gap: 8px">
						<div class="flex items-center g-2">
							<div class="flex col g-1" style="flex: 1">
								<span class="t-sm" style="font-weight: 600">Invite link</span>
								<span class="t-xs ink-5">Anyone with the link can join this project (expires in 7 days).</span>
							</div>
							<Button variant="subtle" theme="gray" :loading="linkCreator.loading" @click="makeInviteLink">Create link</Button>
						</div>
						<div v-for="lk in inviteLinks" :key="lk.name" class="flex items-center g-2 pjx-linkrow">
							<input class="input" :value="lk.url" readonly style="flex: 1; font-size: 12px" @focus="(e) => e.target.select()" />
							<Button variant="ghost" theme="gray" title="Copy" @click="copyLink(lk.url)">
								<template #icon><Icon name="copy" :size="14" /></template>
							</Button>
							<Button variant="ghost" theme="gray" title="Revoke" @click="revokeLink(lk.name)">
								<template #icon><Icon name="trash-2" :size="14" /></template>
							</Button>
						</div>
					</div>
				</template>
			</div>

			<!-- LABELS -->
			<div v-show="tab === 'labels'" class="flex col g-3">
				<div class="flex wrap g-2">
					<span v-for="l in detail.data?.labels || []" :key="l.name" class="pjx-label">
						<span class="pjx-label__dot" :style="{ background: l.color }" />
						{{ l.label_name }}
						<button v-if="canManage" class="pjx-chip__x" @click="removeLabel(l.name)"><Icon name="x" :size="11" /></button>
					</span>
					<span v-if="!(detail.data?.labels || []).length" class="pjx-dim t-xs">No project labels yet.</span>
				</div>
				<div v-if="canManage" class="flex g-2 items-end">
					<label class="flex col g-1" style="flex: 1">
						<span class="t-xs ink-5">New label</span>
						<input v-model="newLabel.name" class="input" placeholder="e.g. frontend" />
					</label>
					<div class="flex g-1">
						<button v-for="c in COLORS" :key="c" class="pjx-sw sm" :class="{ on: newLabel.color === c }" :style="{ background: c }" @click="newLabel.color = c" />
					</div>
					<Button variant="subtle" theme="gray" @click="addLabel">Add</Button>
				</div>
			</div>

			<!-- CYCLES -->
			<div v-show="tab === 'cycles'" class="flex col g-3">
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
						<input v-model="newCycle.name" class="input" placeholder="Cycle name" style="flex: 1" />
						<DatePicker v-model="newCycle.start" placeholder="Start date" />
						<DatePicker v-model="newCycle.end" placeholder="End date" />
					</div>
					<div><Button variant="subtle" theme="gray" @click="addCycle">Add cycle</Button></div>
				</div>
			</div>

			<!-- ERPNEXT -->
			<div v-show="tab === 'erpnext'" class="flex col g-3">
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
		</template>
		<template #actions>
			<div class="flex items-center" style="width: 100%; gap: 8px">
				<span style="flex: 1" />
				<Button variant="subtle" theme="gray" @click="emit('close')">Close</Button>
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
		</template>
	</Dialog>
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
