<script setup>
import { ref, computed, watch } from 'vue'
import { createResource } from 'frappe-ui'
import Icon from './Icon.vue'
import SelectField from './SelectField.vue'

const props = defineProps({ projectKey: { type: String, required: true } })
const emit = defineEmits(['open'])

const selected = ref(null)
const review = createResource({
	url: 'projex.api.get_sprint_review',
	makeParams: () => ({ project: props.projectKey, cycle: selected.value || undefined }),
	auto: true,
})
watch(() => props.projectKey, () => { selected.value = null; review.reload() })
watch(selected, () => review.reload())

const r = computed(() => review.data || {})
const cycleOptions = computed(() => (r.value.cycles || []).map((c) => ({ value: c.name, label: c.cycle_name })))
const issuePct = computed(() => (r.value.total_issues ? Math.round((r.value.done_issues / r.value.total_issues) * 100) : 0))
const ptsPct = computed(() => (r.value.total_points ? Math.round((r.value.done_points / r.value.total_points) * 100) : 0))
</script>

<template>
	<div>
		<div class="pjx-sr__top">
			<div class="pjx-sr__h">Sprint review</div>
			<div style="width: 180px">
				<SelectField
					:options="cycleOptions"
					:model-value="selected || r.cycle"
					placeholder="Select sprint"
					@change="(v) => (selected = v)"
				/>
			</div>
		</div>

		<div v-if="!r.cycle" class="pjx-sr__empty">No sprints yet — create one in the Backlog tab.</div>
		<template v-else>
			<div class="pjx-sr__stats">
				<div class="pjx-sr__stat">
					<div class="pjx-sr__big">{{ r.done_issues }}/{{ r.total_issues }}</div>
					<div class="pjx-sr__lbl">issues done ({{ issuePct }}%)</div>
				</div>
				<div class="pjx-sr__stat">
					<div class="pjx-sr__big">{{ r.done_points }}/{{ r.total_points }}</div>
					<div class="pjx-sr__lbl">points done ({{ ptsPct }}%)</div>
				</div>
				<div class="pjx-sr__stat">
					<div class="pjx-sr__big">{{ (r.carryover || []).length }}</div>
					<div class="pjx-sr__lbl">carryover</div>
				</div>
				<div class="pjx-sr__statestamp">
					<span class="pjx-sr__state">{{ r.state }}</span>
					<span class="pjx-dim t-xs">{{ r.start_date }} → {{ r.end_date }}</span>
				</div>
			</div>

			<div class="pjx-sr__cols">
				<div>
					<div class="pjx-sr__colh"><Icon name="circle-check-big" :size="14" /> Completed ({{ (r.completed || []).length }})</div>
					<div v-for="i in r.completed || []" :key="i.name" class="pjx-sr__row" @click="emit('open', i.name)">
						<span class="pjx-id">{{ i.issue_id }}</span>
						<span class="pjx-sr__t">{{ i.title }}</span>
						<span v-if="i.estimate" class="pjx-pts">{{ i.estimate }}</span>
					</div>
					<div v-if="!(r.completed || []).length" class="pjx-dim t-sm" style="padding: 6px">Nothing completed yet.</div>
				</div>
				<div>
					<div class="pjx-sr__colh"><Icon name="circle-dot" :size="14" /> Carryover ({{ (r.carryover || []).length }})</div>
					<div v-for="i in r.carryover || []" :key="i.name" class="pjx-sr__row" @click="emit('open', i.name)">
						<span class="pjx-id">{{ i.issue_id }}</span>
						<span class="pjx-sr__t">{{ i.title }}</span>
						<span v-if="i.estimate" class="pjx-pts">{{ i.estimate }}</span>
					</div>
					<div v-if="!(r.carryover || []).length" class="pjx-dim t-sm" style="padding: 6px">All work completed. 🎉</div>
				</div>
			</div>
		</template>
	</div>
</template>

<style scoped>
.pjx-sr__top { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
/* Matches the ECharts title spec so hand-built and chart panels read as one family. */
.pjx-sr__h { font-size: 14px; font-weight: 500; color: var(--ink-gray-8); }
.pjx-sr__empty { padding: 20px 4px; color: var(--ink-gray-4); font-size: 13px; }
.pjx-sr__stats { display: flex; gap: 24px; align-items: center; padding: 8px 0 14px; flex-wrap: wrap; }
.pjx-sr__big { font-size: 26px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-sr__lbl { font-size: 12px; color: var(--ink-gray-5); }
.pjx-sr__statestamp { margin-left: auto; display: flex; flex-direction: column; align-items: flex-end; gap: 3px; }
.pjx-sr__state { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; background: var(--surface-gray-3); color: var(--ink-gray-7); }
.pjx-sr__cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.pjx-sr__colh { display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; color: var(--ink-gray-6); margin-bottom: 6px; }
.pjx-sr__row { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.pjx-sr__row:hover { background: var(--surface-gray-1); }
.pjx-sr__t { flex: 1; color: var(--ink-gray-8); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pjx-pts { min-width: 20px; height: 18px; padding: 0 6px; display: inline-grid; place-items: center; border-radius: 5px; background: var(--surface-gray-2); font-size: 11px; font-weight: 600; color: var(--ink-gray-7); }
@media (max-width: 900px) { .pjx-sr__cols { grid-template-columns: 1fr; } }
</style>
