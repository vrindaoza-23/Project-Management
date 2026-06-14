<script setup>
import { ref, computed } from 'vue'
import Icon from '@/components/Icon.vue'
import StatusDot from '@/components/StatusDot.vue'

const props = defineProps({
	issues: { type: Array, default: () => [] },
	statuses: { type: Array, default: () => [] },
})
const emit = defineEmits(['open'])

const cursor = ref(new Date())
const statusById = computed(() => Object.fromEntries(props.statuses.map((s) => [s.name, s])))

const monthLabel = computed(() =>
	cursor.value.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }),
)

// Build a 6-week grid starting on Sunday.
const weeks = computed(() => {
	const first = new Date(cursor.value.getFullYear(), cursor.value.getMonth(), 1)
	const start = new Date(first)
	start.setDate(first.getDate() - first.getDay())
	const byDay = {}
	for (const it of props.issues) {
		if (!it.due_date) continue
		;(byDay[it.due_date] ||= []).push(it)
	}
	const grid = []
	const d = new Date(start)
	for (let w = 0; w < 6; w++) {
		const row = []
		for (let i = 0; i < 7; i++) {
			const iso = d.toISOString().slice(0, 10)
			row.push({
				date: new Date(d),
				iso,
				inMonth: d.getMonth() === cursor.value.getMonth(),
				isToday: iso === new Date().toISOString().slice(0, 10),
				items: byDay[iso] || [],
			})
			d.setDate(d.getDate() + 1)
		}
		grid.push(row)
	}
	return grid
})

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
function move(delta) {
	cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}
function today() {
	cursor.value = new Date()
}
</script>

<template>
	<div class="pjx-cal">
		<div class="pjx-cal__bar">
			<button class="pjx-cal__nav" @click="move(-1)"><Icon name="chevron-left" :size="16" /></button>
			<span class="pjx-cal__month">{{ monthLabel }}</span>
			<button class="pjx-cal__nav" @click="move(1)"><Icon name="chevron-right" :size="16" /></button>
			<button class="pjx-cal__today" @click="today">Today</button>
		</div>
		<div class="pjx-cal__dow">
			<span v-for="d in DOW" :key="d">{{ d }}</span>
		</div>
		<div class="pjx-cal__grid">
			<div v-for="(week, wi) in weeks" :key="wi" class="pjx-cal__week">
				<div
					v-for="cell in week"
					:key="cell.iso"
					class="pjx-cal__cell"
					:class="{ 'is-out': !cell.inMonth }"
				>
					<div class="pjx-cal__date" :class="{ 'is-today': cell.isToday }">{{ cell.date.getDate() }}</div>
					<button
						v-for="it in cell.items.slice(0, 3)"
						:key="it.name"
						class="pjx-cal__chip"
						@click="emit('open', it.name)"
					>
						<StatusDot :status="statusById[it.status]" :size="7" />
						<span class="truncate">{{ it.issue_id }} {{ it.title }}</span>
					</button>
					<span v-if="cell.items.length > 3" class="pjx-cal__more">+{{ cell.items.length - 3 }} more</span>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-cal { display: flex; flex-direction: column; height: 100%; padding: 12px 16px; }
.pjx-cal__bar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.pjx-cal__nav { border: 1px solid var(--outline-gray-2); background: var(--surface-white); border-radius: 7px; width: 28px; height: 28px; display: grid; place-items: center; cursor: pointer; color: var(--ink-gray-7); }
.pjx-cal__nav:hover { background: var(--surface-gray-2); }
.pjx-cal__month { font-size: 15px; font-weight: 600; min-width: 160px; }
.pjx-cal__today { margin-left: 6px; border: 1px solid var(--outline-gray-2); background: var(--surface-white); border-radius: 7px; height: 28px; padding: 0 10px; font-size: 13px; cursor: pointer; }
.pjx-cal__dow { display: grid; grid-template-columns: repeat(7, 1fr); font-size: 11px; color: var(--ink-gray-5); padding-bottom: 4px; }
.pjx-cal__grid { flex: 1; display: flex; flex-direction: column; border: 1px solid var(--outline-gray-1); border-radius: 10px; overflow: hidden; }
.pjx-cal__week { flex: 1; display: grid; grid-template-columns: repeat(7, 1fr); }
.pjx-cal__cell { border-right: 1px solid var(--outline-gray-1); border-bottom: 1px solid var(--outline-gray-1); padding: 4px 5px; min-height: 92px; overflow: hidden; display: flex; flex-direction: column; gap: 2px; }
.pjx-cal__cell.is-out { background: var(--surface-gray-1); }
.pjx-cal__date { font-size: 12px; color: var(--ink-gray-6); align-self: flex-start; width: 22px; height: 22px; display: grid; place-items: center; border-radius: 9999px; }
.pjx-cal__date.is-today { background: var(--blue-500); color: #fff; font-weight: 600; }
.pjx-cal__chip { display: flex; align-items: center; gap: 5px; background: var(--surface-gray-2); border: 0; border-radius: 5px; padding: 2px 6px; font-size: 11px; color: var(--ink-gray-8); cursor: pointer; text-align: left; width: 100%; }
.pjx-cal__chip:hover { background: var(--surface-gray-3); }
.pjx-cal__more { font-size: 10px; color: var(--ink-gray-5); padding-left: 4px; }
</style>
