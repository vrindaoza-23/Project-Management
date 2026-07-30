<script setup>
import { computed, ref, watch } from 'vue'
import { createResource, Button, Badge, AxisChart } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import KpiStrip from '@/components/KpiStrip.vue'
import TimesheetLogDialog from '@/components/TimesheetLogDialog.vue'
import { openDrawer } from '@/data/ui'
import { dueLabel } from '@/utils/format'
import { notify, notifyError, confirm } from '@/utils/feedback'
import { cssColor } from '@/utils/chartColors'

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

// Lead/cycle time only mean something once tasks have completed; show an em
// dash rather than a misleading "0d" when nothing has been measured yet.
const measured = computed(() => (auto.value.completed || 0) > 0)
const flowKpis = computed(() => [
	{ label: 'Avg lead time', value: measured.value ? auto.value.avg_lead_days : '—', suffix: measured.value ? 'd' : '' },
	{ label: 'Avg cycle time', value: measured.value ? auto.value.avg_cycle_days : '—', suffix: measured.value ? 'd' : '' },
	{ label: 'Completed measured', value: auto.value.completed },
])
const loggedKpis = computed(() => [
	{ label: 'Total logged', value: logged.value.total_hours, suffix: 'h' },
	{ label: 'Billable', value: logged.value.billable_hours, suffix: 'h' },
	{ label: 'People logging', value: logged.value.by_user.length },
])

const statusChart = computed(() => ({
	data: auto.value.per_status.map((s) => ({ status: s.status_name, days: s.avg_days })),
	title: 'Average time in each status',
	subtitle: 'Days tasks wait before moving on',
	colors: [cssColor('var(--blue-500)')],
	xAxis: { key: 'status', type: 'category' },
	yAxis: {},
	swapXY: true,
	series: [{ name: 'days', type: 'bar', showDataLabels: true }],
}))

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
		<KpiStrip :items="flowKpis" class="pjx-ts__flow" />

		<div class="pjx-card" :class="auto.per_status.length ? 'pjx-card--chart' : 'pjx-card--list'">
			<AxisChart v-if="auto.per_status.length" :config="statusChart" />
			<template v-else>
				<div class="pjx-card__h">Average time in each status <span class="pjx-card__sub">Days tasks wait before moving on</span></div>
				<div class="pjx-card__empty">Not enough status history yet — move some tasks across columns to build flow data.</div>
			</template>
		</div>

		<!-- Logged time: native Projex Time Log (created in-app) -->
		<div class="pjx-card pjx-card--list">
			<div class="pjx-card__h pjx-card__h--row">
				<span>Logged time</span>
				<Button variant="subtle" theme="gray" size="sm" @click="logOpen = true">
					<template #prefix><Icon name="plus" :size="13" /></template>Log time
				</Button>
			</div>
			<KpiStrip :items="loggedKpis" class="pjx-ts__logged" />
			<div class="pjx-ts__grid">
				<div>
					<div class="pjx-ts__h">Hours by person</div>
					<div v-for="u in logged.by_user" :key="u.user" class="pjx-mrow">
						<span style="flex: 1">{{ u.name }}</span>
						<span class="pjx-dim">{{ u.hours }}h</span>
					</div>
					<div v-if="!logged.by_user.length" class="pjx-card__empty">No time logged yet.</div>
					<div class="pjx-ts__h" style="margin-top: 14px">Hours by task</div>
					<div v-for="b in logged.by_issue" :key="b.issue_id" class="pjx-mrow">
						<span class="pjx-id">{{ b.issue_id }}</span>
						<span style="flex: 1" />
						<span class="pjx-dim">{{ b.hours }}h</span>
					</div>
					<div v-if="!logged.by_issue.length" class="pjx-card__empty">No task-tagged time yet.</div>
				</div>
				<div>
					<div class="pjx-ts__h">Recent entries</div>
					<div v-for="e in logged.entries.slice(0, 25)" :key="e.name" class="pjx-ts__entry">
						<span class="pjx-id is-link" title="Open task" @click="openDrawer(e.issue)">{{ e.issue_id }}</span>
						<span class="pjx-ts__by">{{ e.by }}</span>
						<span class="pjx-dim t-xs" style="flex: 1">{{ e.spent_on ? dueLabel(e.spent_on) : '' }}<template v-if="e.activity"> &middot; {{ e.activity }}</template></span>
						<Badge v-if="e.billable" theme="green" variant="subtle" size="sm">billable</Badge>
						<span class="pjx-dim">{{ e.hours }}h</span>
						<button class="pjx-ts__x" title="Delete" @click="removeEntry(e)"><Icon name="x" :size="13" /></button>
					</div>
					<div v-if="!logged.entries.length" class="pjx-card__empty">No time logged yet — click “Log time”.</div>
				</div>
			</div>
		</div>

		<TimesheetLogDialog :open="logOpen" :project-key="projectKey" @close="logOpen = false" @logged="ts.reload()" />
	</div>
</template>

<style scoped>
.pjx-ts { padding: 16px; overflow-y: auto; letter-spacing: 0.02em; }
.pjx-ts__flow { margin-bottom: 16px; }
.pjx-ts__logged { margin: 4px 0 12px; }
.pjx-card { border: 1px solid var(--outline-gray-1); border-radius: 10px; background: var(--surface-white); overflow: hidden; margin-bottom: 12px; }
.pjx-card--chart { height: 300px; }
.pjx-card--list { padding: 16px 18px; }
.pjx-card__h { font-size: 15px; font-weight: 600; color: var(--ink-gray-8); letter-spacing: 0.005em; margin-bottom: 12px; }
.pjx-card__h--row { display: flex; align-items: center; justify-content: space-between; }
.pjx-card__sub { font-size: 13px; font-weight: 400; color: var(--ink-gray-6); margin-inline-start: 4px; }
.pjx-card__empty { font-size: 13px; color: var(--ink-gray-5); }
.pjx-mrow { display: flex; align-items: center; gap: 10px; font-size: 13px; padding: 5px 0; color: var(--ink-gray-8); }
.pjx-ts__grid { display: grid; grid-template-columns: 1fr 1.4fr; gap: 18px; margin-top: 8px; }
.pjx-ts__h { font-size: 13px; font-weight: 500; color: var(--ink-gray-7); margin-bottom: 6px; }
.pjx-ts__entry { display: flex; align-items: center; gap: 8px; font-size: 13px; padding: 5px 6px; border-bottom: 1px solid var(--outline-gray-1); }
.pjx-ts__entry:last-of-type { border-bottom: 0; }
.pjx-ts__by { color: var(--ink-gray-7); }
.pjx-id.is-link { cursor: pointer; }
.pjx-id.is-link:hover { color: var(--ink-gray-8); text-decoration: underline; }
.pjx-ts__x { border: 0; background: transparent; cursor: pointer; color: var(--ink-gray-4); display: grid; place-items: center; padding: 2px; border-radius: 5px; }
.pjx-ts__x:hover { background: var(--surface-gray-3); color: var(--ink-gray-7); }
.pjx-id { font-size: 12px; color: var(--ink-gray-5); font-variant-numeric: tabular-nums; }
.pjx-dim { color: var(--ink-gray-5); }
@media (max-width: 900px) { .pjx-ts__grid { grid-template-columns: 1fr; } }
</style>
