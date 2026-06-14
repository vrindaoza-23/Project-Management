<script setup>
import Icon from './Icon.vue'
import PriorityBars from './PriorityBars.vue'
import LabelChip from './LabelChip.vue'
import AvatarStack from './AvatarStack.vue'
import LivePill from './LivePill.vue'
import { isToday, dueLabel } from '@/utils/format'

defineProps({ issue: { type: Object, required: true }, presence: { type: Array, default: () => [] } })
defineEmits(['open'])
</script>

<template>
	<div class="pjx-card" draggable="true" @click="$emit('open', issue.name)">
		<div class="pjx-card__top">
			<PriorityBars :priority="issue.priority" />
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
			<span style="flex: 1" />
			<AvatarStack v-if="issue.assignees.length" :users="issue.assignees" :size="20" />
		</div>
	</div>
</template>
