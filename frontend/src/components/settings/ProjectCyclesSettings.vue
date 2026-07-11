<script setup>
import { ref, computed } from 'vue'
import { createResource, Button, DatePicker, FormControl, SettingsHeader, SettingsBody } from 'frappe-ui'
import Icon from '../Icon.vue'

const props = defineProps({
	project: { type: String, required: true },
	data: { type: Object, required: true }, // get_project_detail payload
})
const emit = defineEmits(['reload'])

const cycleCreate = createResource({ url: 'projex.api.create_cycle' })
const cycleDelete = createResource({ url: 'projex.api.delete_cycle' })

const newCycle = ref({ name: '', start: '', end: '', state: 'Upcoming' })
const canManage = computed(() => props.data?.project?.can_manage)
const cycles = computed(() => props.data?.cycles || [])

async function addCycle() {
	if (!newCycle.value.name.trim()) return
	await cycleCreate.submit({
		project: props.project,
		cycle_name: newCycle.value.name.trim(),
		start_date: newCycle.value.start || null,
		end_date: newCycle.value.end || null,
		state: newCycle.value.state,
	})
	newCycle.value = { name: '', start: '', end: '', state: 'Upcoming' }
	emit('reload')
}
async function removeCycle(name) {
	await cycleDelete.submit({ name })
	emit('reload')
}
</script>

<template>
	<SettingsHeader title="Cycles" :description="`${data.project?.project_name || project} · ${data.project?.key || project}`" />
	<SettingsBody>
		<div class="flex col g-3" style="padding-top: 8px">
			<div v-if="!canManage" class="t-sm ink-5">You have read-only access to this project's settings.</div>
			<div v-for="c in cycles" :key="c.name" class="pjx-mrow">
				<Icon name="calendar-range" :size="15" class="ink-5" />
				<span style="flex: 1">{{ c.cycle_name }}</span>
				<span class="pjx-dim t-xs">{{ c.state }}</span>
				<Button v-if="canManage" variant="ghost" theme="gray" @click="removeCycle(c.name)">
					<template #icon><Icon name="x" :size="14" /></template>
				</Button>
			</div>
			<span v-if="!cycles.length" class="pjx-dim t-xs">No cycles yet.</span>
			<div v-if="canManage" class="flex col g-2">
				<div class="flex g-2">
					<FormControl v-model="newCycle.name" type="text" placeholder="Cycle name" style="flex: 1" />
					<DatePicker v-model="newCycle.start" placeholder="Start date" />
					<DatePicker v-model="newCycle.end" placeholder="End date" />
				</div>
				<div><Button variant="subtle" theme="gray" @click="addCycle">Add cycle</Button></div>
			</div>
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
</style>
