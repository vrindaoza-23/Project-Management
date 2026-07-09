<script setup>
import { ref, computed, watch } from 'vue'
import { createResource, Avatar, Button, Select, Checkbox } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import SelectField from '@/components/SelectField.vue'
import { openPalette, openDrawer } from '@/data/ui'
import { relativeTime } from '@/utils/format'
import { notify, notifyError, confirm } from '@/utils/feedback'

const ROLE_OPTS = [
	{ label: 'Admin', value: 'Admin' },
	{ label: 'Member', value: 'Member' },
	{ label: 'Guest', value: 'Guest' },
]
const OPEN_CATS = ['backlog', 'unstarted', 'started']

const overview = createResource({ url: 'projex.api.get_users_overview', auto: true })
const detail = createResource({ url: 'projex.api.get_user_detail' })

const roleUpdate = createResource({ url: 'projex.api.update_member_role' })
const allAccess = createResource({ url: 'projex.api.set_all_access' })
const memberAdd = createResource({ url: 'projex.api.add_member' })
const memberRemove = createResource({ url: 'projex.api.remove_member' })

const selected = ref(null)
const newProjects = ref([])
const newRole = ref('Member')
const search = ref('')

const canGrantAllAccess = computed(() => overview.data?.can_grant_all_access)
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

function selectUser(user) {
	selected.value = user
	newProjects.value = []
	detail.submit({ user })
}

watch(filtered, (list) => {
	if (!selected.value && list.length) selectUser(list[0].user)
})

async function changeRole(p, role) {
	if (!role || role === p.role) return
	await roleUpdate.submit({ parent_doctype: 'Projex Project', parent: p.project, user: selected.value, role })
	detail.reload()
}
async function toggleAllAccess(u, enabled) {
	await allAccess.submit({ user: u.user, enabled: enabled ? 1 : 0 })
	overview.reload()
	if (selected.value === u.user) detail.reload()
}
async function allocate() {
	for (const proj of newProjects.value) {
		await memberAdd.submit({ parent_doctype: 'Projex Project', parent: proj, user: selected.value, role: newRole.value })
	}
	newProjects.value = []
	newRole.value = 'Member'
	detail.reload()
	overview.reload()
}
async function deallocate(p) {
	const ok = await confirm({
		title: 'Remove from project',
		message: `Remove ${current.value.full_name} from ${p.project_name}?`,
		confirmLabel: 'Remove',
		theme: 'red',
	})
	if (!ok) return
	try {
		await memberRemove.submit({ parent_doctype: 'Projex Project', parent: p.project, user: selected.value })
		detail.reload()
		overview.reload()
		notify.success(`Removed ${current.value.full_name} from ${p.project_name}`)
	} catch (e) {
		notifyError(e, 'Could not remove member')
	}
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
		<PageHeader :crumbs="[{ label: 'Users', icon: 'users' }]" @search="openPalette" />
		<div class="pjx-users">
			<!-- LEFT: roster -->
			<div class="pjx-ppl-list">
				<div class="pjx-ppl-list__h">
					<span>Users <span class="pjx-dim">· {{ users.length }}</span></span>
				</div>
				<div class="pjx-usr-search">
					<Icon name="search" :size="14" class="pjx-dim" />
					<input v-model="search" class="pjx-usr-search__in" placeholder="Search users" />
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
					<label
						v-if="canGrantAllAccess"
						class="pjx-ppl-all"
						title="Grant visibility into every project"
						@click.stop
					>
						<Checkbox
							:model-value="u.is_all_access"
							label="All projects"
							@update:model-value="(v) => toggleAllAccess(u, v)"
						/>
					</label>
					<span v-else-if="u.is_all_access" class="pjx-badge">All-access</span>
				</div>
				<div v-if="!filtered.length && !overview.loading" class="pjx-ppl-empty">No users found.</div>
			</div>

			<!-- RIGHT: user detail -->
			<div class="pjx-ppl-detail">
				<template v-if="current">
					<div class="pjx-ppl-detail__h">
						<Avatar :label="current.full_name" :image="current.user_image" size="xl" />
						<div>
							<div class="pjx-ppl-detail__name">{{ current.full_name }}</div>
							<div class="pjx-dim t-sm">{{ current.user }}<template v-if="current.is_all_access"> · All-access</template></div>
						</div>
					</div>

					<div class="pjx-stat-grid">
						<div class="pjx-stat"><b>{{ current.projects.length }}</b><span>Projects</span></div>
						<div class="pjx-stat"><b>{{ openCount }}</b><span>Open tasks</span></div>
						<div class="pjx-stat"><b>{{ current.assigned.length }}</b><span>Assigned</span></div>
						<div class="pjx-stat"><b>{{ current.comments.length }}</b><span>Comments</span></div>
						<div class="pjx-stat"><b>{{ current.mentions.length }}</b><span>Mentions</span></div>
					</div>

					<!-- Project allocations -->
					<div class="pjx-ppl-sec">
						<div class="pjx-ppl-sec__h">Project allocation</div>
						<div v-for="p in current.projects" :key="p.project" class="pjx-ppl-item">
							<span class="pjx-id">{{ p.key }}</span>
							<span class="pjx-ppl-item__t">{{ p.project_name }}</span>
							<div v-if="p.can_manage && p.role !== 'Lead'" style="width: 116px" @click.stop>
								<Select :model-value="p.role" :options="ROLE_OPTS" @update:model-value="(v) => changeRole(p, v)" />
							</div>
							<span v-else class="pjx-badge">{{ p.role }}</span>
							<Button v-if="p.can_manage && p.role !== 'Lead'" variant="ghost" theme="gray" title="Remove from project" @click="deallocate(p)">
								<template #icon><Icon name="x" :size="14" /></template>
							</Button>
						</div>
						<div v-if="!current.projects.length" class="pjx-dim t-sm">Not allocated to any project.</div>

						<div v-if="current.allocatable.length" class="pjx-ppl-add">
							<div class="flex col g-1" style="flex: 1">
								<span class="t-xs ink-5">Allocate to projects</span>
								<SelectField v-model="newProjects" :options="current.allocatable" multiple placeholder="Pick projects" />
							</div>
							<div class="flex col g-1" style="width: 116px">
								<span class="t-xs ink-5">Role</span>
								<Select v-model="newRole" :options="ROLE_OPTS" />
							</div>
							<Button variant="subtle" theme="gray" :loading="memberAdd.loading" :disabled="!newProjects.length" @click="allocate">
								Add
							</Button>
						</div>
					</div>

					<div v-if="detail.loading" class="pjx-dim t-sm" style="padding: 12px">Loading…</div>
					<template v-else>
						<!-- Assigned tasks -->
						<div class="pjx-ppl-sec">
							<div class="pjx-ppl-sec__h">Assigned tasks</div>
							<div v-for="t in current.assigned" :key="t.name" class="pjx-ppl-item is-link" @click="openDrawer(t.name)">
								<span class="pjx-id">{{ t.issue_id }}</span>
								<span class="pjx-ppl-item__t">{{ t.title }}</span>
								<span class="pjx-badge">{{ t.status_name }}</span>
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
				<div v-else class="pjx-ppl-empty">Select a user to manage their projects and see activity.</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-users {
	display: grid;
	grid-template-columns: minmax(360px, 1fr) minmax(380px, 1.1fr);
	gap: 16px;
	padding: 16px;
	flex: 1;
	min-height: 0;
	overflow: hidden;
}
.pjx-ppl-list,
.pjx-ppl-detail {
	overflow-y: auto;
	border: 1px solid var(--outline-gray-1);
	border-radius: 12px;
	background: var(--surface-white);
}
.pjx-ppl-list__h {
	position: sticky;
	top: 0;
	background: var(--surface-white);
	padding: 12px 14px;
	font-weight: 600;
	border-bottom: 1px solid var(--outline-gray-1);
}
.pjx-usr-search {
	display: flex;
	align-items: center;
	gap: 6px;
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
.pjx-ppl-all {
	display: inline-flex;
	align-items: center;
}
.pjx-ppl-add {
	display: flex;
	gap: 8px;
	align-items: flex-end;
	padding: 12px 0 4px;
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
.pjx-stat-grid {
	display: grid;
	grid-template-columns: repeat(5, 1fr);
	gap: 8px;
	padding: 14px;
}
.pjx-stat {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: 10px 4px;
	background: var(--surface-gray-1);
	border-radius: 10px;
}
.pjx-stat b {
	font-size: 18px;
	color: var(--ink-gray-9);
}
.pjx-stat span {
	font-size: 11px;
	color: var(--ink-gray-5);
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
.pjx-badge {
	font-size: 12px;
	padding: 1px 8px;
	border-radius: 999px;
	background: var(--surface-gray-2);
	color: var(--ink-gray-7);
	white-space: nowrap;
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
