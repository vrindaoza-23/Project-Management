<script setup>
import { computed, watch } from 'vue'
import { createResource } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import { formatMoney, dueLabel } from '@/utils/format'

const props = defineProps({ projectKey: { type: String, required: true } })

const fin = createResource({
	url: 'projex.api.get_project_finance',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
watch(() => props.projectKey, () => fin.reload())

const available = computed(() => fin.data?.available)
const s = computed(() => fin.data?.summary || {})
const currency = computed(() => fin.data?.currency || 'USD')
const invoices = computed(() => fin.data?.invoices || [])
const money = (n) => formatMoney(n, currency.value)
const marginPositive = computed(() => (s.value.gross_margin || 0) >= 0)
</script>

<template>
	<div class="pjx-fin">
		<template v-if="available">
			<!-- Headline margin -->
			<div class="pjx-fin__hero" :class="{ neg: !marginPositive }">
				<div>
					<div class="pjx-fin__herolbl">Gross margin</div>
					<div class="pjx-fin__heronum">{{ money(s.gross_margin) }}</div>
				</div>
				<div class="pjx-fin__pct">{{ s.per_gross_margin ?? 0 }}<small>%</small></div>
			</div>

			<div class="pjx-cards">
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ money(s.total_billed_amount) }}</div><div class="pjx-statcard__s">Revenue (billed)</div></div></div>
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ money(s.total_sales_amount) }}</div><div class="pjx-statcard__s">Sales ordered</div></div></div>
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ money(s.total_costing_amount) }}</div><div class="pjx-statcard__s">Cost (timesheets)</div></div></div>
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ money(s.total_purchase_cost) }}</div><div class="pjx-statcard__s">Purchase cost</div></div></div>
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ money(s.total_billable_amount) }}</div><div class="pjx-statcard__s">Billable value</div></div></div>
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ money(s.estimated_costing) }}</div><div class="pjx-statcard__s">Estimated cost</div></div></div>
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ s.actual_time ?? 0 }}<small> h</small></div><div class="pjx-statcard__s">Actual time</div></div></div>
				<div class="pjx-statcard"><div><div class="pjx-statcard__n">{{ s.percent_complete ?? 0 }}<small>%</small></div><div class="pjx-statcard__s">Complete</div></div></div>
			</div>

			<div class="pjx-panel">
				<div class="pjx-panel__h">Sales invoices</div>
				<a
					v-for="inv in invoices"
					:key="inv.name"
					class="pjx-fin__inv is-link"
					:href="`/app/sales-invoice/${encodeURIComponent(inv.name)}`"
					target="_blank"
					rel="noopener"
					title="Open in ERPNext"
				>
					<span class="pjx-id">{{ inv.name }}</span>
					<span class="pjx-dim t-xs">{{ inv.posting_date ? dueLabel(inv.posting_date) : '' }}</span>
					<span class="pjx-badge" :data-st="inv.status">{{ inv.status }}</span>
					<span style="flex: 1" />
					<span v-if="inv.outstanding_amount" class="pjx-dim t-xs">due {{ money(inv.outstanding_amount) }}</span>
					<span class="pjx-fin__invtot">{{ money(inv.grand_total) }}</span>
					<Icon name="external-link" :size="13" class="ink-4" />
				</a>
				<div v-if="!invoices.length" class="pjx-dim t-sm">No sales invoices linked to this project yet.</div>
			</div>
			<div class="pjx-dim t-xs" style="padding: 0 2px">Figures roll up from the linked ERPNext Project ({{ fin.data.erpnext_project }}).</div>
		</template>

		<div v-else class="pjx-fin__empty">
			<Icon name="wallet" :size="28" class="ink-4" />
			<h3>No financials yet</h3>
			<p v-if="fin.data && !fin.data.erpnext">Project accounting needs ERPNext installed.</p>
			<p v-else>Link this project to an ERPNext Project in <strong>Settings → ERPNext</strong>. Cost, revenue and gross margin then roll up here automatically.</p>
		</div>
	</div>
</template>

<style scoped>
.pjx-fin { padding: 16px; overflow-y: auto; }
.pjx-fin__hero { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px 20px; border-radius: 12px; background: var(--surface-green-2); color: var(--ink-green-3); margin-bottom: 12px; }
.pjx-fin__hero.neg { background: var(--surface-red-2); color: var(--ink-red-3); }
.pjx-fin__herolbl { font-size: 12px; font-weight: 600; opacity: 0.8; text-transform: uppercase; letter-spacing: 0.04em; }
.pjx-fin__heronum { font-size: 30px; font-weight: 700; }
.pjx-fin__pct { font-size: 40px; font-weight: 700; }
.pjx-fin__pct small { font-size: 18px; font-weight: 500; }
.pjx-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 12px; }
.pjx-statcard { border: 1px solid var(--outline-gray-1); border-radius: 10px; padding: 14px; background: var(--surface-white); }
.pjx-statcard__n { font-size: 20px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-statcard__n small { font-size: 13px; font-weight: 400; color: var(--ink-gray-5); }
.pjx-statcard__s { font-size: 12px; color: var(--ink-gray-5); margin-top: 2px; }
.pjx-panel { border: 1px solid var(--outline-gray-1); border-radius: 10px; padding: 14px; background: var(--surface-white); margin-bottom: 10px; }
.pjx-panel__h { font-size: 14px; font-weight: 600; color: var(--ink-gray-9); margin-bottom: 10px; }
.pjx-fin__inv { display: flex; align-items: center; gap: 10px; font-size: 13px; padding: 7px 6px; border-bottom: 1px solid var(--outline-gray-1); border-radius: 6px; }
.pjx-fin__inv.is-link { cursor: pointer; text-decoration: none; color: inherit; }
.pjx-fin__inv.is-link:hover { background: var(--surface-gray-1); }
.pjx-fin__invtot { font-weight: 600; color: var(--ink-gray-9); font-variant-numeric: tabular-nums; }
.pjx-id { font-size: 12px; color: var(--ink-gray-5); font-variant-numeric: tabular-nums; }
.pjx-badge { font-size: 11px; padding: 1px 8px; border-radius: 999px; background: var(--surface-gray-2); color: var(--ink-gray-7); }
.pjx-badge[data-st='Paid'] { background: var(--surface-green-2); color: var(--ink-green-3); }
.pjx-badge[data-st='Overdue'] { background: var(--surface-red-2); color: var(--ink-red-3); }
.pjx-fin__empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; min-height: 300px; text-align: center; color: var(--ink-gray-6); }
.pjx-fin__empty h3 { font-size: 15px; font-weight: 600; color: var(--ink-gray-8); }
.pjx-fin__empty p { font-size: 13px; color: var(--ink-gray-5); max-width: 380px; }
.pjx-dim { color: var(--ink-gray-5); }
</style>
