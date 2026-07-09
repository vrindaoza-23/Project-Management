<script setup>
import { ref, computed, watch } from 'vue'
import { createResource, Dialog, Button, DatePicker, FormControl, Checkbox } from 'frappe-ui'
import NativeSelect from './NativeSelect.vue'

const props = defineProps({
	open: Boolean,
	projectKey: { type: String, required: true },
	issue: { type: String, default: '' }, // optional preselected task
})
const emit = defineEmits(['close', 'logged'])

const task = ref('')
const hours = ref(1)
const date = ref('')
const activity = ref('')
const billable = ref(true)
const note = ref('')
const error = ref('')

const issues = createResource({
	url: 'projex.api.get_issues',
	makeParams: () => ({ project: props.projectKey }),
})
const logger = createResource({ url: 'projex.api.create_time_log' })

const taskOptions = computed(() =>
	(issues.data?.issues || []).map((i) => ({ value: i.name, label: `${i.issue_id} · ${i.title}` })),
)

function todayISO() {
	const d = new Date()
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

watch(
	() => props.open,
	(v) => {
		if (v) {
			task.value = props.issue || ''
			hours.value = 1
			date.value = todayISO()
			activity.value = ''
			billable.value = true
			note.value = ''
			error.value = ''
			if (!issues.data) issues.reload()
		}
	},
)

async function submit() {
	error.value = ''
	if (!task.value) return (error.value = 'Pick a task')
	if (!hours.value || hours.value <= 0) return (error.value = 'Enter hours')
	try {
		await logger.submit({
			issue: task.value,
			hours: hours.value,
			activity: activity.value || null,
			note: note.value || null,
			spent_on: date.value || null,
			is_billable: billable.value ? 1 : 0,
		})
		emit('logged')
		emit('close')
	} catch (e) {
		error.value = e?.messages?.[0] || 'Could not log time'
	}
}
</script>

<template>
	<Dialog :model-value="open" @update:model-value="(v) => !v && emit('close')">
		<template #body-title><h3 class="t-lg" style="font-weight: 600">Log time</h3></template>
		<template #body-content>
			<div class="flex col g-3" style="padding-top: 4px">
				<label class="flex col g-1">
					<span class="t-xs ink-5">Task</span>
					<NativeSelect v-model="task" :options="taskOptions" placeholder="Pick a task" />
				</label>
				<div class="flex g-2">
					<div style="width: 120px">
						<FormControl v-model.number="hours" type="number" label="Hours" :min="0" :step="0.25" />
					</div>
					<label class="flex col g-1" style="flex: 1">
						<span class="t-xs ink-5">Date</span>
						<DatePicker v-model="date" placeholder="Date" />
					</label>
				</div>
				<FormControl v-model="activity" type="text" label="Activity (optional)" placeholder="e.g. Development, Review, Meeting" />
				<Checkbox v-model="billable" label="Billable" />
				<FormControl v-model="note" type="textarea" label="Note" :rows="2" />
				<div v-if="error" class="t-sm ink-red">{{ error }}</div>
			</div>
		</template>
		<template #actions>
			<div class="flex" style="gap: 8px; justify-content: flex-end; width: 100%">
				<Button variant="subtle" theme="gray" @click="emit('close')">Cancel</Button>
				<Button variant="solid" theme="blue" :loading="logger.loading" @click="submit">Log time</Button>
			</div>
		</template>
	</Dialog>
</template>
