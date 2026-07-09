<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import PriorityBars from './PriorityBars.vue'
import LabelChip from './LabelChip.vue'
import AvatarStack from './AvatarStack.vue'
import LivePill from './LivePill.vue'
import { isToday, dueLabel, ageChip } from '@/utils/format'

const props = defineProps({ issue: { type: Object, required: true }, presence: { type: Array, default: () => [] } })
const emit = defineEmits(['pickup'])

// Pending age (time in current status) — only surface once it's been sitting ≥3 days.
const age = computed(() => ageChip(props.issue.status_changed_on, props.issue.modified))

// Pointer-based drag: the parent (BoardView) owns the gesture. We just hand it
// the card element + issue on pointer-down; it decides click-to-open vs. drag.
function onPointerDown(e) {
	if (e.button !== 0) return // primary button only
	emit('pickup', { issue: props.issue, event: e, el: e.currentTarget })
}
</script>

<template>
	<div class="pjx-card" @pointerdown="onPointerDown">
		<div class="pjx-card__top">
			<PriorityBars :priority="issue.priority" />
			<span
				v-if="issue.issue_type && issue.issue_type !== 'Task'"
				class="pjx-type"
				:data-type="issue.issue_type"
				:title="issue.issue_type"
			>{{ issue.issue_type[0] }}</span>
			<span class="pjx-id">{{ issue.issue_id }}</span>
			<LivePill :users="presence" />
			<span style="flex: 1" />
			<span v-if="issue.due_date" class="pjx-due" :class="{ 'is-today': isToday(issue.due_date) }">{{
				dueLabel(issue.due_date)
			}}</span>
		</div>
		<div class="pjx-card__title">{{ issue.title }}</div>
		<div v-if="issue.labels.length" class="pjx-card__labels">
			<LabelChip v-for="l in issue.labels.slice(0, 3)" :key="l.label" :label="l" />
		</div>
		<div class="pjx-card__foot">
			<span v-if="issue.sub_total" class="pjx-meta"
				><Icon name="list-checks" :size="13" />{{ issue.sub_done }}/{{ issue.sub_total }}</span
			>
			<span v-if="issue.comment_count" class="pjx-meta"
				><Icon name="message-square" :size="13" />{{ issue.comment_count }}</span
			>
			<span v-if="issue.estimate" class="pjx-pts">{{ issue.estimate }}</span>
			<span
				v-if="issue.reopen_count"
				class="pjx-rwk"
				:title="`Reopened ${issue.reopen_count}×`"
			><Icon name="undo-2" :size="12" />{{ issue.reopen_count }}</span>
			<span
				v-if="issue.rework_count"
				class="pjx-rwk"
				:title="`Sent back ${issue.rework_count}×`"
			><Icon name="rotate-ccw" :size="12" />{{ issue.rework_count }}</span>
			<span style="flex: 1" />
			<span v-if="age.days >= 3" class="pjx-age" :data-level="age.level" :title="`In status ${age.label}`">{{ age.label }}</span>
			<AvatarStack v-if="issue.assignees.length" :users="issue.assignees" :size="20" />
		</div>
	</div>
</template>

<style scoped>
.pjx-type {
	display: inline-grid;
	place-items: center;
	width: 16px;
	height: 16px;
	border-radius: 4px;
	font-size: 10px;
	font-weight: 700;
	color: #fff;
	background: var(--gray-500);
}
.pjx-type[data-type='Bug'] { background: var(--red-500); }
.pjx-type[data-type='Story'] { background: var(--green-600); }
.pjx-type[data-type='Epic'] { background: var(--purple-500); }
</style>
