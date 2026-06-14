<script setup>
import { ref, computed, watch } from 'vue'
import { createResource, Avatar, Button } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import StatusDot from '@/components/StatusDot.vue'
import { userName } from '@/data/store'
import { openPalette, openCreate, openDrawer } from '@/data/ui'
import { relativeTime } from '@/utils/format'

const FILTERS = ['Unread', 'All', 'Mentions', 'Assigned']
const filter = ref('Unread')
const selected = ref(null)
const reply = ref('')

const KIND = {
	mention: { label: 'mentioned you', icon: 'at-sign' },
	assigned: { label: 'assigned you', icon: 'user-plus' },
	comment: { label: 'commented', icon: 'message-square' },
	status: { label: 'changed status', icon: 'circle-dot' },
	due: { label: 'due soon', icon: 'clock' },
	review: { label: 'requested review', icon: 'git-pull-request' },
}

const inbox = createResource({
	url: 'projex.api.get_inbox',
	makeParams: () => ({ filter: filter.value.toLowerCase() }),
	auto: true,
	onSuccess(rows) {
		if (rows.length && !rows.find((r) => r.name === selected.value)) selected.value = rows[0].name
	},
})
const marker = createResource({ url: 'projex.api.mark_notification_read' })
const detail = createResource({ url: 'projex.api.get_issue' })
const commenter = createResource({ url: 'projex.api.add_comment' })

watch(filter, () => inbox.reload())

const current = computed(() => (inbox.data || []).find((n) => n.name === selected.value))
watch(current, (n) => {
	if (n?.issue) detail.submit({ name: n.issue })
})

function select(n) {
	selected.value = n.name
	if (!n.is_read) markRead(n)
}
async function markRead(n) {
	await marker.submit({ name: n.name }).catch(() => {})
	n.is_read = 1
}
async function markAll() {
	await marker.submit({ all: true })
	inbox.reload()
}
async function sendReply() {
	const issue = current.value?.issue
	if (!issue || !reply.value.trim()) return
	await commenter.submit({ issue, content: `<p>${reply.value.trim()}</p>` })
	reply.value = ''
	detail.submit({ name: issue })
}
</script>

<template>
	<div class="pjx-main">
		<PageHeader :crumbs="[{ label: 'Inbox', icon: 'inbox' }]" @search="openPalette" @new="openCreate()" />
		<div class="pjx-view">
			<div class="pjx-inbox">
				<!-- left: list -->
				<div class="pjx-inbox__list">
					<div class="pjx-inbox__filters">
						<button
							v-for="f in FILTERS"
							:key="f"
							class="pjx-vtab"
							:class="{ 'is-active': filter === f }"
							@click="filter = f"
						>
							{{ f }}
						</button>
						<span style="flex: 1" />
						<Button variant="ghost" theme="gray" title="Mark all read" @click="markAll">
							<template #icon><Icon name="check-check" :size="15" /></template>
						</Button>
					</div>
					<button
						v-for="n in inbox.data || []"
						:key="n.name"
						class="pjx-notif"
						:class="{ 'is-active': selected === n.name, 'is-readrow': n.is_read }"
						@click="select(n)"
					>
						<span class="pjx-notif__unread" :class="{ 'is-read': n.is_read }" />
						<Avatar v-if="n.actor" :label="userName(n.actor)" size="md" />
						<span v-else class="pjx-notif__sys"><Icon :name="KIND[n.notification_type]?.icon || 'bell'" :size="14" /></span>
						<span class="pjx-notif__body">
							<span class="pjx-notif__head">
								<span style="font-weight: 500">{{ n.actor ? userName(n.actor) : 'Projex' }}</span>
								<span class="pjx-notif__kind">{{ KIND[n.notification_type]?.label || n.notification_type }}</span>
								<span class="pjx-notif__when">{{ relativeTime(n.creation) }}</span>
							</span>
							<span class="pjx-notif__target">{{ n.issue }}</span>
							<span class="pjx-notif__snip">{{ n.snippet }}</span>
						</span>
					</button>
					<div v-if="!inbox.loading && !(inbox.data || []).length" class="pjx-soon" style="height: 240px">
						<span class="pjx-soon__icon"><Icon name="inbox" :size="20" /></span>
						<div class="t-base ink-7" style="font-weight: 500">Inbox zero</div>
						<div class="t-sm ink-4">Nothing in {{ filter.toLowerCase() }}.</div>
					</div>
				</div>

				<!-- right: detail -->
				<div class="pjx-inbox__detail">
					<template v-if="current && detail.data">
						<div class="pjx-inbox__dhead">
							<span class="pjx-id">{{ detail.data.issue.issue_id }}</span>
							<span>{{ detail.data.issue.project }}</span>
							<span style="flex: 1" />
							<Button variant="outline" theme="gray" @click="openDrawer(detail.data.issue.name)">
								Open task
								<template #suffix><Icon name="arrow-right" :size="14" /></template>
							</Button>
						</div>
						<h2 class="pjx-inbox__dtitle">{{ detail.data.issue.title }}</h2>
						<div class="pjx-inbox__dmeta">
							<StatusDot :status="detail.data.status_meta" />
							<span>{{ detail.data.status_meta?.status_name }}</span>
							<span>·</span>
							<span style="text-transform: capitalize">{{ detail.data.issue.priority }}</span>
						</div>
						<div class="pjx-inbox__thread">
							<div v-for="c in detail.data.comments" :key="c.name" class="pjx-comment">
								<Avatar :label="c.author_name" size="md" />
								<div class="pjx-comment__body">
									<div class="pjx-comment__head">
										<strong>{{ c.author_name }}</strong>
										<span class="pjx-comment__when">{{ relativeTime(c.creation) }} ago</span>
									</div>
									<!-- eslint-disable-next-line vue/no-v-html -->
									<p class="pjx-comment__text" v-html="c.content" />
								</div>
							</div>
							<div v-if="!detail.data.comments.length" class="pjx-inbox__empty">No comments yet.</div>
						</div>
						<div class="pjx-inbox__reply">
							<input
								v-model="reply"
								class="pjx-inbox__replyinput"
								placeholder="Reply…"
								@keydown.enter="sendReply"
							/>
							<Button variant="solid" theme="gray" @click="sendReply">Send</Button>
						</div>
					</template>
					<div v-else class="pjx-inbox__empty" style="padding: 40px">Select a notification.</div>
				</div>
			</div>
		</div>
	</div>
</template>
