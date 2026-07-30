<script setup>
// Espresso stat row: one bordered surface, KPIs split by hairline dividers.
// Follows frappe-ui's NumberChart idiom — muted label on top, restrained 24px
// value below (not a shouty near-black number). items: [{ label, value, suffix? }].
defineProps({ items: { type: Array, default: () => [] } })
</script>

<template>
	<div class="pjx-kpis">
		<div v-for="k in items" :key="k.label" class="pjx-kpi">
			<span class="pjx-kpi__l">{{ k.label }}</span>
			<span class="pjx-kpi__v">{{ k.value }}<span v-if="k.suffix" class="pjx-kpi__s">{{ k.suffix }}</span></span>
		</div>
	</div>
</template>

<style scoped>
.pjx-kpis { display: flex; align-items: stretch; border: 1px solid var(--outline-gray-1); border-radius: 10px; background: var(--surface-white); overflow: hidden; }
.pjx-kpi { flex: 1; display: flex; flex-direction: column; gap: 4px; padding: 14px 20px; border-inline-start: 1px solid var(--outline-gray-1); }
.pjx-kpi:first-child { border-inline-start: 0; }
.pjx-kpi__l { font-size: 13px; font-weight: 500; color: var(--ink-gray-5); letter-spacing: 0.02em; }
.pjx-kpi__v { font-size: 24px; font-weight: 600; line-height: 1.15; color: var(--ink-gray-8); font-variant-numeric: tabular-nums; letter-spacing: 0.005em; }
.pjx-kpi__s { font-size: 15px; font-weight: 500; color: var(--ink-gray-5); margin-inline-start: 2px; }
@media (max-width: 900px) {
	.pjx-kpis { flex-wrap: wrap; }
	.pjx-kpi { flex: 1 0 40%; border-top: 1px solid var(--outline-gray-1); }
	.pjx-kpi:first-child, .pjx-kpi:nth-child(2) { border-top: 0; }
	.pjx-kpi:nth-child(odd) { border-inline-start: 0; }
}
</style>
