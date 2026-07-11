<script setup>
import { ref, computed } from 'vue'
import { createResource, Button, FormControl, SettingsHeader, SettingsBody } from 'frappe-ui'
import Icon from '../Icon.vue'
import { PROJECT_COLORS } from './projectColors'

const props = defineProps({
	project: { type: String, required: true },
	data: { type: Object, required: true }, // get_project_detail payload
})
const emit = defineEmits(['reload'])

const labelCreate = createResource({ url: 'projex.api.create_label' })
const labelDelete = createResource({ url: 'projex.api.delete_label' })

const newLabel = ref({ name: '', color: PROJECT_COLORS[0] })
const canManage = computed(() => props.data?.project?.can_manage)
const labels = computed(() => props.data?.labels || [])

async function addLabel() {
	if (!newLabel.value.name.trim()) return
	await labelCreate.submit({ project: props.project, label_name: newLabel.value.name.trim(), color: newLabel.value.color })
	newLabel.value = { name: '', color: PROJECT_COLORS[0] }
	emit('reload')
}
async function removeLabel(name) {
	await labelDelete.submit({ name })
	emit('reload')
}
</script>

<template>
	<SettingsHeader title="Labels" :description="`${data.project?.project_name || project} · ${data.project?.key || project}`" />
	<SettingsBody>
		<div class="flex col g-3" style="padding-top: 8px">
			<div v-if="!canManage" class="t-sm ink-5">You have read-only access to this project's settings.</div>
			<div class="flex wrap g-2">
				<span v-for="l in labels" :key="l.name" class="pjx-label">
					<span class="pjx-label__dot" :style="{ background: l.color }" />
					{{ l.label_name }}
					<button v-if="canManage" class="pjx-chip__x" @click="removeLabel(l.name)"><Icon name="x" :size="11" /></button>
				</span>
				<span v-if="!labels.length" class="pjx-dim t-xs">No project labels yet.</span>
			</div>
			<div v-if="canManage" class="flex g-2 items-end">
				<div class="flex col g-1" style="flex: 1">
					<span class="t-xs ink-5">New label</span>
					<FormControl v-model="newLabel.name" type="text" placeholder="e.g. frontend" />
				</div>
				<div class="flex g-1">
					<button v-for="c in PROJECT_COLORS" :key="c" class="pjx-sw sm" :class="{ on: newLabel.color === c }" :style="{ background: c }" @click="newLabel.color = c" />
				</div>
				<Button variant="subtle" theme="gray" @click="addLabel">Add</Button>
			</div>
		</div>
	</SettingsBody>
</template>

<style scoped>
.pjx-sw {
	width: 24px;
	height: 24px;
	border-radius: 9999px;
	border: 2px solid transparent;
	cursor: pointer;
}
.pjx-sw.sm {
	width: 20px;
	height: 20px;
}
.pjx-sw.on {
	border-color: var(--ink-gray-9);
}
</style>
