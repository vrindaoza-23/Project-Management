<script setup>
import { Button } from 'frappe-ui'
import Icon from './Icon.vue'
import LivePill from './LivePill.vue'

defineProps({
	crumbs: { type: Array, default: () => [] }, // [{ label, icon }]
	tabs: { type: Array, default: () => [] }, // [{ id, label }]
	activeTab: { type: String, default: '' },
	presence: { type: Array, default: () => [] }, // user ids viewing this project
	showSettings: { type: Boolean, default: false },
})
const emit = defineEmits(['search', 'new', 'tab', 'settings'])
</script>

<template>
	<header class="pjx-topbar">
		<div class="pjx-crumbs">
			<span v-for="(c, i) in crumbs" :key="i" class="pjx-crumb">
				<Icon v-if="i > 0" name="chevron-right" :size="14" class="ink-4" />
				<Icon v-if="c.icon" :name="c.icon" :size="14" class="ink-6" />
				<span
					:style="{
						color: i === crumbs.length - 1 ? 'var(--ink-gray-9)' : 'var(--ink-gray-5)',
						fontWeight: i === crumbs.length - 1 ? 500 : 420,
						fontSize: '13px',
					}"
					>{{ c.label }}</span
				>
			</span>
		</div>

		<nav v-if="tabs.length" class="pjx-vtabs">
			<button
				v-for="t in tabs"
				:key="t.id"
				class="pjx-vtab"
				:class="{ 'is-active': activeTab === t.id }"
				@click="emit('tab', t.id)"
			>
				{{ t.label }}
			</button>
		</nav>

		<div class="pjx-topbar__right">
			<LivePill v-if="presence.length" :users="presence" />
			<button class="pjx-searchbtn" title="Search & commands" @click="emit('search')">
				<Icon name="search" :size="15" />
				<span class="kbd">⌘K</span>
			</button>
			<Button v-if="showSettings" variant="ghost" theme="gray" title="Project settings" @click="emit('settings')">
				<template #icon><Icon name="settings" :size="16" /></template>
			</Button>
			<Button variant="solid" theme="gray" @click="emit('new')">
				<template #prefix><Icon name="plus" :size="15" /></template>
				New task
			</Button>
		</div>
	</header>
</template>
