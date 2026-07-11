<script setup>
import { computed, h } from 'vue'
import { Button, Dropdown, TabButtons } from 'frappe-ui'
import Icon from './Icon.vue'
import LivePill from './LivePill.vue'

const props = defineProps({
	crumbs: { type: Array, default: () => [] }, // [{ label, icon }] — simple mode
	tabs: { type: Array, default: () => [] }, // [{ id, label }] — legacy flat strip
	activeTab: { type: String, default: '' },
	presence: { type: Array, default: () => [] }, // user ids viewing this project
	showSettings: { type: Boolean, default: false },
	// ── tiered mode (set `title` to switch on the anchored title + surface nav) ──
	title: { type: String, default: '' },
	titleIcon: { type: String, default: 'folder' },
	surfaces: { type: Array, default: () => [] }, // [{ id, label, count }]
	activeSurface: { type: String, default: '' },
	moreItems: { type: Array, default: () => [] }, // [{ id, label, icon }] → dropdown
	moreActive: { type: Boolean, default: false },
})
const emit = defineEmits(['search', 'new', 'tab', 'settings', 'surface'])

// Render dropdown icons with our own Icon component (frappe-ui's Menu supports a
// component as `icon`). This uses the curated lucide registry, so dynamic names
// work reliably — a `lucide-<name>` class string would need Tailwind to have
// statically generated that exact class, which it can't for dynamic names.
const moreOptions = computed(() =>
	props.moreItems.map((it) => ({
		label: it.label,
		icon: it.icon ? { render: () => h(Icon, { name: it.icon, size: 16 }) } : undefined,
		onClick: () => emit('surface', it.id),
	})),
)
const surfaceOptions = computed(() =>
	props.surfaces.map((s) => ({
		label: s.count != null ? `${s.label} · ${s.count}` : s.label,
		value: s.id,
	})),
)
</script>

<template>
	<header class="pjx-topbar">
		<!-- simple mode: breadcrumbs + optional flat tab strip -->
		<template v-if="!title">
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
		</template>

		<!-- tiered mode: compact project breadcrumb + surface nav in one bar -->
		<template v-else>
			<button class="pjx-anchor" title="Switch project" @click="emit('search')">
				<span class="pjx-projmark"><Icon :name="titleIcon" :size="13" /></span>
				<span class="pjx-anchor__title">{{ title }}</span>
				<Icon name="chevron-down" :size="13" class="ink-5" style="flex: none" />
			</button>
			<span class="pjx-topbar__div" aria-hidden="true" />
			<nav class="pjx-topbar__nav">
				<TabButtons
					type="underline"
					:model-value="activeSurface"
					:options="surfaceOptions"
					@update:model-value="(v) => emit('surface', v)"
				/>
				<Dropdown v-if="moreItems.length" :options="moreOptions" placement="left">
					<button class="pjx-moretab" :class="{ 'is-active': moreActive }">
						More
						<Icon name="chevron-down" :size="13" />
					</button>
				</Dropdown>
			</nav>
		</template>

		<div class="pjx-topbar__right">
			<LivePill v-if="presence.length" :users="presence" />
			<!-- Tiered mode: the project anchor already opens the palette, so a
			     search button here would be redundant (⌘K still works). -->
			<button v-if="!title" class="pjx-searchbtn" title="Search & commands" @click="emit('search')">
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
