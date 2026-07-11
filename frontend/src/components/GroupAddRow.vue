<script setup>
import { nextTick, ref } from 'vue'
import { createResource } from 'frappe-ui'
import Icon from './Icon.vue'

// Quiet inline add-row at the end of a task group. `fields` carries the
// group's context (status or priority) so the new task lands in place.
const props = defineProps({
	projectKey: { type: String, required: true },
	fields: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['created'])

const editing = ref(false)
const title = ref('')
const inputEl = ref(null)
const creator = createResource({ url: 'projex.api.create_issue' })

async function start() {
	editing.value = true
	await nextTick()
	inputEl.value?.focus()
}

function stop() {
	editing.value = false
	title.value = ''
}

async function submit() {
	const t = title.value.trim()
	if (!t || creator.loading) return
	await creator.submit({ payload: { title: t, project: props.projectKey, ...props.fields } })
	title.value = ''
	emit('created')
	inputEl.value?.focus()
}
</script>

<template>
	<button v-if="!editing" class="pjx-addrow" @click="start">
		<Icon name="plus" :size="14" />
		<span>Add task</span>
	</button>
	<div v-else class="pjx-addrow pjx-addrow--edit">
		<Icon name="plus" :size="14" />
		<input
			ref="inputEl"
			v-model="title"
			class="pjx-addrow__input"
			placeholder="Task title, press Enter"
			@keydown.enter="submit"
			@keydown.esc="stop"
			@blur="!title.trim() && stop()"
		/>
	</div>
</template>

<style scoped>
/* Indent matches ListRow's lane: px-2 (8px) + 14px checkbox column + gap-4 (16px). */
.pjx-addrow { display: flex; align-items: center; gap: 8px; width: 100%; height: 36px; padding: 0 8px 0 38px; border: 0; background: transparent; border-radius: 8px; font-size: 13px; color: var(--ink-gray-5); cursor: pointer; text-align: left; }
.pjx-addrow:hover { background: var(--surface-gray-1); color: var(--ink-gray-7); }
.pjx-addrow--edit { cursor: text; color: var(--ink-gray-7); }
.pjx-addrow__input { flex: 1; border: 0; outline: 0; background: transparent; font-size: 13px; color: var(--ink-gray-9); }
.pjx-addrow__input::placeholder { color: var(--ink-gray-4); }
</style>
