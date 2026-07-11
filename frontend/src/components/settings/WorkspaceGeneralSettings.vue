<script setup>
import { ref, watch, computed } from 'vue'
import { createResource, Button, FormControl, SettingsHeader, SettingsBody } from 'frappe-ui'
import Icon from '../Icon.vue'
import { reloadBootstrap } from '@/data/store'
import { ui } from '@/data/ui'
import { notify, notifyError, confirm } from '@/utils/feedback'

const props = defineProps({
	workspace: { type: String, required: true },
	data: { type: Object, required: true }, // get_workspace_detail payload
})
const emit = defineEmits(['reload', 'deleted'])

const updater = createResource({ url: 'projex.api.update_workspace' })
const deleter = createResource({ url: 'projex.api.delete_workspace' })

const ICONS = ['box', 'rocket', 'building', 'users', 'briefcase', 'globe']

const form = ref({ workspace_name: '', icon: 'box', description: '' })
watch(
	() => props.data,
	(d) => {
		if (d?.workspace) {
			form.value = {
				workspace_name: d.workspace.workspace_name || '',
				icon: d.workspace.icon || 'box',
				description: d.workspace.description || '',
			}
		}
	},
	{ immediate: true },
)

const canManage = computed(() => props.data?.workspace?.can_manage)
const projectCount = computed(() => props.data?.workspace?.project_count || 0)

async function save() {
	await updater.submit({
		workspace: props.workspace,
		fields: JSON.stringify({
			workspace_name: form.value.workspace_name,
			icon: form.value.icon,
			description: form.value.description,
		}),
	})
	await reloadBootstrap()
	emit('reload')
	notify.success('Workspace settings saved')
}

async function confirmDelete() {
	const label = form.value.workspace_name || props.workspace
	if (projectCount.value) {
		notify.warning('Move or delete this workspace’s projects before deleting it.')
		return
	}
	const ok = await confirm({
		title: `Delete workspace “${label}”`,
		message: 'Its teams will be deleted too. This cannot be undone.',
		confirmLabel: 'Delete workspace',
		theme: 'red',
	})
	if (!ok) return
	try {
		await deleter.submit({ workspace: props.workspace })
		if (ui.currentWorkspace === props.workspace) ui.currentWorkspace = null
		await reloadBootstrap()
		notify.success(`Workspace “${label}” deleted`)
		emit('deleted', props.workspace)
	} catch (e) {
		notifyError(e, 'Could not delete workspace')
	}
}
</script>

<template>
	<SettingsHeader title="General" :description="data.workspace?.workspace_name || workspace">
		<template #actions>
			<Button v-if="canManage" variant="solid" theme="gray" :loading="updater.loading" @click="save">Save changes</Button>
		</template>
	</SettingsHeader>
	<SettingsBody>
		<div class="flex col g-3" style="padding-top: 8px">
			<div v-if="!canManage" class="t-sm ink-5">You have read-only access to this workspace's settings.</div>
			<div class="flex col g-1">
				<span class="t-xs ink-5">Name</span>
				<FormControl v-model="form.workspace_name" type="text" :disabled="!canManage" placeholder="Workspace name" />
			</div>
			<div class="flex col g-1">
				<span class="t-xs ink-5">Icon</span>
				<div class="flex g-1">
					<button
						v-for="ic in ICONS"
						:key="ic"
						class="pjx-pick"
						:class="{ on: form.icon === ic }"
						:disabled="!canManage"
						@click="form.icon = ic"
					>
						<Icon :name="ic" :size="16" />
					</button>
				</div>
			</div>
			<div class="flex col g-1">
				<span class="t-xs ink-5">Description</span>
				<FormControl v-model="form.description" type="textarea" :rows="2" :disabled="!canManage" placeholder="What is this workspace for?" />
			</div>

			<div v-if="canManage" class="pjx-danger">
				<div class="flex col g-1" style="flex: 1">
					<span class="t-sm" style="font-weight: 600; color: var(--ink-red-3)">Delete workspace</span>
					<span class="t-xs ink-5">
						{{ projectCount ? `Holds ${projectCount} project${projectCount === 1 ? '' : 's'} — move or delete them first.` : 'Removes this workspace and its teams. This can\'t be undone.' }}
					</span>
				</div>
				<Button theme="red" variant="subtle" :disabled="!!projectCount" :loading="deleter.loading" @click="confirmDelete">Delete workspace…</Button>
			</div>
		</div>
	</SettingsBody>
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
.pjx-pick:disabled {
	cursor: default;
	opacity: 0.6;
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
</style>
