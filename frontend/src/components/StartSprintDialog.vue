<script setup>
import { ref, watch } from 'vue'
import { createResource, Dialog, Button, DatePicker } from 'frappe-ui'

const props = defineProps({
	open: Boolean,
	cycle: { type: Object, default: null }, // { name, cycle_name, start_date, end_date, goal }
})
const emit = defineEmits(['close', 'started'])

const start = ref('')
const end = ref('')
const goal = ref('')
const error = ref('')

const starter = createResource({ url: 'projex.api.start_sprint' })

function todayISO() {
	const d = new Date()
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function addWeeks(iso, weeks) {
	const d = iso ? new Date(iso + 'T00:00:00') : new Date()
	d.setDate(d.getDate() + weeks * 7)
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function preset(weeks) {
	if (!start.value) start.value = todayISO()
	end.value = addWeeks(start.value, weeks)
}

watch(
	() => props.open,
	(v) => {
		if (v && props.cycle) {
			start.value = props.cycle.start_date || todayISO()
			end.value = props.cycle.end_date || addWeeks(start.value, 2)
			goal.value = props.cycle.goal || ''
			error.value = ''
		}
	},
)

async function submit() {
	error.value = ''
	try {
		await starter.submit({
			cycle: props.cycle.name,
			start_date: start.value || null,
			end_date: end.value || null,
			goal: goal.value || '',
		})
		emit('started')
		emit('close')
	} catch (e) {
		error.value = e?.messages?.[0] || 'Could not start sprint'
	}
}
</script>

<template>
	<Dialog :model-value="open" @update:model-value="(v) => !v && emit('close')">
		<template #body-title><h3 class="t-lg" style="font-weight: 600">Start sprint · {{ cycle?.cycle_name }}</h3></template>
		<template #body-content>
			<div class="flex col g-3" style="padding-top: 4px">
				<div class="flex col g-1">
					<span class="t-xs ink-5">Duration</span>
					<div class="flex g-1">
						<Button variant="subtle" theme="gray" size="sm" @click="preset(1)">1 week</Button>
						<Button variant="subtle" theme="gray" size="sm" @click="preset(2)">2 weeks</Button>
						<Button variant="subtle" theme="gray" size="sm" @click="preset(3)">3 weeks</Button>
					</div>
				</div>
				<div class="flex g-2">
					<label class="flex col g-1" style="flex: 1">
						<span class="t-xs ink-5">Start</span>
						<DatePicker v-model="start" placeholder="Start date" />
					</label>
					<label class="flex col g-1" style="flex: 1">
						<span class="t-xs ink-5">End</span>
						<DatePicker v-model="end" placeholder="End date" />
					</label>
				</div>
				<label class="flex col g-1">
					<span class="t-xs ink-5">Sprint goal</span>
					<textarea v-model="goal" class="input" rows="2" placeholder="What is this sprint trying to achieve?" style="resize: vertical; font-family: var(--font-sans)" />
				</label>
				<div v-if="error" class="t-sm ink-red">{{ error }}</div>
			</div>
		</template>
		<template #actions>
			<div class="flex" style="gap: 8px; justify-content: flex-end; width: 100%">
				<Button variant="subtle" theme="gray" @click="emit('close')">Cancel</Button>
				<Button variant="solid" theme="green" :loading="starter.loading" @click="submit">Start sprint</Button>
			</div>
		</template>
	</Dialog>
</template>
