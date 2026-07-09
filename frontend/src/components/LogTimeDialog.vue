<script setup>
import { ref, watch } from 'vue'
import { createResource, Dialog, Button } from 'frappe-ui'
import SelectField from './SelectField.vue'

const props = defineProps({ open: Boolean, issue: { type: String, required: true } })
const emit = defineEmits(['close', 'logged'])

const hours = ref(1)
const activity = ref('')
const note = ref('')
const error = ref('')

const activityTypes = createResource({ url: 'projex.api.get_activity_types', auto: true })
const logger = createResource({ url: 'projex.api.log_time' })

watch(
	() => props.open,
	(v) => {
		if (v) {
			hours.value = 1
			activity.value = ''
			note.value = ''
			error.value = ''
		}
	},
)

const activityOptions = () => (activityTypes.data || []).map((a) => ({ value: a, label: a }))

async function submit() {
	error.value = ''
	try {
		await logger.submit({
			issue: props.issue,
			hours: hours.value,
			activity_type: activity.value || null,
			note: note.value || null,
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
					<span class="t-xs ink-5">Hours</span>
					<input v-model.number="hours" type="number" min="0" step="0.25" class="input" style="width: 120px" />
				</label>
				<label class="flex col g-1">
					<span class="t-xs ink-5">Activity type</span>
					<SelectField
						:options="activityOptions()"
						:model-value="activity"
						placeholder="Select…"
						@change="(v) => (activity = v || '')"
					/>
				</label>
				<label class="flex col g-1">
					<span class="t-xs ink-5">Note</span>
					<textarea v-model="note" class="input" rows="2" style="resize: vertical" />
				</label>
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
