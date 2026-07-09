<script setup>
import { ref, computed, watch } from 'vue'
import { createResource, Dialog, Button } from 'frappe-ui'
import NativeSelect from './NativeSelect.vue'

const props = defineProps({
	open: Boolean,
	cycle: { type: Object, default: null }, // { name, cycle_name }
	issues: { type: Array, default: () => [] }, // issues currently in this cycle
	statuses: { type: Array, default: () => [] },
	upcoming: { type: Array, default: () => [] }, // [{ value, label }] other cycles to carry into
})
const emit = defineEmits(['close', 'completed'])

const carryoverTo = ref('') // '' = backlog
const error = ref('')

const completer = createResource({ url: 'projex.api.complete_sprint' })

const completedSet = computed(
	() => new Set(props.statuses.filter((s) => ['completed', 'cancelled'].includes(s.category)).map((s) => s.name)),
)
const doneCount = computed(() => props.issues.filter((i) => completedSet.value.has(i.status)).length)
const openCount = computed(() => props.issues.length - doneCount.value)

const carryOptions = computed(() => [{ value: '', label: 'Move to Backlog' }, ...props.upcoming])

watch(
	() => props.open,
	(v) => {
		if (v) {
			carryoverTo.value = ''
			error.value = ''
		}
	},
)

async function submit() {
	error.value = ''
	try {
		const res = await completer.submit({ cycle: props.cycle.name, carryover_to: carryoverTo.value || null })
		emit('completed', res)
		emit('close')
	} catch (e) {
		error.value = e?.messages?.[0] || 'Could not complete sprint'
	}
}
</script>

<template>
	<Dialog :model-value="open" @update:model-value="(v) => !v && emit('close')">
		<template #body-title><h3 class="t-lg" style="font-weight: 600">Complete sprint · {{ cycle?.cycle_name }}</h3></template>
		<template #body-content>
			<div class="flex col g-3" style="padding-top: 4px">
				<div class="flex g-2">
					<div class="pjx-cs-stat"><b>{{ doneCount }}</b><span>completed</span></div>
					<div class="pjx-cs-stat"><b>{{ openCount }}</b><span>unfinished</span></div>
				</div>
				<div v-if="openCount" class="flex col g-1">
					<span class="t-xs ink-5">Move the {{ openCount }} unfinished task{{ openCount === 1 ? '' : 's' }} to</span>
					<NativeSelect v-model="carryoverTo" :options="carryOptions" />
				</div>
				<div v-else class="t-sm ink-5">🎉 Everything is done — nothing to carry over.</div>
				<div v-if="error" class="t-sm ink-red">{{ error }}</div>
			</div>
		</template>
		<template #actions>
			<div class="flex" style="gap: 8px; justify-content: flex-end; width: 100%">
				<Button variant="subtle" theme="gray" @click="emit('close')">Cancel</Button>
				<Button variant="solid" theme="blue" :loading="completer.loading" @click="submit">Complete sprint</Button>
			</div>
		</template>
	</Dialog>
</template>

<style scoped>
.pjx-cs-stat {
	display: flex;
	flex-direction: column;
	align-items: center;
	flex: 1;
	padding: 12px;
	background: var(--surface-gray-1);
	border-radius: 10px;
}
.pjx-cs-stat b {
	font-size: 22px;
	color: var(--ink-gray-9);
}
.pjx-cs-stat span {
	font-size: 12px;
	color: var(--ink-gray-5);
}
</style>
