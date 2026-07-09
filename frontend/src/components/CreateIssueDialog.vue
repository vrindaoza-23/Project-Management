<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { createResource, Dialog, Button, FormControl } from 'frappe-ui'
import Icon from './Icon.vue'
import NativeSelect from './NativeSelect.vue'
import { store } from '@/data/store'

const props = defineProps({
	open: Boolean,
	defaultProject: { type: String, default: '' },
	defaultType: { type: String, default: 'Task' },
})
const emit = defineEmits(['close', 'created'])

const title = ref('')
const project = ref('')
const issueType = ref('Task')
const priority = ref('None')
const assignees = ref([])
const labels = ref([])
const dueDate = ref('')
const estimate = ref('')
const description = ref('')

const pickers = createResource({ url: 'projex.api.get_pickers' })
const creator = createResource({ url: 'projex.api.create_issue' })

watch(
	() => props.open,
	(v) => {
		if (v) {
			title.value = ''
			issueType.value = props.defaultType || 'Task'
			priority.value = 'None'
			assignees.value = []
			labels.value = []
			dueDate.value = ''
			estimate.value = ''
			description.value = ''
			project.value = props.defaultProject || store.projects[0]?.key || ''
			if (project.value) pickers.submit({ project: project.value })
		}
	},
)
watch(project, (p) => {
	if (p) pickers.submit({ project: p })
})

const projectOptions = computed(() => store.projects.map((p) => ({ value: p.key, label: p.project_name })))
const userOptions = computed(() =>
	(pickers.data?.users || store.users).map((u) => ({ value: u.name, label: u.full_name || u.name })),
)
const labelOptions = computed(() =>
	(pickers.data?.labels || []).map((l) => ({ value: l.name, label: l.label_name, color: l.color })),
)
const PRIORITIES = ['Urgent', 'High', 'Medium', 'Low', 'None'].map((p) => ({ value: p, label: p }))
const TYPES = ['Task', 'Bug', 'Story', 'Epic'].map((t) => ({ value: t, label: t }))

async function submit() {
	if (!title.value.trim() || !project.value) return
	await creator.submit({
		payload: JSON.stringify({
			title: title.value.trim(),
			project: project.value,
			issue_type: issueType.value,
			priority: priority.value,
			assignees: assignees.value,
			labels: labels.value,
			due_date: dueDate.value || null,
			estimate: estimate.value || null,
			description: description.value ? `<p>${description.value}</p>` : null,
		}),
	})
	emit('created')
	emit('close')
}
</script>

<template>
	<Dialog :model-value="open" @update:model-value="(v) => !v && emit('close')" :options="{ size: 'lg' }">
		<template #body-title><h3 class="t-lg" style="font-weight: 600">New {{ issueType === 'Task' ? 'task' : issueType.toLowerCase() }}</h3></template>
		<template #body-content>
			<div class="flex col g-4" style="padding-top: 4px">
				<FormControl
					v-model="title"
					type="text"
					label="Title"
					placeholder="Task title"
					autofocus
				/>
				<FormControl
					v-model="description"
					type="textarea"
					label="Description"
					placeholder="Add more detail…"
					:rows="3"
					:data-gramm="false"
				/>

				<div class="pjx-grid">
					<div class="pjx-fld">
						<span class="pjx-fld__l">Project</span>
						<NativeSelect v-model="project" :options="projectOptions" placeholder="Select project" />
					</div>
					<div class="pjx-fld">
						<span class="pjx-fld__l">Type</span>
						<NativeSelect v-model="issueType" :options="TYPES" />
					</div>
					<div class="pjx-fld">
						<span class="pjx-fld__l">Priority</span>
						<NativeSelect v-model="priority" :options="PRIORITIES" />
					</div>
					<div class="pjx-fld">
						<span class="pjx-fld__l">Assignees</span>
						<NativeSelect v-model="assignees" :options="userOptions" multiple placeholder="Unassigned" />
					</div>
					<div class="pjx-fld">
						<span class="pjx-fld__l">Labels</span>
						<NativeSelect v-model="labels" :options="labelOptions" multiple placeholder="None" />
					</div>
					<div class="pjx-fld">
						<span class="pjx-fld__l">Due date</span>
						<input v-model="dueDate" type="date" class="pjx-dateinput" />
					</div>
					<div class="pjx-fld">
						<span class="pjx-fld__l">Estimate</span>
						<FormControl v-model="estimate" type="number" size="sm" placeholder="Points" />
					</div>
				</div>
			</div>
		</template>
		<template #actions>
			<div class="flex" style="gap: 8px; justify-content: flex-end; width: 100%">
				<Button variant="subtle" theme="gray" @click="emit('close')">Cancel</Button>
				<Button variant="solid" theme="blue" :loading="creator.loading" @click="submit">
					<template #prefix><Icon name="plus" :size="14" /></template>
					Create task
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<style scoped>
.pjx-grid {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 12px 16px;
}
.pjx-fld {
	display: flex;
	flex-direction: column;
	gap: 4px;
	min-width: 0;
}
.pjx-fld__l {
	font-size: 12px;
	color: var(--ink-gray-5);
}
.pjx-dateinput {
	width: 100%;
	height: 28px;
	padding: 0 10px;
	font-size: 13px;
	font-family: var(--font-sans);
	color: var(--ink-gray-8);
	background: var(--surface-gray-2);
	border: 1px solid transparent;
	border-radius: 8px;
}
.pjx-dateinput:hover {
	background: var(--surface-gray-3);
}
.pjx-dateinput:focus {
	outline: none;
	border-color: var(--outline-gray-3);
	background: var(--surface-white);
}
</style>
