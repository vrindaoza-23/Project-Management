<script setup>
import { ref, computed } from 'vue'
import { createResource, Avatar, Button, SettingsHeader, SettingsBody } from 'frappe-ui'
import Icon from '../Icon.vue'
import SelectField from '../SelectField.vue'
import NativeSelect from '../NativeSelect.vue'
import { store } from '@/data/store'

const props = defineProps({
	workspace: { type: String, required: true },
	data: { type: Object, required: true }, // get_workspace_detail payload
})
const emit = defineEmits(['reload'])

const memberAdd = createResource({ url: 'projex.api.add_member' })
const memberRemove = createResource({ url: 'projex.api.remove_member' })
const roleUpdate = createResource({ url: 'projex.api.update_member_role' })

const ROLES = [
	{ value: 'Admin', label: 'Admin' },
	{ value: 'Member', label: 'Member' },
	{ value: 'Guest', label: 'Guest' },
]
const newMembers = ref([])

const canManage = computed(() => props.data?.workspace?.can_manage)
const members = computed(() => props.data?.members || [])
const memberIds = computed(() => members.value.map((m) => m.user))
const assignableUsers = computed(() =>
	store.users
		.map((u) => ({ value: u.name, label: u.full_name || u.name }))
		.filter((u) => !memberIds.value.includes(u.value)),
)

async function addMembers() {
	for (const u of newMembers.value) {
		await memberAdd.submit({ parent_doctype: 'Projex Workspace', parent: props.workspace, user: u, role: 'Member' })
	}
	newMembers.value = []
	emit('reload')
}
async function removeMember(user) {
	await memberRemove.submit({ parent_doctype: 'Projex Workspace', parent: props.workspace, user })
	emit('reload')
}
async function changeRole(user, role) {
	await roleUpdate.submit({ parent_doctype: 'Projex Workspace', parent: props.workspace, user, role })
	emit('reload')
}
</script>

<template>
	<SettingsHeader title="Members" :description="data.workspace?.workspace_name || workspace" />
	<SettingsBody>
		<div class="flex col g-3" style="padding-top: 8px">
			<div v-if="!canManage" class="t-sm ink-5">You have read-only access to this workspace's members.</div>
			<div v-for="m in members" :key="m.user" class="pjx-mrow">
				<Avatar :label="m.full_name" size="sm" />
				<span style="flex: 1">{{ m.full_name }}</span>
				<NativeSelect
					v-if="canManage"
					class="pjx-rolesel"
					:options="ROLES"
					:model-value="m.role"
					@change="(v) => changeRole(m.user, v)"
				/>
				<span v-else class="pjx-dim t-xs">{{ m.role }}</span>
				<Button v-if="canManage" variant="ghost" theme="gray" @click="removeMember(m.user)">
					<template #icon><Icon name="x" :size="14" /></template>
				</Button>
			</div>
			<div v-if="canManage" class="flex g-2 items-end">
				<div class="flex col g-1" style="flex: 1">
					<span class="t-xs ink-5">Add members</span>
					<SelectField v-model="newMembers" :options="assignableUsers" multiple placeholder="Pick users" />
				</div>
				<Button variant="subtle" theme="gray" :disabled="!newMembers.length" @click="addMembers">Add</Button>
			</div>
			<span class="t-xs ink-4">Workspace admins can manage its settings, members and teams.</span>
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
</style>
