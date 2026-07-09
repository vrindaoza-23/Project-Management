<script setup>
import { ref, watch } from 'vue'
import { createResource, Dialog, Button, FormControl } from 'frappe-ui'
import Icon from './Icon.vue'
import { reloadBootstrap } from '@/data/store'
import { ui } from '@/data/ui'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['close'])

const name = ref('')
const icon = ref('box')
const error = ref('')

const creator = createResource({ url: 'projex.api.create_workspace' })
const ICONS = ['box', 'rocket', 'building', 'users', 'briefcase', 'globe']

watch(
	() => props.open,
	(v) => {
		if (v) {
			name.value = ''
			icon.value = 'box'
			error.value = ''
		}
	},
)

async function submit() {
	error.value = ''
	if (!name.value.trim()) return (error.value = 'Workspace name is required')
	try {
		const res = await creator.submit({ workspace_name: name.value.trim(), icon: icon.value })
		await reloadBootstrap()
		ui.currentWorkspace = res.name
		emit('close')
	} catch (e) {
		error.value = e?.messages?.[0] || 'Could not create workspace'
	}
}
</script>

<template>
	<Dialog :model-value="open" @update:model-value="(v) => !v && emit('close')">
		<template #body-title><h3 class="t-lg" style="font-weight: 600">New workspace</h3></template>
		<template #body-content>
			<div class="flex col g-3" style="padding-top: 4px">
				<FormControl v-model="name" type="text" label="Workspace name" placeholder="e.g. Acme Inc" autofocus />
				<div class="flex col g-1">
					<span class="t-xs ink-5">Icon</span>
					<div class="flex g-1">
						<button v-for="ic in ICONS" :key="ic" class="pjx-pick" :class="{ on: icon === ic }" @click="icon = ic">
							<Icon :name="ic" :size="16" />
						</button>
					</div>
				</div>
				<div v-if="error" class="t-sm ink-red">{{ error }}</div>
			</div>
		</template>
		<template #actions>
			<div class="flex" style="gap: 8px; justify-content: flex-end; width: 100%">
				<Button variant="subtle" theme="gray" @click="emit('close')">Cancel</Button>
				<Button variant="solid" theme="blue" :loading="creator.loading" @click="submit">Create workspace</Button>
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
</style>
