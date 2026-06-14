<script setup>
import { computed } from 'vue'
import { createResource } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import { openPalette } from '@/data/ui'

const res = createResource({ url: 'projex.api.get_roadmap', auto: true })

// Map seeded cycle dates onto a coarse 3-quarter track (relative positions).
const bars = computed(() => {
	const rows = res.data || []
	const dates = rows.flatMap((r) => [r.start_date, r.end_date]).filter(Boolean).map((d) => new Date(d).getTime())
	const min = dates.length ? Math.min(...dates) : 0
	const max = dates.length ? Math.max(...dates) : 1
	const span = Math.max(1, max - min)
	return rows.map((r) => {
		const s = r.start_date ? (new Date(r.start_date).getTime() - min) / span : 0.05
		const e = r.end_date ? (new Date(r.end_date).getTime() - min) / span : 0.4
		return { ...r, left: s * 100, width: Math.max(8, (e - s) * 100) }
	})
})
</script>

<template>
	<div class="pjx-main">
		<PageHeader :crumbs="[{ label: 'Roadmap', icon: 'map' }]" @search="openPalette" />
		<div class="pjx-view">
			<div class="pjx-roadmap">
				<div class="pjx-roadmap__head">
					<div></div>
					<div class="pjx-roadmap__q">Q1</div>
					<div class="pjx-roadmap__q">Q2</div>
					<div class="pjx-roadmap__q">Q3</div>
				</div>
				<div class="pjx-roadmap__grid">
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
