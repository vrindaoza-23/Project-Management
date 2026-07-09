<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import Icon from './Icon.vue'
import { store } from '@/data/store'
import { openDrawer } from '@/data/ui'
import { setTweak, tweaks } from '@/composables/useTweaks'

const issueSearch = createResource({ url: 'frappe.client.get_list' })
const issueResults = ref([])
let searchTimer = null

const props = defineProps({ open: Boolean })
const emit = defineEmits(['close', 'new'])
const router = useRouter()

const q = ref('')
const inputRef = ref(null)
const listRef = ref(null)
const activeIndex = ref(0)

watch(
	() => props.open,
	(v) => {
		if (v) {
			q.value = ''
			issueResults.value = []
			activeIndex.value = 0
			nextTick(() => inputRef.value?.focus())
		}
	},
)

// Debounced issue search (by title) across accessible projects.
watch(q, (val) => {
	clearTimeout(searchTimer)
	if (!val) {
		issueResults.value = []
		return
	}
	searchTimer = setTimeout(() => {
		issueSearch
			.submit({
				doctype: 'Projex Issue',
				filters: { title: ['like', `%${val}%`] },
				fields: ['name', 'issue_id', 'title'],
				limit_page_length: 8,
			})
			.then((rows) => {
				issueResults.value = rows || []
			})
			.catch(() => {})
	}, 180)
})

const items = computed(() => {
	const out = [
		{ section: 'Jump to', kind: 'route', to: '/inbox', label: 'Inbox', icon: 'inbox', hint: 'G I' },
		{ section: 'Jump to', kind: 'route', to: '/my-tasks', label: 'My tasks', icon: 'circle-check-big', hint: 'G M' },
		{ section: 'Jump to', kind: 'route', to: '/roadmap', label: 'Roadmap', icon: 'map', hint: 'G R' },
	]
	for (const p of store.projects) {
		out.push({ section: 'Projects', kind: 'route', to: `/projects/${p.key}`, label: p.project_name, icon: p.icon || 'folder' })
	}
	for (const it of issueResults.value) {
		out.push({ section: 'Tasks', kind: 'issue', id: it.name, label: it.title, icon: 'square-check-big', hint: it.issue_id })
	}
	out.push({ section: 'Actions', kind: 'action', id: 'new', label: 'Create new task', icon: 'plus', hint: 'C' })
	out.push({
		section: 'Actions', kind: 'action', id: 'theme',
		label: tweaks.dark ? 'Switch to light mode' : 'Switch to dark mode', icon: 'moon',
	})
	if (!q.value) return out.filter((i) => i.section !== 'Tasks').slice(0, 8)
	const qq = q.value.toLowerCase()
	return out
		.filter((i) => i.section === 'Tasks' || i.label.toLowerCase().includes(qq))
		.slice(0, 16)
})

// Grouped by section for display, but each row carries a running global index
// (`gi`) so a single activeIndex can drive keyboard highlight across sections.
const grouped = computed(() => {
	const g = {}
	let gi = 0
	for (const it of items.value) (g[it.section] ||= []).push({ ...it, gi: gi++ })
	return g
})

const flatItems = computed(() => items.value)

// Keep the highlight in range as results change under the cursor.
watch(flatItems, (list) => {
	if (activeIndex.value >= list.length) activeIndex.value = Math.max(0, list.length - 1)
})

function move(delta) {
	const n = flatItems.value.length
	if (!n) return
	activeIndex.value = (activeIndex.value + delta + n) % n
	nextTick(() => {
		listRef.value?.querySelector('.pjx-cmdk__row.is-active')?.scrollIntoView({ block: 'nearest' })
	})
}

function chooseActive() {
	const item = flatItems.value[activeIndex.value]
	if (item) choose(item)
}

function choose(item) {
	emit('close')
	if (item.kind === 'route') router.push(item.to)
	else if (item.kind === 'issue') openDrawer(item.id)
	else if (item.kind === 'action' && item.id === 'new') emit('new')
	else if (item.kind === 'action' && item.id === 'theme') setTweak('dark', !tweaks.dark)
}
</script>

<template>
	<div v-if="open" class="pjx-cmdk" @mousedown="emit('close')">
		<div class="pjx-cmdk__box" @mousedown.stop>
			<div class="pjx-cmdk__inputrow">
				<Icon name="search" :size="16" />
				<input
					ref="inputRef"
					v-model="q"
					class="pjx-cmdk__input"
					placeholder="Search projects, jump to views — or type a command"
					@keydown.down.prevent="move(1)"
					@keydown.up.prevent="move(-1)"
					@keydown.enter.prevent="chooseActive"
					@keydown.esc="emit('close')"
				/>
				<span class="kbd">esc</span>
			</div>
			<div ref="listRef" class="pjx-cmdk__list">
				<div v-for="(list, sect) in grouped" :key="sect">
					<div class="pjx-cmdk__sect">{{ sect }}</div>
					<button
						v-for="it in list"
						:key="it.label"
						class="pjx-cmdk__row"
						:class="{ 'is-active': it.gi === activeIndex }"
						@click="choose(it)"
						@mousemove="activeIndex = it.gi"
					>
						<span class="pjx-cmdk__icon"><Icon :name="it.icon" :size="16" /></span>
						<span class="pjx-cmdk__label">{{ it.label }}</span>
						<span v-if="it.hint" class="kbd">{{ it.hint }}</span>
					</button>
				</div>
				<div v-if="items.length === 0" class="pjx-cmdk__empty">No matches for “{{ q }}”.</div>
			</div>
			<div class="pjx-cmdk__foot">
				<span><span class="kbd">↑↓</span> navigate</span>
				<span><span class="kbd">↵</span> open</span>
				<span style="margin-left: auto">Projex</span>
			</div>
		</div>
	</div>
</template>
