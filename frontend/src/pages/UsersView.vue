<script setup>
import { ref, computed, watch } from 'vue'
import { createResource, Avatar, Button, Badge } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import KpiStrip from '@/components/KpiStrip.vue'
import { store } from '@/data/store'
import { openPalette, openDrawer, openAppSettings } from '@/data/ui'
import { relativeTime } from '@/utils/format'

const OPEN_CATS = ['backlog', 'unstarted', 'started']
// Task workflow category → Badge theme, so status chips read in colour like the
// rest of the app (Todo grey, In progress amber, Done green, Cancelled red).
const STATUS_THEME = {
	backlog: 'gray',
	unstarted: 'gray',
	started: 'amber',
	completed: 'green',
	cancelled: 'red',
}
const statusTheme = (cat) => STATUS_THEME[cat] || 'gray'

const overview = createResource({ url: 'projex.api.get_users_overview', auto: true })
const detail = createResource({ url: 'projex.api.get_user_detail' })

const selected = ref(null)
const search = ref('')

const canManageUsers = computed(() => store.canManageUsers)
const users = computed(() => overview.data?.users || [])
const filtered = computed(() => {
	const q = search.value.trim().toLowerCase()
	if (!q) return users.value
	return users.value.filter(
		(u) => (u.full_name || '').toLowerCase().includes(q) || (u.user || '').toLowerCase().includes(q),
	)
})
const current = computed(() => detail.data)
const openCount = computed(() =>
	(detail.data?.assigned || []).filter((t) => OPEN_CATS.includes(t.category)).length,
)
const statItems = computed(() => {
	const c = current.value
	if (!c) return []
	return [
		{ label: 'Projects', value: c.projects.length },
		{ label: 'Open', value: openCount.value },
		{ label: 'Assigned', value: c.assigned.length },
		{ label: 'Comments', value: c.comments.length },
		{ label: 'Mentions', value: c.mentions.length },
	]
})

function selectUser(user) {
	selected.value = user
	detail.submit({ user })
}

watch(filtered, (list) => {
	if (!selected.value && list.length) selectUser(list[0].user)
})

function manageAccess() {
	openAppSettings('people-access', current.value.user)
}

const ACTION_ICON = {
	created: 'plus',
	status: 'circle-dot',
	updated: 'pencil',
	comment: 'message-square',
	assigned: 'user',
}
</script>

<template>
	<div class="pjx-main">
		<PageHeader :crumbs="[{ label: 'People', icon: 'users' }]" @search="openPalette" />
		<div class="pjx-users">
			<!-- LEFT: roster -->
			<div class="pjx-ppl-list">
				<div class="pjx-ppl-list__h">
					<span>People <span class="pjx-dim">· {{ users.length }}</span></span>
				</div>
				<div class="pjx-usr-search">
					<Icon name="search" :size="14" class="pjx-dim" />
					<input v-model="search" class="pjx-usr-search__in" placeholder="Search people" />
				</div>

				<div
					v-for="u in filtered"
					:key="u.user"
					class="pjx-ppl-row"
					:class="{ 'is-active': u.user === selected }"
					@click="selectUser(u.user)"
				>
					<Avatar :label="u.full_name" :image="u.user_image" size="md" />
					<div class="pjx-ppl-row__id">
						<span class="pjx-ppl-row__name">{{ u.full_name }}</span>
						<span class="pjx-ppl-row__sub">
							{{ u.project_count }} project{{ u.project_count === 1 ? '' : 's' }} · {{ u.open_tasks }} open
							<template v-if="u.last_activity"> · active {{ relativeTime(u.last_activity) }}</template>
						</span>
					</div>
					<Badge v-if="u.is_all_access" theme="gray" variant="subtle" size="sm">All-access</Badge>
				</div>
				<div v-if="!filtered.length && !overview.loading" class="pjx-ppl-empty">No users found.</div>
			</div>

			<!-- RIGHT: user detail -->
			<div class="pjx-ppl-detail">
				<template v-if="current">
					<div class="pjx-ppl-detail__h">
						<Avatar :label="current.full_name" :image="current.user_image" size="xl" />
						<div style="flex: 1; min-width: 0">
							<div class="pjx-ppl-detail__name">{{ current.full_name }}</div>
							<div class="pjx-dim t-sm">{{ current.user }}<template v-if="current.is_all_access"> · All-access</template></div>
						</div>
						<Button v-if="canManageUsers" variant="subtle" theme="gray" @click="manageAccess">
							<template #prefix><Icon name="settings" :size="14" /></template>
							Manage access
						</Button>
					</div>

					<div class="pjx-detail-kpis">
						<KpiStrip :items="statItems" />
					</div>

					<!-- Projects (read-only; admins edit access via Manage access) -->
					<div class="pjx-ppl-sec">
						<div class="pjx-ppl-sec__h">Projects</div>
						<div v-for="p in current.projects" :key="p.project" class="pjx-ppl-item">
							<span class="pjx-id">{{ p.key }}</span>
							<span class="pjx-ppl-item__t">{{ p.project_name }}</span>
							<Badge theme="gray" variant="subtle" size="sm">{{ p.role }}</Badge>
						</div>
						<div v-if="!current.projects.length" class="pjx-dim t-sm">Not allocated to any project.</div>
					</div>

					<div v-if="detail.loading" class="pjx-dim t-sm" style="padding: 12px">Loading…</div>
					<template v-else>
						<!-- Assigned tasks -->
						<div class="pjx-ppl-sec">
							<div class="pjx-ppl-sec__h">Assigned tasks</div>
							<div v-for="t in current.assigned" :key="t.name" class="pjx-ppl-item is-link" @click="openDrawer(t.name)">
								<span class="pjx-id">{{ t.issue_id }}</span>
								<span class="pjx-ppl-item__t">{{ t.title }}</span>
								<Badge :theme="statusTheme(t.category)" variant="subtle" size="sm">{{ t.status_name }}</Badge>
							</div>
							<div v-if="!current.assigned.length" class="pjx-dim t-sm">No assigned tasks.</div>
						</div>

						<!-- Recent activity -->
						<div class="pjx-ppl-sec">
							<div class="pjx-ppl-sec__h">Recent activity</div>
							<div
								v-for="a in current.activity"
								:key="a.name"
								class="pjx-ppl-item"
								:class="{ 'is-link': a.issue }"
								@click="a.issue && openDrawer(a.issue)"
							>
								<span class="pjx-ppl-item__ic"><Icon :name="ACTION_ICON[a.action] || 'dot'" :size="13" /></span>
								<span class="pjx-ppl-item__t">
									<span class="pjx-dim">{{ a.project_key }}</span>
									{{ a.action }}<template v-if="a.detail"> · {{ a.detail }}</template>
									<span v-if="a.issue_id" class="pjx-id">{{ a.issue_id }}</span>
								</span>
								<span class="pjx-dim t-xs">{{ relativeTime(a.creation) }}</span>
							</div>
							<div v-if="!current.activity.length" class="pjx-dim t-sm">No activity yet.</div>
						</div>

						<!-- Comments -->
						<div class="pjx-ppl-sec">
							<div class="pjx-ppl-sec__h">Comments</div>
							<div v-for="c in current.comments" :key="c.name" class="pjx-ppl-item is-link" @click="openDrawer(c.issue)">
								<span class="pjx-id">{{ c.issue_id }}</span>
								<span class="pjx-ppl-item__t">{{ c.snippet }}</span>
								<span class="pjx-dim t-xs">{{ relativeTime(c.creation) }}</span>
							</div>
							<div v-if="!current.comments.length" class="pjx-dim t-sm">No comments.</div>
						</div>

						<!-- Mentions -->
						<div class="pjx-ppl-sec">
							<div class="pjx-ppl-sec__h">Mentions</div>
							<div v-for="c in current.mentions" :key="c.name" class="pjx-ppl-item is-link" @click="openDrawer(c.issue)">
								<span class="pjx-id">{{ c.issue_id }}</span>
								<span class="pjx-ppl-item__t"><strong>{{ c.by }}:</strong> {{ c.snippet }}</span>
								<span class="pjx-dim t-xs">{{ relativeTime(c.creation) }}</span>
							</div>
							<div v-if="!current.mentions.length" class="pjx-dim t-sm">No mentions.</div>
						</div>
					</template>
				</template>
				<div v-else class="pjx-ppl-empty">Select someone to see their projects and activity.</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-users {
	display: grid;
	grid-template-columns: minmax(340px, 1fr) minmax(380px, 1.15fr);
	gap: 0;
	flex: 1;
	min-height: 0;
	overflow: hidden;
	letter-spacing: 0.02em;
}
/* Flush split: no boxes — the two panes read apart on one surface, divided by a
   single hairline rather than each sitting inside its own card. */
.pjx-ppl-list {
	overflow-y: auto;
}
.pjx-ppl-detail {
	overflow-y: auto;
	border-inline-start: 1px solid var(--outline-gray-1);
}
.pjx-ppl-list__h {
	position: sticky;
	top: 0;
	z-index: 2;
	background: var(--surface-white);
	padding: 12px 14px;
	font-weight: 600;
	border-bottom: 1px solid var(--outline-gray-1);
}
.pjx-usr-search {
	position: sticky;
	top: 45px;
	z-index: 2;
	display: flex;
	align-items: center;
	gap: 6px;
	background: var(--surface-white);
	padding: 8px 12px;
	border-bottom: 1px solid var(--outline-gray-1);
}
.pjx-usr-search__in {
	border: 0;
	outline: none;
	background: transparent;
	font-size: 13px;
	width: 100%;
	color: var(--ink-gray-8);
}
.pjx-ppl-row {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 8px 14px;
	cursor: pointer;
	border-bottom: 1px solid var(--outline-gray-1);
}
.pjx-ppl-row:hover {
	background: var(--surface-gray-1);
}
.pjx-ppl-row.is-active {
	background: var(--surface-gray-2);
}
.pjx-ppl-row__id {
	display: flex;
	flex-direction: column;
	flex: 1;
	min-width: 0;
}
.pjx-ppl-row__name {
	font-weight: 500;
	color: var(--ink-gray-8);
}
.pjx-ppl-row__sub {
	font-size: 12px;
	color: var(--ink-gray-5);
}
.pjx-ppl-detail__h {
	display: flex;
	gap: 12px;
	align-items: center;
	padding: 16px;
	border-bottom: 1px solid var(--outline-gray-1);
}
.pjx-ppl-detail__name {
	font-size: 16px;
	font-weight: 600;
	color: var(--ink-gray-9);
}
/* Shared Espresso stat strip (KpiStrip), inset to match the section padding. */
.pjx-detail-kpis {
	margin: 14px 16px;
}
.pjx-ppl-sec {
	padding: 6px 14px 14px;
}
.pjx-ppl-sec__h {
	font-size: 12px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--ink-gray-5);
	padding: 8px 0;
}
.pjx-ppl-item {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 8px;
	border-radius: 8px;
	font-size: 13px;
}
.pjx-ppl-item.is-link {
	cursor: pointer;
}
.pjx-ppl-item.is-link:hover {
	background: var(--surface-gray-1);
}
.pjx-ppl-item__t {
	flex: 1;
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	color: var(--ink-gray-7);
}
.pjx-ppl-item__ic {
	color: var(--ink-gray-5);
	display: inline-flex;
}
.pjx-id {
	font-variant-numeric: tabular-nums;
	font-size: 12px;
	color: var(--ink-gray-5);
}
.pjx-ppl-empty {
	padding: 24px;
	color: var(--ink-gray-5);
	font-size: 13px;
}
.pjx-dim {
	color: var(--ink-gray-5);
}
</style>
