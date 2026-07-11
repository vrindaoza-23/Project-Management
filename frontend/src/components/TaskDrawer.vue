<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { createResource, Dropdown, Button, Avatar, DatePicker, Checkbox, TabButtons } from 'frappe-ui'
import Icon from './Icon.vue'
import StatusDot from './StatusDot.vue'
import PriorityBars from './PriorityBars.vue'
import LabelChip from './LabelChip.vue'
import AvatarStack from './AvatarStack.vue'
import SelectField from './SelectField.vue'
import LogTimeDialog from './LogTimeDialog.vue'
import { userName, store } from '@/data/store'
import { relativeTime, dueLabel, isToday, ageChip } from '@/utils/format'
import { notify } from '@/utils/feedback'

const REACTIONS = ['👍', '💡', '🎉', '👀']

const props = defineProps({ name: { type: String, default: null } })
const emit = defineEmits(['close', 'changed'])

const tab = ref('comments')
const newComment = ref('')
const editingDesc = ref(false)
const descDraft = ref('')

const detail = createResource({
	url: 'projex.api.get_issue',
	makeParams: () => ({ name: props.name }),
})
const statuses = createResource({ url: 'projex.api.get_statuses' })
const integration = createResource({ url: 'projex.api.integration_status', auto: true })
const updater = createResource({ url: 'projex.api.update_issue' })
const commenter = createResource({ url: 'projex.api.add_comment' })
const presence = createResource({ url: 'projex.api.set_presence' })
const pickers = createResource({ url: 'projex.api.get_pickers' })
const reactor = createResource({ url: 'projex.api.toggle_reaction' })
const timeLogs = createResource({ url: 'projex.api.get_issue_time_logs' })
const attDelete = createResource({ url: 'projex.api.delete_attachment' })
const checklistSaver = createResource({ url: 'projex.api.set_checklist' })
const linkAdd = createResource({ url: 'projex.api.add_issue_link' })
const linkRemove = createResource({ url: 'projex.api.remove_issue_link' })
const projectIssues = createResource({ url: 'frappe.client.get_list' })
const logTimeOpen = ref(false)
const uploading = ref(false)
const newLinkType = ref('blocks')
const newLinkTarget = ref('')
const LINK_TYPES = ['blocks', 'blocked by', 'relates to', 'duplicates']

watch(
	() => props.name,
	(name) => {
		if (name) {
			tab.value = 'comments'
			detail.fetch()
			// Announce presence (ephemeral; fans out to the project room).
			presence.submit({ issue: name }).catch(() => {})
		}
	},
	{ immediate: true },
)

const issue = computed(() => detail.data?.issue)
const statusMeta = computed(() => detail.data?.status_meta)
const labels = computed(() => detail.data?.labels || [])
const subtasks = computed(() => detail.data?.subtasks || [])
const comments = computed(() => detail.data?.comments || [])

// ---- checklist (in-issue, lighter than subtasks) ----
const checklist = ref([])
const newChecklist = ref('')
watch(
	() => detail.data?.checklist,
	(items) => { checklist.value = (items || []).map((c) => ({ ...c })) },
	{ immediate: true },
)
const checkDone = computed(() => checklist.value.filter((c) => c.done).length)

async function persistChecklist() {
	const items = checklist.value.map((c) => ({ title: c.title, done: c.done ? 1 : 0 }))
	const res = await checklistSaver.submit({ issue: issue.value.name, items: JSON.stringify(items) })
	checklist.value = (res.checklist || []).map((c) => ({ ...c }))
}
function addChecklistItem() {
	const title = newChecklist.value.trim()
	if (!title) return
	checklist.value.push({ title, done: false })
	newChecklist.value = ''
	persistChecklist()
}
function toggleChecklistItem(item) {
	item.done = !item.done // optimistic
	persistChecklist()
}
function deleteChecklistItem(item) {
	checklist.value = checklist.value.filter((c) => c !== item)
	persistChecklist()
}
const subDone = computed(() => subtasks.value.filter((s) => s.done).length)

const PRIORITIES = ['Urgent', 'High', 'Medium', 'Low', 'None']
const TYPES = ['Task', 'Bug', 'Story', 'Epic']
const TYPE_ICON = { Task: 'square-check', Bug: 'bug', Story: 'bookmark', Epic: 'zap' }
const typeOptions = computed(() => TYPES.map((t) => ({ label: t, onClick: () => changeField('issue_type', t) })))
const RECURRENCE_OPTIONS = [
	{ value: 'None', label: 'Never' },
	{ value: 'Daily', label: 'Daily' },
	{ value: 'Weekly', label: 'Weekly' },
	{ value: 'Biweekly', label: 'Every 2 weeks' },
	{ value: 'Monthly', label: 'Monthly' },
]

watch(
	() => issue.value?.project,
	(p) => {
		if (p) {
			statuses.submit({ project: p })
			pickers.submit({ project: p })
		}
	},
)
watch(
	() => props.name,
	(name) => {
		if (name && integration.data?.timesheet) timeLogs.submit({ issue: name })
	},
)

const labelIds = computed(() => labels.value.map((l) => l.label))
const userOptions = computed(() =>
	(pickers.data?.users || store.users).map((u) => ({ value: u.name, label: u.full_name || u.name })),
)
const labelOptions = computed(() =>
	(pickers.data?.labels || []).map((l) => ({ value: l.name, label: l.label_name, color: l.color })),
)
const cycleOptions = computed(() =>
	(pickers.data?.cycles || []).map((c) => ({ value: c.name, label: c.cycle_name })),
)

async function setAssignees(users) {
	issue.value.assignees = users // optimistic
	await updater.submit({ name: issue.value.name, fields: JSON.stringify({ assignees: users }) }).catch(() => {})
	emit('changed')
}
async function setLabels(ids) {
	detail.data.labels = ids.map((id) => {
		const o = (pickers.data?.labels || []).find((l) => l.name === id)
		return { label: id, label_name: o?.label_name, color: o?.color }
	})
	await updater.submit({ name: issue.value.name, fields: JSON.stringify({ labels: ids }) }).catch(() => {})
	emit('changed')
}

async function react(comment, emoji) {
	const data = await reactor.submit({ comment: comment.name, emoji })
	comment.reactions = data
}
function reactionEntries(c) {
	return Object.entries(c.reactions || {})
}

const statusOptions = computed(() =>
	(statuses.data || []).map((s) => ({
		label: s.status_name,
		onClick: () => changeField('status', s.name),
	})),
)
const priorityOptions = computed(() =>
	PRIORITIES.map((p) => ({ label: p, onClick: () => changeField('priority', p) })),
)

async function changeField(field, value) {
	if (!issue.value || issue.value[field] === value) return
	const prev = issue.value[field]
	issue.value[field] = value // optimistic
	if (field === 'status') {
		const meta = (statuses.data || []).find((s) => s.name === value)
		if (meta) detail.data.status_meta = meta
	}
	try {
		await updater.submit({ name: issue.value.name, fields: JSON.stringify({ [field]: value }) })
		emit('changed')
	} catch (e) {
		issue.value[field] = prev
		console.error('[projex] update failed', e)
	}
}

function htmlToText(html) {
	const tmp = document.createElement('div')
	tmp.innerHTML = html || ''
	return tmp.textContent || tmp.innerText || ''
}
function escapeHtml(s) {
	return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
function startEditDesc() {
	descDraft.value = htmlToText(issue.value?.description)
	editingDesc.value = true
}
async function saveDesc() {
	const text = descDraft.value.trim()
	const html = text
		? text.split(/\n/).map((l) => (l.trim() ? `<p>${escapeHtml(l)}</p>` : '<p><br></p>')).join('')
		: ''
	editingDesc.value = false
	await changeField('description', html)
}

async function saveTitle(e) {
	const title = e.target.value.trim()
	if (!issue.value || !title || title === issue.value.title) return
	const prev = issue.value.title
	issue.value.title = title
	try {
		await updater.submit({ name: issue.value.name, fields: JSON.stringify({ title }) })
		emit('changed')
	} catch {
		issue.value.title = prev
	}
}

async function toggleSubtask(st) {
	const done = !st.done
	st.done = done // optimistic
	const target = (statuses.data || []).find(
		(s) => (done ? s.category === 'completed' : s.category === 'unstarted'),
	)
	if (!target) return
	try {
		await updater.submit({ name: st.name, fields: JSON.stringify({ status: target.name }) })
	} catch {
		st.done = !done
	}
}

async function postComment() {
	const content = newComment.value.trim()
	if (!content) return
	const html = `<p>${content}</p>`
	newComment.value = ''
	const res = await commenter.submit({ issue: issue.value.name, content: html })
	comments.value.push(res)
}

// ---- @mention autocomplete -------------------------------------------------
// Backend (Projex Comment controller) turns `@<email>` tokens into mention
// notifications, so the picker inserts the user's id (their email in Frappe).
const commentInput = ref(null)
const mention = ref({ open: false, query: '', start: 0, active: 0 })

const mentionPeople = computed(() => {
	if (!mention.value.open) return []
	const q = mention.value.query.toLowerCase()
	const people = pickers.data?.users || store.users || []
	return people
		.filter((u) => !q || (u.full_name || u.name).toLowerCase().includes(q) || u.name.toLowerCase().includes(q))
		.slice(0, 6)
})

function onCommentInput(e) {
	const el = e.target
	const pos = el.selectionStart
	const upto = el.value.slice(0, pos)
	const m = upto.match(/@([\w.\-+@]*)$/) // open token: @ + word chars, no whitespace
	if (m) {
		mention.value = { open: true, query: m[1], start: pos - m[0].length, active: 0 }
	} else {
		mention.value.open = false
	}
}

function mentionNav(dir) {
	const n = mentionPeople.value.length
	if (!n) return
	mention.value.active = (mention.value.active + dir + n) % n
}

function pickMention(user) {
	const el = commentInput.value
	const before = newComment.value.slice(0, mention.value.start)
	const after = newComment.value.slice(el ? el.selectionStart : newComment.value.length)
	newComment.value = `${before}@${user.name} ${after}`
	mention.value.open = false
	nextTick(() => {
		if (!el) return
		const caret = (before + '@' + user.name + ' ').length
		el.focus()
		el.setSelectionRange(caret, caret)
	})
}

// Enter selects the highlighted person while the menu is open (otherwise falls
// through to a normal newline). Cmd+Enter still posts.
function onCommentEnter(e) {
	if (mention.value.open && mentionPeople.value.length) {
		e.preventDefault()
		pickMention(mentionPeople.value[mention.value.active])
	}
}

const attachments = computed(() => detail.data?.attachments || [])
const links = computed(() => detail.data?.links || [])

const githubLinks = computed(() => detail.data?.github_links || [])
const githubEnabled = computed(() => !!integration.data?.github)

// Suggested git branch: <issue-id>-<slugged title>, e.g. QAP-4-fix-login. The
// leading issue id is the magic word the webhook parses back to this issue.
const branchName = computed(() => {
	const id = issue.value?.issue_id
	if (!id) return ''
	const slug = (issue.value?.title || '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '')
		.slice(0, 40)
	return slug ? `${id}-${slug}` : id
})

const tabOptions = computed(() => {
	const opts = [
		{ label: 'Comments', value: 'comments' },
		{ label: 'Activity', value: 'activity' },
		{ label: 'Files', value: 'files' },
		{ label: 'Linked work', value: 'links' },
	]
	if (githubEnabled.value) opts.push({ label: 'Development', value: 'dev' })
	return opts
})

const GH_STATE = {
	open: { label: 'Open', tone: 'green' },
	draft: { label: 'Draft', tone: 'gray' },
	merged: { label: 'Merged', tone: 'purple' },
	closed: { label: 'Closed', tone: 'red' },
}

function copyText(text) {
	if (!text) return
	navigator.clipboard?.writeText(text)
	notify.success('Copied')
}

const ghRefresh = createResource({ url: 'projex.github.refresh_links' })
function refreshGithub() {
	ghRefresh.submit({ issue: issue.value.name }).then((rows) => {
		if (detail.data) detail.data.github_links = rows
		notify.success('Refreshed from GitHub')
	})
}
const ghRemove = createResource({ url: 'projex.github.remove_link' })
function removeGithubLink(name) {
	ghRemove.submit({ name }).then(() => {
		if (detail.data) detail.data.github_links = githubLinks.value.filter((l) => l.name !== name)
	})
}
const linkTargetOptions = computed(() =>
	(projectIssues.data || [])
		.filter((i) => i.name !== issue.value?.name)
		.map((i) => ({ value: i.name, label: `${i.issue_id} ${i.title}` })),
)

watch(
	() => issue.value?.project,
	(p) => {
		if (p) {
			projectIssues.submit({
				doctype: 'Projex Issue',
				filters: { project: p },
				fields: ['name', 'issue_id', 'title'],
				limit_page_length: 200,
			})
		}
	},
)

function fmtSize(bytes) {
	if (!bytes) return ''
	if (bytes < 1024) return bytes + ' B'
	if (bytes < 1048576) return Math.round(bytes / 1024) + ' KB'
	return (bytes / 1048576).toFixed(1) + ' MB'
}

async function onUpload(e) {
	const file = e.target.files?.[0]
	if (!file) return
	uploading.value = true
	try {
		const fd = new FormData()
		fd.append('file', file, file.name)
		fd.append('is_private', '1')
		fd.append('doctype', 'Projex Issue')
		fd.append('docname', issue.value.name)
		await fetch('/api/method/upload_file', {
			method: 'POST',
			headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '' },
			body: fd,
		})
		detail.fetch()
	} finally {
		uploading.value = false
		e.target.value = ''
	}
}
async function removeAttachment(name) {
	await attDelete.submit({ name })
	detail.fetch()
}
async function addLink() {
	const target = newLinkTarget.value
	if (!target) return
	await linkAdd.submit({ issue: issue.value.name, link_type: newLinkType.value, target })
	newLinkTarget.value = ''
	detail.fetch()
}
async function removeLink(name) {
	await linkRemove.submit({ name })
	detail.fetch()
}
</script>

<template>
	<div v-if="name" class="pjx-drawerlayer">
		<div class="pjx-scrim is-open" @click="emit('close')" />
		<aside class="pjx-drawer is-open" role="dialog" :aria-label="issue?.title">
			<div class="pjx-drawer__top">
				<div class="pjx-drawer__crumbs">
					<span class="pjx-id">{{ issue?.issue_id }}</span>
				</div>
				<span style="flex: 1" />
				<Button variant="ghost" theme="gray" @click="emit('close')">
					<template #icon><Icon name="x" :size="16" /></template>
				</Button>
			</div>

			<div v-if="issue" class="pjx-drawer__body">
				<div class="pjx-drawer__main">
					<div class="pjx-statusrow">
						<Dropdown :options="typeOptions">
							<Button variant="outline" theme="gray">
								<span class="flex items-center g-2">
									<Icon :name="TYPE_ICON[issue.issue_type || 'Task']" :size="13" />{{ issue.issue_type || 'Task' }}
								</span>
								<template #suffix><Icon name="chevron-down" :size="14" /></template>
							</Button>
						</Dropdown>
						<Dropdown :options="statusOptions">
							<Button variant="outline" theme="gray">
								<span class="flex items-center g-2">
									<StatusDot :status="statusMeta" :size="8" />{{ statusMeta?.status_name || 'Status' }}
								</span>
								<template #suffix><Icon name="chevron-down" :size="14" /></template>
							</Button>
						</Dropdown>
						<Dropdown :options="priorityOptions">
							<Button variant="outline" theme="gray">
								<span class="flex items-center g-2">
									<PriorityBars :priority="issue.priority" />{{ issue.priority }}
								</span>
								<template #suffix><Icon name="chevron-down" :size="14" /></template>
							</Button>
						</Dropdown>
					</div>

					<input class="pjx-dtitle" :value="issue.title" placeholder="Issue title" @blur="saveTitle" />

					<div class="pjx-descwrap">
						<div v-if="editingDesc" class="pjx-descedit">
							<textarea
								v-model="descDraft"
								class="pjx-descarea"
								rows="6"
								placeholder="Add a description…"
								data-gramm="false"
								@keydown.meta.enter="saveDesc"
							/>
							<div class="flex g-2" style="margin-top: 6px">
								<Button variant="solid" theme="gray" @click="saveDesc">Save</Button>
								<Button variant="subtle" theme="gray" @click="editingDesc = false">Cancel</Button>
							</div>
						</div>
						<template v-else>
							<div class="pjx-desc__head">
								<span class="t-xs ink-5" style="font-weight: 500">Description</span>
								<button class="pjx-desc__edit" @click="startEditDesc">
									<Icon name="pencil" :size="12" /> Edit
								</button>
							</div>
							<!-- eslint-disable-next-line vue/no-v-html -->
							<div v-if="issue.description" class="pjx-desc" v-html="issue.description" @click="startEditDesc" />
							<div v-else class="pjx-desc pjx-descempty" @click="startEditDesc">Add a description…</div>
						</template>
					</div>

					<div v-if="subtasks.length" class="pjx-subs">
						<div class="pjx-subs__head">
							<span style="font-weight: 500">Subtasks</span>
							<span class="pjx-subs__count">{{ subDone }}/{{ subtasks.length }}</span>
							<span class="pjx-subs__bar"
								><span
									class="pjx-subs__fill"
									:style="{ width: (subDone / subtasks.length) * 100 + '%' }"
							/></span>
						</div>
						<div v-for="st in subtasks" :key="st.name" class="pjx-subs__row">
							<Checkbox :model-value="st.done" @update:model-value="toggleSubtask(st)" />
							<span class="pjx-subs__title" :class="{ 'is-done': st.done }">{{ st.title }}</span>
							<span class="pjx-subs__id">{{ st.issue_id }}</span>
						</div>
					</div>

					<div class="pjx-subs">
						<div class="pjx-subs__head">
							<span style="font-weight: 500">Checklist</span>
							<span v-if="checklist.length" class="pjx-subs__count">{{ checkDone }}/{{ checklist.length }}</span>
							<span v-if="checklist.length" class="pjx-subs__bar"
								><span
									class="pjx-subs__fill"
									:style="{ width: (checkDone / checklist.length) * 100 + '%' }"
							/></span>
						</div>
						<div v-for="(ck, i) in checklist" :key="ck.name || i" class="pjx-subs__row pjx-check__row">
							<Checkbox :model-value="ck.done" @update:model-value="toggleChecklistItem(ck)" />
							<span class="pjx-subs__title" :class="{ 'is-done': ck.done }">{{ ck.title }}</span>
							<button class="pjx-check__del" title="Remove" @click="deleteChecklistItem(ck)">
								<Icon name="x" :size="13" />
							</button>
						</div>
						<input
							v-model="newChecklist"
							class="pjx-check__add"
							placeholder="Add checklist item…"
							@keydown.enter="addChecklistItem"
						/>
					</div>

					<TabButtons v-model="tab" :options="tabOptions" />

					<div v-if="tab === 'comments'" class="pjx-comments">
						<div v-for="c in comments" :key="c.name" class="pjx-comment">
							<Avatar :label="c.author_name" size="md" />
							<div class="pjx-comment__body">
								<div class="pjx-comment__head">
									<strong>{{ c.author_name }}</strong>
									<span class="pjx-comment__when">{{ relativeTime(c.creation) }} ago</span>
								</div>
								<!-- eslint-disable-next-line vue/no-v-html -->
								<p class="pjx-comment__text" v-html="c.content" />
								<div class="pjx-react-row">
									<button
										v-for="[emoji, users] in reactionEntries(c)"
										:key="emoji"
										class="pjx-react"
										@click="react(c, emoji)"
									>
										{{ emoji }} {{ users.length }}
									</button>
									<Dropdown
										:options="REACTIONS.map((e) => ({ label: e, onClick: () => react(c, e) }))"
									>
										<button class="pjx-react"><Icon name="smile-plus" :size="12" /></button>
									</Dropdown>
								</div>
							</div>
						</div>
						<div v-if="!comments.length" class="pjx-inbox__empty">No comments yet — start the thread.</div>
						<div class="pjx-commentbox">
							<div class="pjx-commentbox__field" style="position: relative">
								<textarea
									ref="commentInput"
									v-model="newComment"
									class="pjx-commentbox__input"
									placeholder="Leave a comment… use @ to mention"
									style="width: 100%; border: 0; outline: 0; resize: vertical; background: transparent; font-family: var(--font-sans)"
									@input="onCommentInput"
									@keydown.meta.enter="postComment"
									@keydown.enter="onCommentEnter"
									@keydown.down.prevent="mention.open && mentionNav(1)"
									@keydown.up.prevent="mention.open && mentionNav(-1)"
									@keydown.esc="mention.open = false"
								/>
								<div v-if="mention.open && mentionPeople.length" class="pjx-mentions">
									<button
										v-for="(u, idx) in mentionPeople"
										:key="u.name"
										class="pjx-mentions__item"
										:class="{ 'is-active': idx === mention.active }"
										@mousedown.prevent="pickMention(u)"
									>
										<Avatar :label="u.full_name || u.name" :image="u.user_image" size="sm" />
										<span class="pjx-mentions__name">{{ u.full_name || u.name }}</span>
										<span class="pjx-mentions__email">{{ u.name }}</span>
									</button>
								</div>
								<div class="pjx-commentbox__foot">
									<span style="flex: 1" />
									<Button variant="solid" theme="gray" @click="postComment">Comment</Button>
								</div>
							</div>
						</div>
					</div>

					<div v-else-if="tab === 'activity'" class="pjx-activity">
						<div class="pjx-inbox__empty">See the project Summary for the full activity feed.</div>
					</div>

					<div v-else-if="tab === 'files'" class="pjx-files">
						<label class="pjx-upload">
							<Icon name="paperclip" :size="14" />
							<span>{{ uploading ? 'Uploading…' : 'Attach a file' }}</span>
							<input type="file" hidden @change="onUpload" />
						</label>
						<div v-for="f in attachments" :key="f.name" class="pjx-file">
							<Icon name="file" :size="16" class="ink-5" />
							<a class="pjx-file__name" :href="f.file_url" target="_blank">{{ f.file_name }}</a>
							<span class="pjx-file__meta">{{ fmtSize(f.file_size) }}</span>
							<Button variant="ghost" theme="gray" @click="removeAttachment(f.name)">
								<template #icon><Icon name="x" :size="14" /></template>
							</Button>
						</div>
						<div v-if="!attachments.length" class="pjx-inbox__empty">No files attached yet.</div>
					</div>

					<div v-else-if="tab === 'links'" class="pjx-linked">
						<div v-for="l in links" :key="l.name" class="pjx-linked__row">
							<span class="pjx-linked__rel">{{ l.link_type }}</span>
							<span class="pjx-id">{{ l.target }}</span>
							<span style="flex: 1">{{ l.target_title }}</span>
							<Button variant="ghost" theme="gray" @click="removeLink(l.name)">
								<template #icon><Icon name="x" :size="14" /></template>
							</Button>
						</div>
						<div class="pjx-linkadd">
							<div style="width: 130px">
								<SelectField
									:options="LINK_TYPES.map((t) => ({ value: t, label: t }))"
									:model-value="newLinkType"
									@change="(v) => (newLinkType = v || 'blocks')"
								/>
							</div>
							<div style="flex: 1">
								<SelectField
									:options="linkTargetOptions"
									:model-value="newLinkTarget"
									placeholder="Pick a task"
									@change="(v) => (newLinkTarget = v || '')"
								/>
							</div>
							<Button variant="subtle" theme="gray" :disabled="!newLinkTarget" @click="addLink">Link</Button>
						</div>
					</div>

					<div v-else-if="tab === 'dev'" class="pjx-dev">
						<div class="pjx-dev__branch">
							<div class="flex col g-1" style="min-width: 0; flex: 1">
								<span class="t-xs ink-5">Branch name</span>
								<code class="pjx-dev__code">{{ branchName }}</code>
							</div>
							<Button variant="subtle" @click="copyText(branchName)">
								<template #prefix><Icon name="copy" :size="14" /></template>Copy
							</Button>
						</div>

						<div v-if="githubLinks.length" class="pjx-dev__head">
							<span class="t-xs ink-5">{{ githubLinks.length }} linked</span>
							<Button variant="ghost" :loading="ghRefresh.loading" @click="refreshGithub">
								<template #prefix><Icon name="rotate-ccw" :size="13" /></template>Refresh
							</Button>
						</div>

						<div v-for="l in githubLinks" :key="l.name" class="pjx-dev__row">
							<a class="pjx-dev__link" :href="l.url" target="_blank" rel="noopener">
								<Icon :name="l.kind === 'Commit' ? 'git-pull-request' : 'github'" :size="15" class="ink-6 shrink-0" />
								<span class="pjx-dev__title">
									<span class="pjx-dev__name">{{ l.repository }}<template v-if="l.number">#{{ l.number }}</template></span>
									<span class="ink-5">{{ l.title }}</span>
								</span>
							</a>
							<span v-if="l.ci_status" class="pjx-dev__ci" :class="`is-${l.ci_status}`" :title="`CI ${l.ci_status}`" />
							<span class="pjx-dev__badge" :class="`is-${(GH_STATE[l.state] || {}).tone}`">
								{{ (GH_STATE[l.state] || {}).label || l.state }}
							</span>
							<button class="pjx-dev__x" title="Unlink" @click="removeGithubLink(l.name)">
								<Icon name="x" :size="13" />
							</button>
						</div>

						<div v-if="!githubLinks.length" class="pjx-inbox__empty">
							No pull requests yet. Include <strong>{{ issue?.issue_id }}</strong> in a branch or PR to link it here.
						</div>
					</div>
				</div>

				<div class="pjx-drawer__side">
					<div class="pjx-field">
						<div class="pjx-field__lbl">Assignees</div>
						<SelectField
							:options="userOptions"
							:model-value="issue.assignees"
							multiple
							placeholder="Unassigned"
							@change="setAssignees"
						/>
					</div>
					<div class="pjx-field">
						<div class="pjx-field__lbl">Reporter</div>
						<div class="pjx-field__val">{{ userName(issue.reporter) }}</div>
					</div>
					<div class="pjx-field">
						<div class="pjx-field__lbl">Labels</div>
						<SelectField :options="labelOptions" :model-value="labelIds" multiple placeholder="None" @change="setLabels" />
					</div>
					<div class="pjx-field">
						<div class="pjx-field__lbl">Cycle</div>
						<SelectField
							:options="cycleOptions"
							:model-value="issue.cycle"
							placeholder="No cycle"
							@change="(v) => changeField('cycle', v || null)"
						/>
					</div>
					<div class="pjx-field">
						<div class="pjx-field__lbl">Project</div>
						<div class="pjx-field__val">{{ issue.project }}</div>
					</div>
					<div class="pjx-field">
						<div class="pjx-field__lbl">Start date</div>
						<div class="pjx-field__val">
							<DatePicker
								:model-value="issue.start_date || ''"
								placeholder="No date"
								@update:model-value="(v) => changeField('start_date', v || null)"
							/>
						</div>
					</div>
					<div class="pjx-field">
						<div class="pjx-field__lbl">Due</div>
						<div class="pjx-field__val">
							<DatePicker
								:model-value="issue.due_date || ''"
								placeholder="No date"
								@update:model-value="(v) => changeField('due_date', v || null)"
							/>
						</div>
					</div>
					<div class="pjx-field">
						<div class="pjx-field__lbl">Estimate</div>
						<div class="pjx-field__val">
							<input
								type="number"
								min="0"
								class="pjx-inlineinput"
								style="width: 70px"
								:value="issue.estimate || ''"
								@change="(e) => changeField('estimate', Number(e.target.value) || 0)"
							/>
							<span class="t-xs ink-5">points</span>
						</div>
					</div>

					<div class="pjx-field">
						<div class="pjx-field__lbl">Repeat</div>
						<SelectField
							:options="RECURRENCE_OPTIONS"
							:model-value="issue.recurrence || 'None'"
							placeholder="Never"
							@change="(v) => changeField('recurrence', v || 'None')"
						/>
					</div>

					<div class="pjx-field">
						<div class="pjx-field__lbl">Pending</div>
						<div class="pjx-field__val flex" style="gap: 6px; flex-wrap: wrap">
							<span class="pjx-age" :data-level="ageChip(issue.status_changed_on, issue.modified).level">{{ ageChip(issue.status_changed_on, issue.modified).label || '—' }} in status</span>
							<span v-if="issue.reopen_count" class="pjx-rwk" title="Times reopened"><Icon name="undo-2" :size="12" />{{ issue.reopen_count }} reopened</span>
							<span v-if="issue.rework_count" class="pjx-rwk" title="Times sent back"><Icon name="rotate-ccw" :size="12" />{{ issue.rework_count }} reworked</span>
						</div>
					</div>

					<div v-if="integration.data?.timesheet" class="pjx-field">
						<div class="pjx-field__lbl">Time (ERPNext)</div>
						<div class="pjx-field__val flex col" style="align-items: flex-start; gap: 4px">
							<Button variant="subtle" theme="gray" size="sm" @click="logTimeOpen = true">
								<template #prefix><Icon name="clock" :size="13" /></template>
								Log time
							</Button>
							<div v-for="(t, i) in timeLogs.data || []" :key="i" class="t-xs ink-6">
								{{ t.hours }}h · {{ t.billed ? 'billed' : 'unbilled' }}
							</div>
						</div>
					</div>

					<div class="pjx-sideblock">
						<div class="pjx-sideblock__h">Created</div>
						<div class="pjx-sideblock__t">{{ relativeTime(issue.creation) }} ago</div>
						<div class="pjx-sideblock__h" style="margin-top: 8px">Last updated</div>
						<div class="pjx-sideblock__t">{{ relativeTime(issue.modified) }} ago</div>
					</div>

					</div>
			</div>
			<div v-else class="pjx-drawer__body" style="padding: 40px">
				<span class="t-sm ink-5">Loading…</span>
			</div>
		</aside>
		<LogTimeDialog
			v-if="issue"
			:open="logTimeOpen"
			:issue="issue.name"
			@close="logTimeOpen = false"
			@logged="timeLogs.submit({ issue: issue.name })"
		/>
	</div>
</template>

<style scoped>
.pjx-check__row {
	align-items: center;
}
.pjx-check__del {
	margin-left: auto;
	border: 0;
	background: transparent;
	color: var(--ink-gray-4);
	cursor: pointer;
	opacity: 0;
	display: inline-flex;
	padding: 2px;
	border-radius: 4px;
}
.pjx-check__row:hover .pjx-check__del {
	opacity: 1;
}
.pjx-check__del:hover {
	color: var(--ink-gray-7);
	background: var(--surface-gray-2);
}
.pjx-check__add {
	width: 100%;
	margin-top: 4px;
	border: 0;
	outline: 0;
	background: transparent;
	font-size: 13px;
	color: var(--ink-gray-8);
	font-family: var(--font-sans);
	padding: 4px 2px;
}
.pjx-check__add::placeholder {
	color: var(--ink-gray-4);
}
.pjx-mentions {
	position: absolute;
	left: 0;
	bottom: calc(100% + 4px);
	z-index: 20;
	width: 260px;
	max-height: 240px;
	overflow-y: auto;
	background: var(--surface-white);
	border: 1px solid var(--outline-gray-2);
	border-radius: 8px;
	box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
	padding: 4px;
}
.pjx-mentions__item {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	padding: 5px 8px;
	border: 0;
	border-radius: 6px;
	background: transparent;
	cursor: pointer;
	text-align: left;
}
.pjx-mentions__item:hover,
.pjx-mentions__item.is-active {
	background: var(--surface-gray-2);
}
.pjx-mentions__name {
	font-size: 13px;
	color: var(--ink-gray-8);
	font-weight: 500;
}
.pjx-mentions__email {
	font-size: 11px;
	color: var(--ink-gray-5);
	margin-left: auto;
}
.pjx-inlineinput {
	border: 1px solid transparent;
	background: transparent;
	border-radius: 6px;
	padding: 2px 6px;
	font-size: 13px;
	color: var(--ink-gray-8);
	font-family: var(--font-sans);
}
.pjx-inlineinput:hover {
	background: var(--surface-gray-2);
}
.pjx-inlineinput:focus {
	outline: none;
	background: var(--surface-white);
	border-color: var(--outline-gray-3);
}
.pjx-descwrap {
	margin: 10px 0 4px;
}
.pjx-desc__head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 4px;
}
.pjx-desc__edit {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	border: 0;
	background: transparent;
	cursor: pointer;
	color: var(--ink-gray-5);
	font-size: 12px;
	border-radius: 5px;
	padding: 2px 6px;
}
.pjx-desc__edit:hover {
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
}
.pjx-desc {
	cursor: text;
	border-radius: 8px;
}
.pjx-desc:hover {
	background: var(--surface-gray-1);
}
.pjx-descempty {
	color: var(--ink-gray-4);
}
.pjx-descarea {
	width: 100%;
	border: 1px solid var(--outline-gray-2);
	border-radius: 8px;
	padding: 10px 12px;
	font-size: 13px;
	line-height: 1.55;
	color: var(--ink-gray-8);
	font-family: var(--font-sans);
	resize: vertical;
	background: var(--surface-white);
}
.pjx-descarea:focus {
	outline: none;
	border-color: var(--outline-gray-3);
}
.pjx-upload {
	display: inline-flex;
	align-items: center;
	gap: 8px;
	padding: 8px 12px;
	border: 1px dashed var(--outline-gray-2);
	border-radius: 8px;
	cursor: pointer;
	font-size: 13px;
	color: var(--ink-gray-6);
	margin-bottom: 10px;
}
.pjx-upload:hover {
	background: var(--surface-gray-1);
}
.pjx-linkadd {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-top: 12px;
	padding-top: 12px;
	border-top: 1px solid var(--outline-gray-1);
}

/* Development tab: branch helper + PR links */
.pjx-dev {
	display: flex;
	flex-direction: column;
	gap: 8px;
}
.pjx-dev__branch {
	display: flex;
	align-items: flex-end;
	gap: 8px;
	padding-bottom: 4px;
}
.pjx-dev__code {
	overflow-x: auto;
	white-space: nowrap;
	padding: 6px 8px;
	border-radius: 6px;
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
	font-size: 12px;
}
.pjx-dev__head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-top: 2px;
}
.pjx-dev__row {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 8px 10px;
	border: 1px solid var(--outline-gray-1);
	border-radius: 8px;
}
.pjx-dev__row:hover {
	background: var(--surface-gray-1);
}
.pjx-dev__link {
	display: flex;
	align-items: center;
	gap: 10px;
	min-width: 0;
	flex: 1;
	text-decoration: none;
	color: inherit;
}
.pjx-dev__x {
	display: grid;
	place-items: center;
	width: 22px;
	height: 22px;
	border: none;
	border-radius: 6px;
	background: none;
	color: var(--ink-gray-5);
	cursor: pointer;
	flex-shrink: 0;
}
.pjx-dev__x:hover {
	background: var(--surface-gray-3);
	color: var(--ink-gray-7);
}
.pjx-dev__title {
	display: flex;
	flex-direction: column;
	gap: 1px;
	min-width: 0;
	flex: 1;
}
.pjx-dev__name {
	font-size: 13px;
	font-weight: 500;
	color: var(--ink-gray-8);
}
.pjx-dev__title .ink-5 {
	font-size: 12px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.pjx-dev__ci {
	width: 8px;
	height: 8px;
	border-radius: 999px;
	flex-shrink: 0;
	background: var(--ink-gray-4);
}
.pjx-dev__ci.is-success {
	background: var(--green-500);
}
.pjx-dev__ci.is-failure {
	background: var(--red-500, #e03636);
}
.pjx-dev__ci.is-pending {
	background: var(--amber-500, #efad3a);
}
.pjx-dev__badge {
	flex-shrink: 0;
	padding: 2px 8px;
	border-radius: 999px;
	font-size: 11px;
	font-weight: 500;
	background: var(--surface-gray-2);
	color: var(--ink-gray-6);
}
.pjx-dev__badge.is-green {
	background: var(--surface-green-1);
	color: var(--ink-green-3);
}
.pjx-dev__badge.is-purple {
	background: color-mix(in srgb, var(--purple-500, #7c5cff) 14%, transparent);
	color: var(--purple-600, #6c4ce0);
}
.pjx-dev__badge.is-red {
	background: color-mix(in srgb, var(--red-500, #e03636) 12%, transparent);
	color: var(--red-600, #c62d2d);
}
</style>
