<script setup>
import { computed } from 'vue'
import Icon from '@/components/Icon.vue'
import StatusDot from '@/components/StatusDot.vue'
import PriorityBars from '@/components/PriorityBars.vue'
import LabelChip from '@/components/LabelChip.vue'
import AvatarStack from '@/components/AvatarStack.vue'
import LivePill from '@/components/LivePill.vue'
import QuickAdd from '@/components/QuickAdd.vue'
import { isToday, dueLabel, relativeTime } from '@/utils/format'

const props = defineProps({
	projectKey: { type: String, required: true },
	issues: { type: Array, default: () => [] },
	statuses: { type: Array, default: () => [] },
	groupBy: { type: String, default: 'status' },
	presence: { type: Object, default: () => ({}) },
	loading: { type: Boolean, default: false },
})
const emit = defineEmits(['open', 'created'])

const statusById = computed(() => Object.fromEntries(props.statuses.map((s) => [s.name, s])))

const PRIORITY_ORDER = ['Urgent', 'High', 'Medium', 'Low', 'None']

// Group issues by the active groupBy; hide empty groups.
const groups = computed(() => {
	if (props.groupBy === 'none') {
		return props.issues.length ? [{ key: 'all', label: 'All issues', items: props.issues }] : []
	}
	if (props.groupBy === 'priority') {
		return PRIORITY_ORDER.map((p) => ({
			key: p, label: p, priority: p,
			items: props.issues.filter((i) => (i.priority || 'None') === p),
		})).filter((g) => g.items.length)
	}
	const ordered = [...props.statuses].sort((a, b) => (a.position || 0) - (b.position || 0))
	return ordered
		.map((s) => ({ key: s.name, label: s.status_name, status: s, items: props.issues.filter((i) => i.status === s.name) }))
		.filter((g) => g.items.length)
})
</script>

<template>
	<div class="pjx-list">
		<QuickAdd :project-key="projectKey" @created="emit('created')" />

		<div class="pjx-list__head">
			<span></span>
			<span>Task</span>
			<span>Labels</span>
			<span class="r">Pts</span>
			<span class="r">Due</span>
			<span class="r">Updated</span>
			<span class="r">Assignees</span>
		</div>

		<template v-if="loading">
			<div v-for="n in 6" :key="n" class="pjx-row" style="opacity: 0.5">
				<span class="pjx-cell"></span>
				<span class="pjx-cell pjx-titlecell">
					<span class="pjx-skel" style="width: 40%" />
				</span>
			</div>
		</template>

		<template v-else>
			<div v-for="g in groups" :key="g.key">
				<div class="pjx-grouphead">
					<StatusDot v-if="g.status" :status="g.status" />
					<PriorityBars v-else-if="g.priority" :priority="g.priority" />
					<span class="pjx-grouphead__name">{{ g.label }}</span>
					<span class="pjx-grouphead__count">{{ g.items.length }}</span>
				</div>

				<div v-for="it in g.items" :key="it.name" class="pjx-row" @click="emit('open', it.name)">
					<span class="pjx-cell"><PriorityBars :priority="it.priority" /></span>
					<span class="pjx-cell pjx-titlecell">
						<StatusDot :status="statusById[it.status]" />
						<span class="pjx-id">{{ it.issue_id }}</span>
						<span class="pjx-title">{{ it.title }}</span>
						<span v-if="it.sub_total" class="pjx-meta"
							><Icon name="list-checks" :size="13" />{{ it.sub_done }}/{{ it.sub_total }}</span
						>
						<span v-if="it.comment_count" class="pjx-meta"
							><Icon name="message-square" :size="13" />{{ it.comment_count }}</span
						>
						<LivePill :users="presence[it.name] || []" />
					</span>
					<span class="pjx-cell">
						<LabelChip v-for="l in it.labels.slice(0, 2)" :key="l.label" :label="l" />
						<span v-if="it.labels.length > 2" class="pjx-dim t-xs">+{{ it.labels.length - 2 }}</span>
					</span>
					<span class="pjx-cell r">
						<span v-if="it.estimate" class="pjx-pts">{{ it.estimate }}</span>
						<span v-else class="pjx-dim">–</span>
					</span>
					<span class="pjx-cell r">
						<span v-if="it.due_date" class="pjx-due" :class="{ 'is-today': isToday(it.due_date) }">{{
							dueLabel(it.due_date)
						}}</span>
						<span v-else class="pjx-dim">–</span>
					</span>
					<span class="pjx-cell r"><span class="pjx-dim t-xs">{{ relativeTime(it.modified) }}</span></span>
					<span class="pjx-cell r">
						<AvatarStack v-if="it.assignees.length" :users="it.assignees" :size="22" />
						<span v-else class="pjx-noass">–</span>
					</span>
				</div>
			</div>

			<div v-if="!groups.length" class="pjx-soon" style="height: 320px">
				<span class="pjx-soon__icon"><Icon name="inbox" :size="20" /></span>
				<div class="t-base ink-7" style="font-weight: 500">No tasks yet</div>
				<div class="t-sm ink-4">Create one above to get started.</div>
			</div>
		</template>
	</div>
</template>
