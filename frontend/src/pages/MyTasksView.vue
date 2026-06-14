<script setup>
import { computed } from 'vue'
import { createResource } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import PriorityBars from '@/components/PriorityBars.vue'
import { openPalette } from '@/data/ui'
import { dueLabel, isToday } from '@/utils/format'

const res = createResource({ url: 'projex.api.get_my_issues', auto: true })

const GROUPS = [
	{ id: 'today', label: 'Today' },
	{ id: 'week', label: 'This week' },
	{ id: 'later', label: 'Later' },
	{ id: 'done', label: 'Recently done' },
]
const groups = computed(() =>
	GROUPS.map((g) => ({ ...g, items: (res.data && res.data[g.id]) || [] })).filter((g) => g.items.length),
)
</script>

<template>
	<div class="pjx-main">
		<PageHeader :crumbs="[{ label: 'My tasks', icon: 'circle-check-big' }]" @search="openPalette" />
		<div class="pjx-view">
			<div class="pjx-list">
				<div v-for="g in groups" :key="g.id">
					<div class="pjx-grouphead">
						<span class="pjx-grouphead__name">{{ g.label }}</span>
						<span class="pjx-grouphead__count">{{ g.items.length }}</span>
					</div>
					<div v-for="it in g.items" :key="it.name" class="pjx-row">
						<span class="pjx-cell"><PriorityBars :priority="it.priority" /></span>
						<span class="pjx-cell pjx-titlecell">
							<span class="pjx-id">{{ it.issue_id }}</span>
							<span class="pjx-title">{{ it.title }}</span>
						</span>
						<span class="pjx-cell"><span class="pjx-dim t-xs">{{ it.project }}</span></span>
						<span class="pjx-cell r"
							><span v-if="it.due_date" class="pjx-due" :class="{ 'is-today': isToday(it.due_date) }">{{
								dueLabel(it.due_date)
							}}</span></span
						>
					</div>
				</div>
				<div v-if="!res.loading && !groups.length" class="pjx-soon" style="height: 280px">
					<span class="pjx-soon__icon"><Icon name="circle-check-big" :size="20" /></span>
					<div class="t-base ink-7" style="font-weight: 500">Nothing assigned</div>
					<div class="t-sm ink-4">Tasks assigned to you will appear here.</div>
				</div>
			</div>
		</div>
	</div>
</template>
