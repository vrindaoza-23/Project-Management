<script setup>
import { computed, watch } from 'vue'
import { createResource } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import Donut from '@/components/Donut.vue'

const props = defineProps({ projectKey: { type: String, required: true } })

const reports = createResource({
	url: 'projex.api.get_project_reports',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
watch(() => props.projectKey, () => reports.reload())

const distribution = computed(() =>
	(reports.data?.distribution || []).map((d) => ({ status_name: d.label, color_theme: d.color_theme, count: d.count })),
)
const velocity = computed(() => reports.data?.velocity || [])
const throughput = computed(() => reports.data?.throughput || [])
const maxPts = computed(() => Math.max(1, ...velocity.value.map((v) => v.points)))
const maxThru = computed(() => Math.max(1, ...throughput.value.map((t) => t.count)))

function weekLabel(iso) {
	return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
</script>

<template>
	<div class="pjx-reports">
		<div class="pjx-rgrid">
			<div class="pjx-panel">
				<div class="pjx-panel__h">Status distribution</div>
				<div class="flex items-center g-5" style="padding: 8px 4px">
					<Donut :slices="distribution"><template #label><div class="pjx-donut__lbl">tasks</div></template></Donut>
					<div class="flex col g-2" style="flex: 1">
						<div v-for="s in distribution" :key="s.status_name" class="pjx-legend">
							<span style="flex: 1">{{ s.status_name }}</span><span class="pjx-dim">{{ s.count }}</span>
						</div>
					</div>
				</div>
			</div>

			<div class="pjx-panel">
				<div class="pjx-panel__h">Cycle time</div>
				<div class="pjx-bignum">{{ reports.data?.avg_cycle_time ?? 0 }}<span> days avg</span></div>
				<div class="t-sm ink-5">{{ reports.data?.total_completed ?? 0 }} completed tasks measured (created → done)</div>
			</div>

			<div class="pjx-panel">
				<div class="pjx-panel__h">Velocity by cycle</div>
				<div class="pjx-bars">
					<div v-for="v in velocity" :key="v.cycle" class="pjx-bar">
						<div class="pjx-bar__track">
							<div class="pjx-bar__fill" :style="{ height: (v.points / maxPts) * 100 + '%' }" />
						</div>
						<div class="pjx-bar__val">{{ v.points }}</div>
						<div class="pjx-bar__lbl">{{ v.cycle }}</div>
					</div>
					<div v-if="!velocity.length" class="pjx-dim t-sm">No cycles yet.</div>
				</div>
			</div>

			<div class="pjx-panel">
				<div class="pjx-panel__h">Throughput (tasks done / week)</div>
				<div class="pjx-bars">
					<div v-for="t in throughput" :key="t.week" class="pjx-bar">
						<div class="pjx-bar__track">
							<div class="pjx-bar__fill green" :style="{ height: (t.count / maxThru) * 100 + '%' }" />
						</div>
						<div class="pjx-bar__val">{{ t.count }}</div>
						<div class="pjx-bar__lbl">{{ weekLabel(t.week) }}</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-reports { padding: 16px; overflow-y: auto; }
.pjx-rgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pjx-panel { border: 1px solid var(--outline-gray-1); border-radius: 10px; padding: 14px; background: var(--surface-white); }
.pjx-panel__h { font-size: 14px; font-weight: 600; color: var(--ink-gray-9); margin-bottom: 10px; }
.pjx-legend { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ink-gray-8); }
.pjx-bignum { font-size: 36px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-bignum span { font-size: 14px; font-weight: 400; color: var(--ink-gray-5); margin-left: 6px; }
.pjx-bars { display: flex; align-items: flex-end; gap: 14px; height: 160px; padding-top: 8px; }
.pjx-bar { display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1; height: 100%; justify-content: flex-end; }
.pjx-bar__track { width: 28px; flex: 1; display: flex; align-items: flex-end; background: var(--surface-gray-1); border-radius: 6px; overflow: hidden; }
.pjx-bar__fill { width: 100%; background: var(--blue-500); border-radius: 6px 6px 0 0; min-height: 2px; }
.pjx-bar__fill.green { background: var(--green-600); }
.pjx-bar__val { font-size: 12px; font-weight: 500; color: var(--ink-gray-8); }
.pjx-bar__lbl { font-size: 10px; color: var(--ink-gray-5); text-align: center; }
@media (max-width: 900px) { .pjx-rgrid { grid-template-columns: 1fr; } }
</style>
