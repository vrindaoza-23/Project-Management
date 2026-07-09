<script setup>
import { computed } from 'vue'
import { createResource } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import { openPalette } from '@/data/ui'

const res = createResource({ url: 'projex.api.get_roadmap', auto: true })

const quarterIndex = (d) => Math.floor(d.getMonth() / 3) // 0..3
const startOfQuarter = (d) => new Date(d.getFullYear(), quarterIndex(d) * 3, 1)
const addQuarter = (d) => new Date(d.getFullYear(), d.getMonth() + 3, 1)

// Derive a quarter-aligned timeline from the real cycle dates so the header
// shows the actual quarters spanned (Q2 ’26 …), not fixed Q1/Q2/Q3 labels.
const timeline = computed(() => {
	const rows = res.data || []
	const times = rows
		.flatMap((r) => [r.start_date, r.end_date])
		.filter(Boolean)
		.map((d) => new Date(d).getTime())
	if (!times.length) return { min: 0, span: 1, quarters: [] }

	const min = startOfQuarter(new Date(Math.min(...times))).getTime()
	const max = addQuarter(startOfQuarter(new Date(Math.max(...times)))).getTime()
	const span = Math.max(1, max - min)

	const quarters = []
	for (let d = new Date(min); d.getTime() < max; d = addQuarter(d)) {
		const qs = d.getTime()
		quarters.push({
			key: qs,
			label: `Q${quarterIndex(d) + 1} ’${String(d.getFullYear()).slice(2)}`,
			left: ((qs - min) / span) * 100,
			width: ((addQuarter(d).getTime() - qs) / span) * 100,
		})
	}
	return { min, span, quarters }
})

const bars = computed(() => {
	const { min, span } = timeline.value
	return (res.data || []).map((r) => {
		const s = r.start_date ? ((new Date(r.start_date).getTime() - min) / span) * 100 : 4
		const e = r.end_date ? ((new Date(r.end_date).getTime() - min) / span) * 100 : s + 30
		return { ...r, left: s, width: Math.max(8, e - s) }
	})
})

const loading = computed(() => res.loading && !res.data)
const isEmpty = computed(() => !res.loading && !(res.data || []).length)
const gridStyle = computed(() => ({
	'--pjx-q-step': `${100 / Math.max(1, timeline.value.quarters.length)}%`,
}))
</script>

<template>
	<div class="pjx-main">
		<PageHeader :crumbs="[{ label: 'Roadmap', icon: 'map' }]" @search="openPalette" />
		<div class="pjx-view">
			<div v-if="loading" class="pjx-roadmap__state">
				<Icon name="loader" :size="22" class="ink-4 pjx-spin" />
				<span class="t-sm ink-5">Loading roadmap…</span>
			</div>

			<div v-else-if="isEmpty" class="pjx-roadmap__state">
				<Icon name="map" :size="28" class="ink-4" />
				<div class="t-base ink-7" style="font-weight: 600">No dated cycles yet</div>
				<div class="t-sm ink-5" style="max-width: 340px; text-align: center">
					Add start and end dates to your project cycles to see them plotted on the roadmap.
				</div>
			</div>

			<div v-else class="pjx-roadmap">
				<div class="pjx-roadmap__head">
					<div></div>
					<div class="pjx-roadmap__qtrack">
						<div
							v-for="q in timeline.quarters"
							:key="q.key"
							class="pjx-roadmap__q"
							:style="{ left: q.left + '%', width: q.width + '%' }"
						>
							{{ q.label }}
						</div>
					</div>
				</div>
				<div class="pjx-roadmap__grid" :style="gridStyle">
					<div v-for="b in bars" :key="b.project" class="pjx-roadmap__row">
						<div class="pjx-roadmap__rl">
							<span class="pjx-projicon"><Icon :name="b.icon || 'folder'" :size="12" /></span>
							<span>{{ b.label }}</span>
						</div>
						<div class="pjx-roadmap__track">
							<div
								class="pjx-roadmap__bar"
								:style="{ left: b.left + '%', width: b.width + '%', background: b.color || 'var(--blue-500)' }"
							>
								<span class="pjx-roadmap__barlabel">{{ b.label }}</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
