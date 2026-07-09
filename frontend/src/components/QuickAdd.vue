<script setup>
import { ref, computed } from 'vue'
import { createResource } from 'frappe-ui'
import Icon from './Icon.vue'
import { projectByKey } from '@/data/store'

const props = defineProps({ projectKey: { type: String, required: true } })
const emit = defineEmits(['created'])

const text = ref('')
const saving = ref(false)

// Pickers give us the label + user options to resolve #label / @assignee tokens
// against real records instead of silently dropping them.
const pickers = createResource({
	url: 'projex.api.get_pickers',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})

const PRIORITIES = ['Urgent', 'High', 'Medium', 'Low', 'None']

// Live tokenizer: @assignee (blue), !priority (amber), #label (green).
const tokens = computed(() => {
	const out = []
	const re = /(@[\w.-]+)|(!\w+)|(#[\w-]+)/g
	let m
	while ((m = re.exec(text.value)) !== null) {
		const s = m[0]
		if (s[0] === '@') out.push({ kind: 'assignee', glyph: '@', label: s.slice(1) })
		else if (s[0] === '!') out.push({ kind: 'priority', glyph: '!', label: s.slice(1) })
		else out.push({ kind: 'label', glyph: '#', label: s.slice(1) })
	}
	return out
})

const projectName = computed(() => projectByKey(props.projectKey)?.project_name || props.projectKey)

const creator = createResource({ url: 'projex.api.create_issue' })

function resolveAssignee(handle) {
	const h = handle.toLowerCase()
	const users = pickers.data?.users || []
	return (
		users.find((u) => (u.name || '').toLowerCase().split('@')[0] === h) ||
		users.find((u) => (u.full_name || '').toLowerCase().split(' ')[0] === h) ||
		users.find((u) => (u.full_name || '').toLowerCase().includes(h))
	)?.name
}

function resolveLabel(handle) {
	const h = handle.toLowerCase()
	const labels = pickers.data?.labels || []
	return (
		labels.find((l) => (l.label_name || '').toLowerCase() === h) ||
		labels.find((l) => (l.label_name || '').toLowerCase().includes(h))
	)?.name
}

function normalizePriority(token) {
	if (!token) return 'None'
	const p = token.label.charAt(0).toUpperCase() + token.label.slice(1).toLowerCase()
	return PRIORITIES.includes(p) ? p : 'None'
}

async function submit() {
	const title = text.value.replace(/[@!#][\w.-]+/g, '').trim()
	if (!title || saving.value) return
	saving.value = true
	const priority = normalizePriority(tokens.value.find((t) => t.kind === 'priority'))
	const assignees = tokens.value
		.filter((t) => t.kind === 'assignee')
		.map((t) => resolveAssignee(t.label))
		.filter(Boolean)
	const labels = tokens.value
		.filter((t) => t.kind === 'label')
		.map((t) => resolveLabel(t.label))
		.filter(Boolean)
	try {
		await creator.submit({
			payload: { title, project: props.projectKey, priority, assignees, labels },
		})
		text.value = ''
		emit('created')
	} finally {
		saving.value = false
	}
}
</script>

<template>
	<div class="pjx-quickadd">
		<Icon name="plus" :size="16" class="ink-5" />
		<input
			v-model="text"
			class="pjx-quickadd__input"
			placeholder='Add task — try "Fix login bug @alice !high #frontend"'
			@keydown.enter="submit"
		/>
		<span v-for="(t, i) in tokens" :key="i" class="pjx-tok" :class="`pjx-tok--${t.kind}`"
			>{{ t.glyph }}{{ t.label }}</span
		>
		<span class="t-xs ink-4" style="flex: none">in {{ projectName }}</span>
	</div>
</template>
