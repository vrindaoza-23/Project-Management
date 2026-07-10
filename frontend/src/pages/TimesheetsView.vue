<script setup>
import { computed, ref, watch } from 'vue'
import { createResource, Button } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import TimesheetLogDialog from '@/components/TimesheetLogDialog.vue'
import { openDrawer } from '@/data/ui'
import { dueLabel } from '@/utils/format'
import { notify, notifyError, confirm } from '@/utils/feedback'

const props = defineProps({ projectKey: { type: String, required: true } })

const ts = createResource({
	url: 'projex.api.get_project_timesheets',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
const remover = createResource({ url: 'projex.api.delete_time_log' })
watch(() => props.projectKey, () => ts.reload())

const logOpen = ref(false)

const auto = computed(() => ts.data?.auto || { per_status: [], avg_lead_days: 0, avg_cycle_days: 0, completed: 0 })
const logged = computed(() => ts.data?.logged || { total_hours: 0, billable_hours: 0, by_user: [], by_issue: [], entries: [] })
const maxStatus = computed(() => Math.max(1, ...auto.value.per_status.map((s) => s.avg_days)))

async function removeEntry(e) {
	const ok = await confirm({
		title: 'Delete time entry',
		message: 'This time entry will be permanently deleted.',
		confirmLabel: 'Delete',
		theme: 'red',
	})
	if (!ok) return
	try {
		await remover.submit({ name: e.name })
		ts.reload()
		notify.success('Time entry deleted')
	} catch (err) {
		notifyError(err, 'Could not delete time entry')
	}
}
</script>

<template>
	<div class="pjx-ts">
		<!-- Flow time: native, always available -->
		<div class="pjx-cards">
			<div class="pjx-statcard">
				<span class="pjx-statcard__ic"><Icon name="timer" :size="18" /></span>
				<div><div class="pjx-statcard__n">{{ auto.avg_lead_days }}<small> d</small></div><div class="pjx-statcard__s">avg lead time (created → done)</div></div>
			</div>
			<div class="pjx-statcard">
				<span class="pjx-statcard__ic"><Icon name="gauge" :size="18" /></span>
				<div><div class="pjx-statcard__n">{{ auto.avg_cycle_days }}<small> d</small></div><div class="pjx-statcard__s">avg cycle time (started → done)</div></div>
			</div>
			<div class="pjx-statcard">
				<span class="pjx-statcard__ic"><Icon name="check-check" :size="18" /></span>
				<div><div class="pjx-statcard__n">{{ auto.completed }}</div><div class="pjx-statcard__s">completed tasks measured</div></div>
			</div>
		</div>

		<div class="pjx-panel">
			<div class="pjx-panel__h">Average time in each status <span class="pjx-dim t-xs">— how long tasks wait before moving on</span></div>
			<div v-for="s in auto.per_status" :key="s.status_name" class="pjx-mrow">
				<span style="flex: 1">{{ s.status_name }}</span>
				<span class="pjx-dim t-xs">{{ s.moves }} moves</span>
				<div class="pjx-mrow__bar"><span :style="{ width: (s.avg_days / maxStatus) * 100 + '%' }" /></div>
				<span class="pjx-ts__d">{{ s.avg_days }}d</span>
			</div>
			<div v-if="!auto.per_status.length" class="pjx-dim t-sm">Not enough status history yet — move some tasks across columns to build flow data.</div>
		</div>

		<!-- Logged time: native Projex Time Log (created in-app) -->
		<div class="pjx-panel">
			<div class="pjx-panel__h" style="display: flex; align-items: center; justify-content: space-between">
				<span>Logged time</span>
				<Button variant="solid" theme="gray" size="sm" @click="logOpen = true">
					<template #prefix><Icon name="plus" :size="13" /></template>Log time
				</Button>
			</div>
			<div class="pjx-cards">
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ logged.total_hours }}<small> h</small></div><div class="pjx-statcard__s">total logged</div></div></div>
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ logged.billable_hours }}<small> h</small></div><div class="pjx-statcard__s">billable</div></div></div>
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ logged.by_user.length }}</div><div class="pjx-statcard__s">people logging</div></div></div>
			</div>
			<div class="pjx-ts__grid">
				<div>
					<div class="pjx-ts__h">Hours by person</div>
					<div v-for="u in logged.by_user" :key="u.user" class="pjx-mrow">
						<span style="flex: 1">{{ u.name }}</span>
						<span class="pjx-dim">{{ u.hours }}h</span>
					</div>
					<div v-if="!logged.by_user.length" class="pjx-dim t-sm">No time logged yet.</div>
					<div class="pjx-ts__h" style="margin-top: 14px">Hours by task</div>
					<div v-for="b in logged.by_issue" :key="b.issue_id" class="pjx-mrow">
						<span class="pjx-id">{{ b.issue_id }}</span>
						<span style="flex: 1" />
						<span class="pjx-dim">{{ b.hours }}h</span>
					</div>
					<div v-if="!logged.by_issue.length" class="pjx-dim t-sm">No task-tagged time yet.</div>
				</div>
				<div>
					<div class="pjx-ts__h">Recent entries</div>
					<div v-for="e in logged.entries.slice(0, 25)" :key="e.name" class="pjx-ts__entry">
						<span class="pjx-id is-link" title="Open task" @click="openDrawer(e.issue)">{{ e.issue_id }}</span>
						<span class="pjx-ts__by">{{ e.by }}</span>
						<span class="pjx-dim t-xs" style="flex: 1">{{ e.spent_on ? dueLabel(e.spent_on) : '' }}<template v-if="e.activity"> &middot; {{ e.activity }}</template></span>
						<span v-if="e.billable" class="pjx-badge">billable</span>
						<span class="pjx-dim">{{ e.hours }}h</span>
						<button class="pjx-ts__x" title="Delete" @click="removeEntry(e)"><Icon name="x" :size="13" /></button>
					</div>
					<div v-if="!logged.entries.length" class="pjx-dim t-sm">No time logged yet — click “Log time”.</div>
				</div>
			</div>
		</div>

		<TimesheetLogDialog :open="logOpen" :project-key="projectKey" @close="logOpen = false" @logged="ts.reload()" />
	</div>
</template>

<style scoped>
.pjx-ts { padding: 16px; overflow-y: auto; }
.pjx-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 12px; }
.pjx-statcard { display: flex; align-items: center; gap: 12px; border: 1px solid var(--outline-gray-1); border-radius: 10px; padding: 14px; background: var(--surface-white); }
.pjx-statcard__ic { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 9px; background: var(--surface-gray-2); color: var(--ink-gray-7); }
.pjx-statcard__n { font-size: 22px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-statcard__n small { font-size: 13px; font-weight: 400; color: var(--ink-gray-5); }
.pjx-statcard__s { font-size: 12px; color: var(--ink-gray-5); }
.pjx-panel { border: 1px solid var(--outline-gray-1); border-radius: 10px; padding: 14px; background: var(--surface-white); margin-bottom: 12px; }
.pjx-panel__h { font-size: 14px; font-weight: 600; color: var(--ink-gray-9); margin-bottom: 10px; }
.pjx-mrow { display: flex; align-items: center; gap: 10px; font-size: 13px; padding: 5px 0; color: var(--ink-gray-8); }
.pjx-mrow__bar { width: 160px; height: 6px; border-radius: 3px; background: var(--surface-gray-2); overflow: hidden; }
.pjx-mrow__bar span { display: block; height: 100%; background: var(--blue-500); }
.pjx-ts__d { width: 44px; text-align: right; font-variant-numeric: tabular-nums; color: var(--ink-gray-7); }
.pjx-ts__grid { display: grid; grid-template-columns: 1fr 1.4fr; gap: 18px; margin-top: 12px; }
.pjx-ts__h { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--ink-gray-5); margin-bottom: 6px; }
.pjx-ts__entry { display: flex; align-items: center; gap: 8px; font-size: 13px; padding: 5px 6px; border-bottom: 1px solid var(--outline-gray-1); border-radius: 6px; }
.pjx-ts__entry.is-link { cursor: pointer; text-decoration: none; color: inherit; }
.pjx-ts__entry.is-link:hover { background: var(--surface-gray-1); }
.pjx-ts__by { color: var(--ink-gray-7); }
.pjx-id.is-link { cursor: pointer; }
.pjx-id.is-link:hover { color: var(--ink-gray-8); text-decoration: underline; }
.pjx-ts__x { border: 0; background: transparent; cursor: pointer; color: var(--ink-gray-4); display: grid; place-items: center; padding: 2px; border-radius: 5px; }
.pjx-ts__x:hover { background: var(--surface-gray-3); color: var(--ink-gray-7); }
.pjx-id { font-size: 12px; color: var(--ink-gray-5); font-variant-numeric: tabular-nums; }
.pjx-badge { font-size: 11px; padding: 1px 7px; border-radius: 999px; background: var(--surface-green-2); color: var(--ink-green-3); }
.pjx-dim { color: var(--ink-gray-5); }
</style>
