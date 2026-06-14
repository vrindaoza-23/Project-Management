<script setup>
import { ref, computed } from 'vue'
import { createResource } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import StatusDot from '@/components/StatusDot.vue'
import BoardCard from '@/components/BoardCard.vue'

const props = defineProps({
	issues: { type: Array, default: () => [] },
	statuses: { type: Array, default: () => [] },
	presence: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['open', 'changed'])

const dragName = ref(null)
const overStatus = ref(null)

const columns = computed(() =>
	[...props.statuses]
		.sort((a, b) => (a.position || 0) - (b.position || 0))
		.map((s) => ({ status: s, items: props.issues.filter((i) => i.status === s.name) })),
)

const updater = createResource({ url: 'projex.api.update_issue' })
const reorder = createResource({ url: 'projex.api.reorder_issue' })

function onDragStart(name) {
	dragName.value = name
}

async function onDrop(statusName) {
	overStatus.value = null
	const name = dragName.value
	dragName.value = null
	if (!name) return
	const issue = props.issues.find((i) => i.name === name)
	if (!issue || issue.status === statusName) return

	const prev = issue.status
	issue.status = statusName // optimistic
	try {
		await updater.submit({ name, fields: JSON.stringify({ status: statusName }) })
		emit('changed')
	} catch (e) {
		issue.status = prev // rollback
		console.error('[projex] status update failed', e)
	}
}

// Drop directly onto a card: reorder before it (and adopt its status).
async function onCardDrop(targetIssue) {
	const name = dragName.value
	dragName.value = null
	overStatus.value = null
	if (!name || name === targetIssue.name) return
	const moving = props.issues.find((i) => i.name === name)
	if (!moving) return
	const col = columns.value.find((c) => c.status.name === targetIssue.status)
	const idx = col.items.findIndex((i) => i.name === targetIssue.name)
	const after = idx > 0 ? col.items[idx - 1].name : null
	if (moving.status !== targetIssue.status) {
		moving.status = targetIssue.status
		await updater.submit({ name, fields: JSON.stringify({ status: targetIssue.status }) }).catch(() => {})
	}
	await reorder.submit({ issue: name, before: targetIssue.name, after }).catch(() => {})
	emit('changed')
}
</script>

<template>
	<div class="pjx-board">
		<div class="pjx-board__cols">
			<div
				v-for="col in columns"
				:key="col.status.name"
				class="pjx-col"
				:class="{ 'is-over': overStatus === col.status.name }"
				@dragover.prevent="overStatus = col.status.name"
				@dragleave="overStatus = null"
				@drop="onDrop(col.status.name)"
			>
				<div class="pjx-col__head">
					<StatusDot :status="col.status" />
					<span class="pjx-col__name">{{ col.status.status_name }}</span>
					<span class="pjx-col__count">{{ col.items.length }}</span>
				</div>
				<div class="pjx-col__body">
					<BoardCard
						v-for="it in col.items"
						:key="it.name"
						:issue="it"
						:presence="presence[it.name] || []"
						@dragstart="onDragStart(it.name)"
						@drop="onCardDrop(it)"
						@dragover.prevent.stop
						@open="emit('open', $event)"
					/>
					<div v-if="!col.items.length" class="pjx-col__empty">No tasks</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-col.is-over {
	outline: 2px solid var(--outline-blue-1);
	outline-offset: -2px;
}
</style>
