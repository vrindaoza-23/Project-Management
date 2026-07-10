<script setup>
import { ref, computed, watch } from 'vue'
import { createResource, Button, Dropdown, FormControl, DatePicker, TextEditor } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import { relativeTime } from '@/utils/format'
import { notify, notifyError, confirm } from '@/utils/feedback'

const props = defineProps({ projectKey: { type: String, required: true } })

const DOC_TYPES = ['PRD', 'BRD', 'Standup MOM', 'Change Request', 'Note']
const TYPE_ICON = { PRD: 'file-text', BRD: 'briefcase', 'Standup MOM': 'users', 'Change Request': 'git-pull-request', Note: 'sticky-note' }

// Rich-text (HTML) starter content for the editor.
const TEMPLATES = {
	PRD: `<h2>Overview</h2><p>What are we building and why?</p><h2>Goals</h2><ul><li></li></ul><h2>Non-goals</h2><ul><li></li></ul><h2>Requirements</h2><ol><li></li></ol><h2>Success metrics</h2><ul><li></li></ul>`,
	BRD: `<h2>Business need</h2><p></p><h2>Scope</h2><p></p><h2>Stakeholders</h2><ul><li></li></ul><h2>Requirements</h2><ol><li></li></ol><h2>Risks &amp; assumptions</h2><ul><li></li></ul>`,
	'Standup MOM': `<p><strong>Date:</strong> </p><p><strong>Attendees:</strong> </p><h3>Yesterday</h3><ul><li></li></ul><h3>Today</h3><ul><li></li></ul><h3>Blockers</h3><ul><li></li></ul>`,
	'Change Request': `<h2>Change</h2><p>What is changing?</p><h2>Reason</h2><p></p><h2>Impact</h2><p></p><h2>Approval</h2><ul><li>Requested by: </li><li>Approved by: </li></ul>`,
	Note: '',
}

// Old docs were stored as plain text; new docs are HTML. Render HTML as-is,
// but keep whitespace for legacy plain-text content so it doesn't collapse.
const looksLikeHtml = (s) => typeof s === 'string' && /<[a-z][\s\S]*>/i.test(s)

const list = createResource({
	url: 'projex.api.get_docs',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
const detail = createResource({ url: 'projex.api.get_doc_detail' })
const creator = createResource({ url: 'projex.api.create_doc' })
const updater = createResource({ url: 'projex.api.update_doc' })
const remover = createResource({ url: 'projex.api.delete_doc_entry' })

watch(() => props.projectKey, () => { list.reload(); selected.value = null })

const filter = ref('All')
const selected = ref(null)
const editing = ref(false)
const draft = ref({ title: '', doc_type: 'Note', doc_date: '', content: '' })

const docs = computed(() => {
	const all = list.data || []
	return filter.value === 'All' ? all : all.filter((d) => d.doc_type === filter.value)
})
const current = computed(() => detail.data)

function selectDoc(name) {
	editing.value = false
	selected.value = name
	detail.submit({ name })
}

function newDoc(type) {
	selected.value = null
	editing.value = true
	draft.value = { title: '', doc_type: type, doc_date: '', content: TEMPLATES[type] || '' }
}

function editCurrent() {
	if (!current.value) return
	draft.value = {
		title: current.value.title,
		doc_type: current.value.doc_type,
		doc_date: current.value.doc_date || '',
		content: current.value.content || '',
	}
	editing.value = true
}

async function save() {
	if (!draft.value.title.trim()) return
	if (selected.value) {
		await updater.submit({ name: selected.value, fields: JSON.stringify(draft.value) })
		await detail.submit({ name: selected.value })
	} else {
		const res = await creator.submit({
			project: props.projectKey,
			title: draft.value.title.trim(),
			doc_type: draft.value.doc_type,
			content: draft.value.content,
			doc_date: draft.value.doc_date || null,
		})
		selected.value = res.name
		await detail.submit({ name: res.name })
	}
	editing.value = false
	list.reload()
}

async function removeDoc() {
	if (!selected.value) return
	const ok = await confirm({
		title: 'Delete document',
		message: 'This document will be permanently deleted.',
		confirmLabel: 'Delete',
		theme: 'red',
	})
	if (!ok) return
	try {
		await remover.submit({ name: selected.value })
		selected.value = null
		list.reload()
		notify.success('Document deleted')
	} catch (e) {
		notifyError(e, 'Could not delete document')
	}
}

const newOptions = DOC_TYPES.map((t) => ({ label: t, onClick: () => newDoc(t) }))
</script>

<template>
	<div class="pjx-docs">
		<!-- list pane -->
		<div class="pjx-docs__list">
			<div class="pjx-docs__lhead">
				<Dropdown :options="newOptions">
					<Button variant="solid" theme="blue" size="sm" style="width: 100%">
						<template #prefix><Icon name="plus" :size="14" /></template>New document
					</Button>
				</Dropdown>
			</div>
			<div class="pjx-docs__filters">
				<button class="pjx-chip" :class="{ on: filter === 'All' }" @click="filter = 'All'">All</button>
				<button v-for="t in DOC_TYPES" :key="t" class="pjx-chip" :class="{ on: filter === t }" @click="filter = t">{{ t }}</button>
			</div>
			<div class="pjx-docs__items">
				<button
					v-for="doc in docs"
					:key="doc.name"
					class="pjx-docitem"
					:class="{ on: selected === doc.name }"
					@click="selectDoc(doc.name)"
				>
					<Icon :name="TYPE_ICON[doc.doc_type] || 'file-text'" :size="15" class="ink-5" />
					<span class="pjx-docitem__body">
						<span class="pjx-docitem__t">{{ doc.title }}</span>
						<span class="pjx-docitem__m">{{ doc.doc_type }} · {{ relativeTime(doc.modified) }} ago</span>
					</span>
				</button>
				<div v-if="!docs.length" class="pjx-dim t-sm" style="padding: 12px">No documents yet.</div>
			</div>
		</div>

		<!-- detail / editor pane -->
		<div class="pjx-docs__detail">
			<template v-if="editing">
				<input v-model="draft.title" class="pjx-docs__title-input" placeholder="Document title" />
				<div class="pjx-docs__meta">
					<div style="width: 200px">
						<FormControl
							v-model="draft.doc_type"
							type="select"
							size="sm"
							:options="DOC_TYPES.map((t) => ({ value: t, label: t }))"
						/>
					</div>
					<div style="width: 180px">
						<DatePicker v-model="draft.doc_date" placeholder="Date" />
					</div>
				</div>
				<TextEditor
					class="pjx-docs__editor"
					:content="draft.content"
					:fixed-menu="true"
					placeholder="Write your document…"
					editor-class="pjx-docs__prose"
					@change="(html) => (draft.content = html)"
				/>
				<div class="flex g-2" style="margin-top: 10px">
					<Button variant="solid" theme="blue" :loading="creator.loading || updater.loading" @click="save">Save</Button>
					<Button variant="subtle" theme="gray" @click="editing = false">Cancel</Button>
				</div>
			</template>

			<template v-else-if="current">
				<div class="pjx-docs__dhead">
					<div>
						<h2 class="pjx-docs__h2">{{ current.title }}</h2>
						<div class="pjx-docs__sub">
							{{ current.doc_type }}<template v-if="current.doc_date"> · {{ current.doc_date }}</template>
							· {{ current.owner_name }} · updated {{ relativeTime(current.modified) }} ago
						</div>
					</div>
					<div class="flex g-2">
						<Button variant="subtle" theme="gray" size="sm" @click="editCurrent">
							<template #prefix><Icon name="pencil" :size="13" /></template>Edit
						</Button>
						<Button variant="ghost" theme="gray" size="sm" @click="removeDoc">
							<template #icon><Icon name="trash-2" :size="15" /></template>
						</Button>
					</div>
				</div>
				<div
					v-if="looksLikeHtml(current.content)"
					class="pjx-docs__content pjx-docs__prose"
					v-html="current.content"
				/>
				<div v-else class="pjx-docs__content" style="white-space: pre-wrap">
					{{ current.content || 'This document is empty. Click Edit to add content.' }}
				</div>
			</template>

			<div v-else class="pjx-docs__empty">
				<Icon name="file-text" :size="28" class="ink-4" />
				<p class="t-sm ink-5">Select a document, or create a PRD, BRD, standup MOM or change request.</p>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-docs { display: grid; grid-template-columns: 280px 1fr; height: 100%; overflow: hidden; }
.pjx-docs__list { border-right: 1px solid var(--outline-gray-1); display: flex; flex-direction: column; min-height: 0; }
.pjx-docs__lhead { padding: 12px; }
.pjx-docs__filters { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 12px 10px; }
.pjx-chip { border: 1px solid var(--outline-gray-2); background: transparent; border-radius: 9999px; padding: 2px 10px; font-size: 11px; color: var(--ink-gray-6); cursor: pointer; }
.pjx-chip.on { background: var(--surface-gray-3); color: var(--ink-gray-9); border-color: transparent; }
.pjx-docs__items { flex: 1; overflow-y: auto; padding: 0 8px 8px; }
.pjx-docitem { display: flex; align-items: center; gap: 10px; width: 100%; text-align: left; border: 0; background: transparent; padding: 9px 8px; border-radius: 8px; cursor: pointer; }
.pjx-docitem:hover { background: var(--surface-gray-1); }
.pjx-docitem.on { background: var(--surface-gray-2); }
.pjx-docitem__body { display: flex; flex-direction: column; min-width: 0; }
.pjx-docitem__t { font-size: 13px; font-weight: 500; color: var(--ink-gray-9); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pjx-docitem__m { font-size: 11px; color: var(--ink-gray-5); }
.pjx-docs__detail { padding: 20px 24px; overflow-y: auto; min-height: 0; }
.pjx-docs__title-input { width: 100%; font-size: 22px; font-weight: 600; border: 0; outline: 0; color: var(--ink-gray-9); background: transparent; margin-bottom: 10px; }
.pjx-docs__meta { display: flex; gap: 10px; margin-bottom: 12px; }
.pjx-docs__editor { border: 1px solid var(--outline-gray-2); border-radius: 10px; overflow: hidden; }
.pjx-docs__editor :deep(.ProseMirror) { min-height: 320px; padding: 14px 16px; }
.pjx-docs__editor :deep(.ProseMirror:focus) { outline: none; }
.pjx-docs__dhead { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.pjx-docs__h2 { font-size: 22px; font-weight: 600; color: var(--ink-gray-9); }
.pjx-docs__sub { font-size: 12px; color: var(--ink-gray-5); margin-top: 4px; }
.pjx-docs__content { font-size: 14px; line-height: 1.7; color: var(--ink-gray-8); }
/* Prose typography for rendered rich-text (both editor and read view). */
.pjx-docs__prose :deep(h1), .pjx-docs__prose h1 { font-size: 20px; font-weight: 600; color: var(--ink-gray-9); margin: 16px 0 8px; }
.pjx-docs__prose :deep(h2), .pjx-docs__prose h2 { font-size: 17px; font-weight: 600; color: var(--ink-gray-9); margin: 14px 0 6px; }
.pjx-docs__prose :deep(h3), .pjx-docs__prose h3 { font-size: 14px; font-weight: 600; color: var(--ink-gray-9); margin: 12px 0 4px; }
.pjx-docs__prose :deep(p), .pjx-docs__prose p { margin: 6px 0; }
.pjx-docs__prose :deep(ul), .pjx-docs__prose ul { list-style: disc; padding-left: 22px; margin: 6px 0; }
.pjx-docs__prose :deep(ol), .pjx-docs__prose ol { list-style: decimal; padding-left: 22px; margin: 6px 0; }
.pjx-docs__prose :deep(a), .pjx-docs__prose a { color: var(--ink-blue-2); text-decoration: underline; }
.pjx-docs__prose :deep(blockquote), .pjx-docs__prose blockquote { border-left: 3px solid var(--outline-gray-3); padding-left: 12px; color: var(--ink-gray-6); margin: 8px 0; }
.pjx-docs__prose :deep(code), .pjx-docs__prose code { font-family: var(--font-mono); background: var(--surface-gray-2); padding: 1px 5px; border-radius: 4px; font-size: 12px; }
.pjx-docs__empty { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; text-align: center; }
</style>
