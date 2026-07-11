<script setup>
import { ref, computed, onMounted } from 'vue'
import { createResource, Avatar, Button, FormControl } from 'frappe-ui'
import Icon from '../Icon.vue'
import SelectField from '../SelectField.vue'
import { store, reloadBootstrap } from '@/data/store'
import { notify, promptText } from '@/utils/feedback'

const props = defineProps({
	project: { type: String, required: true },
	members: { type: Array, default: () => [] },
	canManage: Boolean,
})
const emit = defineEmits(['changed'])

const memberAdd = createResource({ url: 'projex.api.add_member' })
const memberRemove = createResource({ url: 'projex.api.remove_member' })
const bulkInviter = createResource({ url: 'projex.api.bulk_invite' })
const linkLister = createResource({ url: 'projex.api.list_invite_links' })
const linkCreator = createResource({ url: 'projex.api.create_invite_link' })
const linkRevoker = createResource({ url: 'projex.api.revoke_invite_link' })

const newMember = ref([])
const bulkEmails = ref('')
const bulkResult = ref(null)
const inviteLinks = ref([])

const memberIds = computed(() => props.members.map((m) => m.user))
const assignableUsers = computed(() =>
	store.users
		.map((u) => ({ value: u.name, label: u.full_name || u.name }))
		.filter((u) => !memberIds.value.includes(u.value)),
)

onMounted(() => {
	if (props.canManage) loadLinks()
})

async function addMembers() {
	for (const u of newMember.value) {
		await memberAdd.submit({ parent_doctype: 'Projex Project', parent: props.project, user: u, role: 'Member' })
	}
	newMember.value = []
	emit('changed')
}
async function removeMember(user) {
	await memberRemove.submit({ parent_doctype: 'Projex Project', parent: props.project, user })
	emit('changed')
}

async function bulkInvite() {
	if (!bulkEmails.value.trim()) return
	const res = await bulkInviter.submit({ project: props.project, emails: bulkEmails.value })
	bulkResult.value = res.results || []
	bulkEmails.value = ''
	await reloadBootstrap()
	emit('changed')
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
		notify.success('Invite link copied to clipboard')
	} catch {
		await promptText({ title: 'Copy invite link', label: 'Select and copy', value: url })
	}
}
async function revokeLink(name) {
	await linkRevoker.submit({ name })
	await loadLinks()
}
</script>

<template>
	<div class="flex col g-3">
		<div v-for="m in members" :key="m.user" class="pjx-mrow">
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
				<FormControl
					v-model="bulkEmails"
					type="textarea"
					:rows="2"
					placeholder="ann@company.com, ben@company.com&#10;cara@company.com"
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
					<FormControl class="pjx-linkurl" type="text" :model-value="lk.url" readonly @focus="(e) => e.target.select()" />
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
