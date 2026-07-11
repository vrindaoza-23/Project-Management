<script setup>
import { computed, watch } from 'vue'
import { createResource, Avatar } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import { relativeTime } from '@/utils/format'

const props = defineProps({ projectKey: { type: String, required: true } })
const emit = defineEmits(['open'])

const activity = createResource({
	url: 'projex.api.get_activity',
	makeParams: () => ({ project: props.projectKey, limit: 200 }),
	auto: true,
})
watch(() => props.projectKey, () => activity.reload())

const rows = computed(() => activity.data || [])

function dayKey(iso) {
	return new Date(iso).toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })
}
const grouped = computed(() => {
	const out = []
	let cur = null
	for (const r of rows.value) {
		const k = dayKey(r.creation)
		if (!cur || cur.day !== k) {
			cur = { day: k, items: [] }
			out.push(cur)
		}
		cur.items.push(r)
	}
	return out
})
</script>

<template>
	<div class="pjx-changelog">
		<div class="pjx-cl__intro">
			<Icon name="history" :size="15" />
			<span>Every change in this project — status moves, edits, comments and new tasks. Use it as the project change-management record.</span>
		</div>

		<div v-for="g in grouped" :key="g.day" class="pjx-cl__group">
			<div class="pjx-cl__day">{{ g.day }}</div>
			<div
				v-for="a in g.items"
				:key="a.name"
				class="pjx-cl__row"
				:class="{ 'is-link': a.issue }"
				@click="a.issue && emit('open', a.issue)"
			>
				<Avatar :label="a.actor_name" size="sm" />
				<span class="pjx-cl__txt">
					<strong>{{ a.actor_name }}</strong>
					{{ a.action }}<template v-if="a.detail"> · {{ a.detail }}</template>
					<span v-if="a.issue_id" class="pjx-id" style="margin-left: 6px">{{ a.issue_id }}</span>
				</span>
				<span class="pjx-cl__when">{{ relativeTime(a.creation) }} ago</span>
			</div>
		</div>
		<div v-if="!rows.length" class="pjx-cl__empty">No activity recorded yet.</div>
	</div>
</template>

<style scoped>
.pjx-changelog { padding: 16px; overflow-y: auto; max-width: 820px; }
.pjx-cl__intro { display: flex; align-items: center; gap: 8px; padding: 10px 12px; margin-bottom: 14px; border-radius: 8px; background: var(--surface-gray-1); font-size: 12px; color: var(--ink-gray-6); }
.pjx-cl__day { font-size: 13px; font-weight: 500; color: var(--ink-gray-6); margin: 16px 0 4px; }
.pjx-cl__row { display: flex; align-items: center; gap: 10px; padding: 7px 10px; margin: 0 -10px; border-radius: 8px; font-size: 13px; color: var(--ink-gray-7); }
.pjx-cl__row.is-link { cursor: pointer; }
.pjx-cl__row.is-link:hover { background: var(--surface-gray-1); }
.pjx-cl__txt { flex: 1; }
.pjx-cl__txt strong { color: var(--ink-gray-9); font-weight: 500; }
.pjx-cl__when { font-size: 12px; color: var(--ink-gray-4); white-space: nowrap; }
.pjx-cl__empty { padding: 30px 10px; color: var(--ink-gray-4); font-size: 13px; }
</style>
