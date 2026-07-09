<script setup>
import { ref, watch, onBeforeUnmount, nextTick } from 'vue'
import { createResource } from 'frappe-ui'
import Gantt from 'frappe-gantt'
import Icon from '@/components/Icon.vue'
import { notifyError } from '@/utils/feedback'

const props = defineProps({ projectKey: { type: String, required: true } })
const emit = defineEmits(['open'])

const el = ref(null)
let gantt = null

const data = createResource({
	url: 'projex.api.get_gantt',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
	onSuccess: () => nextTick(render),
})
watch(() => props.projectKey, () => data.reload())

const updater = createResource({ url: 'projex.api.update_issue' })

function fmt(d) {
	// frappe-gantt passes JS Date; write back local YYYY-MM-DD
	const z = (n) => String(n).padStart(2, '0')
	return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`
}

function onDateChange(task, start, end) {
	updater
		.submit({ name: task.id, fields: JSON.stringify({ start_date: fmt(start), due_date: fmt(end) }) })
		.catch((e) => notifyError(e, 'Could not update task dates'))
}

function render() {
	const tasks = data.data || []
	if (!el.value || !tasks.length) {
		gantt = null
		return
	}
	// frappe-gantt mutates the container; rebuild cleanly each time.
	el.value.innerHTML = ''
	gantt = new Gantt(el.value, tasks, {
		view_mode: 'Week',
		view_modes: ['Day', 'Week', 'Month', 'Quarter Day', 'Year'].filter((m) =>
			['Day', 'Week', 'Month', 'Year'].includes(m),
		),
		view_mode_select: true,
		today_button: true,
		bar_height: 26,
		padding: 16,
		readonly_progress: true,
		on_click: (task) => emit('open', task.id),
		on_date_change: onDateChange,
	})
}

onBeforeUnmount(() => {
	gantt = null
})
</script>

<template>
	<div class="pjx-gantt">
		<div v-if="!data.loading && !(data.data || []).length" class="pjx-soon" style="height: 320px">
			<span class="pjx-soon__icon"><Icon name="gantt-chart" :size="20" /></span>
			<div class="t-base ink-7" style="font-weight: 500">Nothing to plot yet</div>
			<div class="t-sm ink-4">Add tasks with start/due dates to see the Gantt.</div>
		</div>
		<div v-show="(data.data || []).length" ref="el" class="pjx-gantt__canvas" />
	</div>
</template>

<style scoped>
.pjx-gantt {
	height: 100%;
	overflow: auto;
	padding: 12px 16px;
}
.pjx-gantt__canvas {
	width: 100%;
}
/* nudge frappe-gantt toward Espresso tokens */
.pjx-gantt :deep(.gantt .bar) {
	fill: var(--surface-gray-3);
}
.pjx-gantt :deep(.gantt .bar-progress) {
	fill: var(--blue-500);
}
.pjx-gantt :deep(.gantt .bar-label) {
	fill: var(--ink-gray-9);
	font-family: var(--font-sans);
}
.pjx-gantt :deep(.gantt .grid-header) {
	fill: var(--surface-gray-1);
}
.pjx-gantt :deep(.gantt .today-highlight) {
	fill: var(--surface-blue-2);
}
</style>
