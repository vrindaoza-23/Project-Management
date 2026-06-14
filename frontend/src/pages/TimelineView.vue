<script setup>
import { computed } from 'vue'
import Icon from '@/components/Icon.vue'
import StatusDot from '@/components/StatusDot.vue'

const props = defineProps({
	issues: { type: Array, default: () => [] },
	statuses: { type: Array, default: () => [] },
})
const emit = defineEmits(['open'])

const statusById = computed(() => Object.fromEntries(props.statuses.map((s) => [s.name, s])))

// Plot issues with due dates on a shared date axis (creation → due as a bar).
const dated = computed(() => props.issues.filter((i) => i.due_date))
const range = computed(() => {
	const times = dated.value.flatMap((i) => [
		i.creation ? new Date(i.creation).getTime() : null,
		new Date(i.due_date).getTime(),
	].filter(Boolean))
	const min = times.length ? Math.min(...times) : Date.now()
	const max = times.length ? Math.max(...times) : Date.now() + 1
	return { min, max, span: Math.max(1, max - min) }
})
const bars = computed(() =>
	dated.value.map((i) => {
		const start = i.creation ? new Date(i.creation).getTime() : range.value.min
		const end = new Date(i.due_date).getTime()
		const left = ((start - range.value.min) / range.value.span) * 100
		const width = Math.max(6, ((end - start) / range.value.span) * 100)
		return { issue: i, left, width }
	}),
)
</script>

<template>
	<div class="pjx-roadmap">
		<div class="pjx-roadmap__grid">
			<div v-for="b in bars" :key="b.issue.name" class="pjx-roadmap__row" @click="emit('open', b.issue.name)">
				<div class="pjx-roadmap__rl">
					<StatusDot :status="statusById[b.issue.status]" />
					<span class="pjx-id">{{ b.issue.issue_id }}</span>
					<span>{{ b.issue.title }}</span>
				</div>
				<div class="pjx-roadmap__track">
					<div
						class="pjx-roadmap__bar"
						:style="{ left: b.left + '%', width: b.width + '%', background: 'var(--blue-500)' }"
					>
						<span class="pjx-roadmap__barlabel">{{ b.issue.issue_id }}</span>
					</div>
				</div>
			</div>
		</div>
		<div v-if="!bars.length" class="pjx-soon" style="height: 280px">
			<span class="pjx-soon__icon"><Icon name="calendar" :size="20" /></span>
			<div class="t-base ink-7" style="font-weight: 500">No scheduled tasks</div>
			<div class="t-sm ink-4">Tasks with a due date appear on the timeline.</div>
		</div>
	</div>
</template>
