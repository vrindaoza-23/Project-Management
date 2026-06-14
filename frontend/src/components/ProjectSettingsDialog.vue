<script setup>
import { ref, watch, computed } from 'vue'
import { createResource, Dialog, Button, Avatar } from 'frappe-ui'
import Icon from './Icon.vue'
import SelectField from './SelectField.vue'
import { store, reloadBootstrap, userName } from '@/data/store'

const props = defineProps({ open: Boolean, project: { type: String, required: true } })
const emit = defineEmits(['close', 'changed'])

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

// editable copies
const gen = ref({})
const newMember = ref([])
const inviteEmail = ref('')
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
			load()
		}
	},
)

const canManage = computed(() => detail.data?.project?.can_manage)
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
					<input v-model="gen.project_name" class="input" :disabled="!canManage" />
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
					<span class="t-xs ink-5">Color</span>
					<div class="flex g-2">
						<button v-for="c in COLORS" :key="c" class="pjx-sw" :class="{ on: gen.color === c }" :style="{ background: c }" @click="gen.color = c" />
					</div>
				</div>
				<div v-if="canManage"><Button variant="solid" theme="gray" :loading="updater.loading" @click="saveGeneral">Save</Button></div>
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
					<div class="flex g-2 items-end">
						<label class="flex col g-1" style="flex: 1">
							<span class="t-xs ink-5">Invite by email</span>
							<input v-model="inviteEmail" class="input" placeholder="teammate@company.com" />
						</label>
						<Button variant="subtle" theme="gray" :loading="inviter.loading" @click="invite">Invite</Button>
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
						<input v-model="newCycle.start" type="date" class="input" />
						<input v-model="newCycle.end" type="date" class="input" />
					</div>
					<div><Button variant="subtle" theme="gray" @click="addCycle">Add cycle</Button></div>
				</div>
			</div>

			<!-- ERPNEXT -->
			<div v-show="tab === 'erpnext'" class="flex col g-3">
				<p class="t-sm ink-5">Link to ERPNext for the timesheet/billing wedge.</p>
				<label class="flex col g-1">
					<span class="t-xs ink-5">ERPNext Customer</span>
					<input v-model="erp.customer" class="input" :disabled="!canManage" placeholder="Customer name" />
				</label>
				<label class="flex col g-1">
					<span class="t-xs ink-5">ERPNext Project</span>
					<input v-model="erp.project" class="input" :disabled="!canManage" placeholder="Project name" />
				</label>
				<div v-if="canManage"><Button variant="solid" theme="gray" :loading="linkSaver.loading" @click="saveErp">Save links</Button></div>
			</div>
		</template>
		<template #actions>
			<Button variant="subtle" theme="gray" @click="emit('close')">Done</Button>
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
</style>
