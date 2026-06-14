<script setup>
import { ref, computed } from 'vue'
import { createResource } from 'frappe-ui'
import Icon from './Icon.vue'
import { projectByKey } from '@/data/store'

const props = defineProps({ projectKey: { type: String, required: true } })
const emit = defineEmits(['created'])

const text = ref('')
const saving = ref(false)

// Live tokenizer: @assignee (blue), !priority (amber), #label (green).
const tokens = computed(() => {
	const out = []
	const re = /(@\w+)|(!\w+)|(#\w+)/g
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

const creator = createResource({ url: 'frappe.client.insert' })

async function submit() {
	const title = text.value.replace(/[@!#]\w+/g, '').trim()
	if (!title || saving.value) return
	saving.value = true
	const priorityToken = tokens.value.find((t) => t.kind === 'priority')
	const priority = priorityToken
		? priorityToken.label.charAt(0).toUpperCase() + priorityToken.label.slice(1)
		: 'None'
	try {
		await creator.submit({
			doc: {
				doctype: 'Projex Issue',
				title,
				project: props.projectKey,
				priority: ['Urgent', 'High', 'Medium', 'Low', 'None'].includes(priority) ? priority : 'None',
			},
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
