<script setup>
import { computed } from 'vue'
import { Dialog, FormControl } from 'frappe-ui'
import { confirmState, resolveConfirm, promptState, resolvePrompt } from '@/utils/feedback'

// Renders the app-wide promise-based confirm() and promptText() dialogs.
// Mounted once at the root.
const confirmOptions = computed(() => ({
	title: confirmState.title,
	actions: [
		{
			label: confirmState.confirmLabel,
			variant: 'solid',
			theme: confirmState.theme,
			onClick: () => resolveConfirm(true),
		},
		{ label: confirmState.cancelLabel, variant: 'subtle', onClick: () => resolveConfirm(false) },
	],
}))

const promptOptions = computed(() => ({
	title: promptState.title,
	actions: [
		{
			label: promptState.confirmLabel,
			variant: 'solid',
			onClick: () => resolvePrompt(promptState.value.trim()),
		},
		{ label: 'Cancel', variant: 'subtle', onClick: () => resolvePrompt(null) },
	],
}))

function onConfirmClose() {
	if (confirmState.open) resolveConfirm(false)
}
function onPromptClose() {
	if (promptState.open) resolvePrompt(null)
}
</script>

<template>
	<Dialog v-model="confirmState.open" :options="confirmOptions" @close="onConfirmClose">
		<template #body-content>
			<p v-if="confirmState.message" class="text-p-base text-ink-gray-6 whitespace-pre-line">
				{{ confirmState.message }}
			</p>
		</template>
	</Dialog>

	<Dialog v-model="promptState.open" :options="promptOptions" @close="onPromptClose">
		<template #body-content>
			<FormControl
				v-model="promptState.value"
				type="text"
				:label="promptState.label"
				:placeholder="promptState.placeholder"
				autofocus
				@keydown.enter="resolvePrompt(promptState.value.trim())"
			/>
		</template>
	</Dialog>
</template>
