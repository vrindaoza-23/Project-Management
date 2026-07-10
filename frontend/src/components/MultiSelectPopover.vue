<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
	options: { type: Array, default: () => [] }, // [{ value, label, color, image }]
	modelValue: { type: Array, default: () => [] }, // selected values
	multiple: { type: Boolean, default: true },
	placeholder: { type: String, default: 'Select…' },
	bare: { type: Boolean, default: false }, // borderless (inline rail) styling
})
const emit = defineEmits(['update:modelValue', 'change'])

const open = ref(false)
const q = ref('')
const root = ref(null)
const panel = ref(null)
const searchInput = ref(null)
const panelStyle = ref({})

const filtered = computed(() => {
	const qq = q.value.trim().toLowerCase()
	if (!qq) return props.options
	return props.options.filter((o) => (o.label || '').toLowerCase().includes(qq))
})

function isSelected(v) {
	return props.modelValue.includes(v)
}

function position() {
	const el = root.value
	if (!el) return
	const r = el.getBoundingClientRect()
	const width = Math.max(r.width, 220)
	const belowSpace = window.innerHeight - r.bottom - 12
	const aboveSpace = r.top - 12
	const openUp = belowSpace < 240 && aboveSpace > belowSpace
	const maxHeight = Math.min(340, Math.max(160, openUp ? aboveSpace : belowSpace))
	panelStyle.value = {
		position: 'fixed',
		left: `${Math.min(r.left, window.innerWidth - width - 8)}px`,
		width: `${width}px`,
		maxHeight: `${maxHeight}px`,
		display: 'flex',
		flexDirection: 'column',
		overflow: 'hidden',
		...(openUp
			? { bottom: `${window.innerHeight - r.top + 4}px` }
			: { top: `${r.bottom + 4}px` }),
	}
}

async function toggleOpen() {
	open.value = !open.value
	if (open.value) {
		q.value = ''
		await nextTick()
		position()
		searchInput.value?.focus()
	}
}

function toggle(v) {
	let next
	if (props.multiple) {
		next = isSelected(v) ? props.modelValue.filter((x) => x !== v) : [...props.modelValue, v]
	} else {
		next = isSelected(v) ? [] : [v]
		open.value = false
	}
	emit('update:modelValue', next)
	emit('change', next)
}

function onPointerDown(e) {
	if (root.value?.contains(e.target)) return
	if (panel.value?.contains(e.target)) return
	open.value = false
}
function reposition() {
	if (open.value) position()
}
onMounted(() => {
	document.addEventListener('pointerdown', onPointerDown, true)
	window.addEventListener('resize', reposition)
	window.addEventListener('scroll', reposition, true)
})
onUnmounted(() => {
	document.removeEventListener('pointerdown', onPointerDown, true)
	window.removeEventListener('resize', reposition)
	window.removeEventListener('scroll', reposition, true)
})
</script>

<template>
	<div ref="root" class="pjx-msel" :class="{ 'pjx-msel--bare': bare }">
		<button type="button" class="pjx-msel__trigger" @click="toggleOpen">
			<slot name="trigger">
				<span class="pjx-dim t-xs">{{ placeholder }}</span>
			</slot>
			<Icon name="chevron-down" :size="13" class="ink-4" style="margin-left: auto" />
		</button>

		<Teleport to="body">
			<div v-if="open" ref="panel" class="pjx-msel__panel" :style="panelStyle" @pointerdown.stop>
				<input ref="searchInput" v-model="q" class="pjx-msel__search" placeholder="Search…" @keydown.stop />
				<div class="pjx-msel__list" style="flex: 1; min-height: 0; overflow-y: auto">
					<button
						v-for="o in filtered"
						:key="o.value"
						type="button"
						class="pjx-msel__opt"
						:class="{ 'is-sel': isSelected(o.value) }"
						@click="toggle(o.value)"
					>
						<span v-if="o.color" class="pjx-label__dot" :style="{ background: o.color }" />
						<span class="truncate" style="flex: 1; text-align: left">{{ o.label }}</span>
						<Icon v-if="isSelected(o.value)" name="check" :size="14" />
					</button>
					<div v-if="!filtered.length" class="pjx-msel__empty">No matches</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<style scoped>
.pjx-msel {
	position: relative;
}
.pjx-msel__trigger {
	display: flex;
	align-items: center;
	gap: 6px;
	width: 100%;
	min-height: 28px;
	padding: 3px 8px;
	border-radius: 8px;
	background: var(--surface-gray-2);
	border: 1px solid transparent;
	cursor: pointer;
	text-align: left;
	font-size: 13px;
	color: var(--ink-gray-8);
}
.pjx-msel__trigger:hover {
	background: var(--surface-gray-3);
}
.pjx-msel--bare .pjx-msel__trigger {
	background: transparent;
	padding: 2px 6px;
	min-height: 24px;
}
.pjx-msel--bare .pjx-msel__trigger:hover {
	background: var(--surface-gray-2);
}
</style>

<style>
/* Panel is teleported to body, so its styles are global (not scoped). */
.pjx-msel__panel {
	z-index: var(--z-popover);
	background: var(--surface-modal);
	border: 1px solid var(--outline-gray-2);
	border-radius: 10px;
	box-shadow: var(--shadow-lg);
	padding: 6px;
}
.pjx-msel__panel .pjx-msel__search {
	width: 100%;
	height: 30px;
	border: 0;
	border-bottom: 1px solid var(--outline-gray-1);
	outline: 0;
	background: transparent;
	font-size: 13px;
	padding: 0 6px 6px;
	margin-bottom: 4px;
	color: var(--ink-gray-9);
}
.pjx-msel__panel .pjx-msel__list {
	max-height: 240px;
	overflow-y: auto;
}
.pjx-msel__panel .pjx-msel__opt {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	height: 32px;
	padding: 0 8px;
	border: 0;
	background: transparent;
	border-radius: 6px;
	cursor: pointer;
	font-size: 13px;
	color: var(--ink-gray-8);
}
.pjx-msel__panel .pjx-msel__opt:hover {
	background: var(--surface-gray-2);
}
.pjx-msel__panel .pjx-msel__opt.is-sel {
	color: var(--ink-gray-9);
	font-weight: 500;
}
.pjx-msel__panel .pjx-msel__empty {
	padding: 12px;
	text-align: center;
	color: var(--ink-gray-4);
	font-size: 12px;
}
</style>
