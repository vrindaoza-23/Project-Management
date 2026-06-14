<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { createResource, Dialog, Button, FormControl, DatePicker } from 'frappe-ui'
import Icon from './Icon.vue'
import SelectField from './SelectField.vue'
import { store } from '@/data/store'

const props = defineProps({ open: Boolean, defaultProject: { type: String, default: '' } })
const emit = defineEmits(['close', 'created'])

const title = ref('')
const project = ref('')
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

async function submit() {
	if (!title.value.trim() || !project.value) return
	await creator.submit({
		payload: JSON.stringify({
			title: title.value.trim(),
			project: project.value,
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
		<template #body-title><h3 class="t-lg" style="font-weight: 600">New task</h3></template>
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
						<FormControl v-model="project" type="select" size="sm" :options="projectOptions" />
					</div>
					<div class="pjx-fld">
						<span class="pjx-fld__l">Priority</span>
						<FormControl v-model="priority" type="select" size="sm" :options="PRIORITIES" />
					</div>
					<div class="pjx-fld">
						<span class="pjx-fld__l">Assignees</span>
						<SelectField v-model="assignees" :options="userOptions" multiple placeholder="Unassigned" />
					</div>
					<div class="pjx-fld">
						<span class="pjx-fld__l">Labels</span>
						<SelectField v-model="labels" :options="labelOptions" multiple placeholder="None" />
					</div>
					<div class="pjx-fld">
						<span class="pjx-fld__l">Due date</span>
						<DatePicker v-model="dueDate" placeholder="No date" />
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
				<Button variant="solid" theme="gray" :loading="creator.loading" @click="submit">
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
</style>
