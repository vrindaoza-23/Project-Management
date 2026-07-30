<script setup>
import { ref, computed, watch } from 'vue'
import { createResource, Avatar, Button, Checkbox, SettingsHeader, SettingsBody } from 'frappe-ui'
import Icon from '../Icon.vue'
import SelectField from '../SelectField.vue'
import NativeSelect from '../NativeSelect.vue'
import { confirm, notify, notifyError } from '@/utils/feedback'

// Access management, organised by person (the transpose of Project → Members):
// pick someone, see and set every project they belong to at once. Built for
// onboarding — grant a new hire access to several projects in one place.
const props = defineProps({
	// Optional user to preselect (e.g. the "Manage access" deep-link from People).
	user: { type: String, default: '' },
})

const ROLES = [
	{ value: 'Admin', label: 'Admin' },
	{ value: 'Member', label: 'Member' },
	{ value: 'Guest', label: 'Guest' },
]

const overview = createResource({ url: 'projex.api.get_users_overview', auto: true })
const detail = createResource({ url: 'projex.api.get_user_detail' })
const roleUpdate = createResource({ url: 'projex.api.update_member_role' })
const allAccess = createResource({ url: 'projex.api.set_all_access' })
const memberAdd = createResource({ url: 'projex.api.add_member' })
const memberRemove = createResource({ url: 'projex.api.remove_member' })

const selected = ref('')
const newProjects = ref([])
const newRole = ref('Member')

const users = computed(() => overview.data?.users || [])
const userOptions = computed(() =>
	users.value.map((u) => ({ value: u.user, label: u.full_name || u.user })),
)
const canGrantAllAccess = computed(() => overview.data?.can_grant_all_access)
const currentRow = computed(() => users.value.find((u) => u.user === selected.value))
const current = computed(() => detail.data)

function selectUser(user) {
	if (!user) return
	selected.value = user
	newProjects.value = []
	detail.submit({ user })
}

// Preselect the deep-linked user, else the first once the roster loads.
watch(
	() => [users.value, props.user],
	() => {
		if (selected.value) return
		if (props.user && users.value.some((u) => u.user === props.user)) selectUser(props.user)
		else if (users.value.length) selectUser(users.value[0].user)
	},
	{ immediate: true },
)

async function changeRole(p, role) {
	if (!role || role === p.role) return
	await roleUpdate.submit({ parent_doctype: 'Projex Project', parent: p.project, user: selected.value, role })
	detail.reload()
}
async function toggleAllAccess(enabled) {
	await allAccess.submit({ user: selected.value, enabled: enabled ? 1 : 0 })
	overview.reload()
	detail.reload()
}
async function allocate() {
	for (const proj of newProjects.value) {
		await memberAdd.submit({ parent_doctype: 'Projex Project', parent: proj, user: selected.value, role: newRole.value })
	}
	newProjects.value = []
	newRole.value = 'Member'
	detail.reload()
	overview.reload()
}
async function deallocate(p) {
	const ok = await confirm({
		title: 'Remove from project',
		message: `Remove ${current.value.full_name} from ${p.project_name}?`,
		confirmLabel: 'Remove',
		theme: 'red',
	})
	if (!ok) return
	try {
		await memberRemove.submit({ parent_doctype: 'Projex Project', parent: p.project, user: selected.value })
		detail.reload()
		overview.reload()
		notify.success(`Removed ${current.value.full_name} from ${p.project_name}`)
	} catch (e) {
		notifyError(e, 'Could not remove member')
	}
}
</script>

<template>
	<SettingsHeader title="People access" description="Manage which projects each person belongs to" />
	<SettingsBody>
		<div class="flex col g-3" style="padding-top: 8px">
			<!-- Person switcher -->
			<div class="flex col g-1">
				<span class="t-xs ink-5">Person</span>
				<SelectField :model-value="selected" :options="userOptions" placeholder="Select a person" @change="selectUser" />
			</div>

			<template v-if="current">
				<!-- All-projects grant -->
				<label v-if="canGrantAllAccess" class="pjx-allrow">
					<Checkbox
						:model-value="!!currentRow?.is_all_access"
						@update:model-value="toggleAllAccess"
					/>
					<span class="flex col g-1">
						<span class="pjx-allrow__t">All projects</span>
						<span class="t-xs ink-4">Grants visibility into every project in the workspace.</span>
					</span>
				</label>

				<!-- Per-project allocation -->
				<div class="flex col g-1">
					<span class="t-xs ink-5">Projects</span>
					<div v-for="p in current.projects" :key="p.project" class="pjx-mrow">
						<span class="pjx-id">{{ p.key }}</span>
						<span style="flex: 1">{{ p.project_name }}</span>
						<NativeSelect
							v-if="p.can_manage && p.role !== 'Lead'"
							class="pjx-rolesel"
							:options="ROLES"
							:model-value="p.role"
							@change="(v) => changeRole(p, v)"
						/>
						<span v-else class="pjx-dim t-xs">{{ p.role }}</span>
						<Button
							v-if="p.can_manage && p.role !== 'Lead'"
							variant="ghost"
							theme="gray"
							title="Remove from project"
							@click="deallocate(p)"
						>
							<template #icon><Icon name="x" :size="14" /></template>
						</Button>
					</div>
					<div v-if="!current.projects.length" class="t-sm ink-5" style="padding: 4px 0">
						Not allocated to any project.
					</div>
				</div>

				<!-- Allocate to more projects -->
				<div v-if="current.allocatable.length" class="flex g-2 items-end">
					<div class="flex col g-1" style="flex: 1">
						<span class="t-xs ink-5">Allocate to projects</span>
						<SelectField v-model="newProjects" :options="current.allocatable" multiple placeholder="Pick projects" />
					</div>
					<div class="flex col g-1" style="width: 120px">
						<span class="t-xs ink-5">Role</span>
						<NativeSelect v-model="newRole" :options="ROLES" />
					</div>
					<Button variant="subtle" theme="gray" :loading="memberAdd.loading" :disabled="!newProjects.length" @click="allocate">
						Add
					</Button>
				</div>
			</template>

			<span class="t-xs ink-4">People need at least Member access to see a project's issues and boards.</span>
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
.pjx-rolesel {
	width: 120px;
}
.pjx-allrow {
	display: flex;
	align-items: flex-start;
	gap: 10px;
	padding: 10px 0;
	border-block: 1px solid var(--outline-gray-1);
	cursor: pointer;
}
.pjx-allrow__t {
	font-size: 13px;
	font-weight: 500;
	color: var(--ink-gray-8);
}
.pjx-id {
	font-variant-numeric: tabular-nums;
	font-size: 12px;
	color: var(--ink-gray-5);
}
.pjx-dim {
	color: var(--ink-gray-5);
}
</style>
