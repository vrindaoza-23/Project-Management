<script setup>
import { computed } from 'vue'
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
	meta: { type: Array, default: () => [] }, // ['26 tasks', 'Active sprint']
	surfaces: { type: Array, default: () => [] }, // [{ id, label, count }]
	activeSurface: { type: String, default: '' },
	views: { type: Array, default: () => [] }, // [{ id, label, icon }] nested under Tasks
	activeView: { type: String, default: '' },
	moreItems: { type: Array, default: () => [] }, // [{ id, label, icon }] → dropdown
	moreActive: { type: Boolean, default: false },
})
const emit = defineEmits(['search', 'new', 'tab', 'settings', 'surface', 'view'])

const moreOptions = computed(() =>
	props.moreItems.map((it) => ({ label: it.label, icon: it.icon, onClick: () => emit('surface', it.id) })),
)
const surfaceOptions = computed(() =>
	props.surfaces.map((s) => ({
		label: s.count != null ? `${s.label} · ${s.count}` : s.label,
		value: s.id,
	})),
)
const viewOptions = computed(() => props.views.map((v) => ({ label: v.label, value: v.id })))
</script>

<template>
	<header class="pjx-topbar" :class="{ 'pjx-topbar--tiered': title }">
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

		<!-- tiered mode: anchored project title -->
		<template v-else>
			<button class="pjx-anchor" title="Switch project" @click="emit('search')">
				<span class="pjx-projmark"><Icon :name="titleIcon" :size="15" /></span>
				<span class="pjx-anchor__text">
					<span class="pjx-anchor__title">
						{{ title }}
						<Icon name="chevron-down" :size="14" class="ink-5" />
					</span>
					<span v-if="meta.length" class="pjx-anchor__meta">
						<template v-for="(m, i) in meta" :key="i">
							<span v-if="i > 0" class="pjx-anchor__sep">·</span>{{ m }}
						</template>
					</span>
				</span>
			</button>
		</template>

		<div class="pjx-topbar__right">
			<LivePill v-if="presence.length" :users="presence" />
			<button class="pjx-searchbtn" title="Search & commands" @click="emit('search')">
				<Icon name="search" :size="15" />
				<span class="kbd">⌘K</span>
			</button>
			<Button v-if="showSettings" variant="ghost" theme="gray" title="Project settings" @click="emit('settings')">
				<template #icon><Icon name="settings" :size="16" /></template>
			</Button>
			<Button variant="solid" theme="blue" @click="emit('new')">
				<template #prefix><Icon name="plus" :size="15" /></template>
				New task
			</Button>
		</div>
	</header>

	<!-- tier 2: surfaces + view switcher (tiered mode only) -->
	<div v-if="title" class="pjx-subbar">
		<div class="pjx-subbar__left">
			<TabButtons
				type="underline"
				:model-value="activeSurface"
				:options="surfaceOptions"
				@update:model-value="(v) => emit('surface', v)"
			/>
			<Dropdown v-if="moreItems.length" :options="moreOptions" placement="left">
				<Button variant="ghost" theme="gray" :class="{ 'text-ink-gray-9': moreActive }">
					More
					<template #suffix><Icon name="chevron-down" :size="14" /></template>
				</Button>
			</Dropdown>
		</div>

		<TabButtons
			v-if="views.length"
			type="subtle"
			:model-value="activeView"
			:options="viewOptions"
			@update:model-value="(v) => emit('view', v)"
		/>
	</div>
</template>
