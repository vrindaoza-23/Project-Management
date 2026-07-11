<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { createResource, Button, SettingsHeader, SettingsBody } from 'frappe-ui'
import NativeSelect from '../NativeSelect.vue'
import { notify } from '@/utils/feedback'

const props = defineProps({
	project: { type: String, required: true },
	data: { type: Object, required: true }, // get_project_detail payload
})

const erpOptions = createResource({ url: 'projex.api.erpnext_link_options' })
const linkSaver = createResource({ url: 'projex.api.set_project_links' })

const erp = ref({ customer: '', project: '' })
watch(
	() => props.data,
	(d) => {
		if (d?.project) erp.value = { customer: d.project.erpnext_customer || '', project: d.project.erpnext_project || '' }
	},
	{ immediate: true },
)

const canManage = computed(() => props.data?.project?.can_manage)
const erpInstalled = computed(() => erpOptions.data?.erpnext !== false)
const erpProjectOptions = computed(() => [{ value: '', label: '— None —' }, ...(erpOptions.data?.projects || [])])
const erpCustomerOptions = computed(() => [{ value: '', label: '— None —' }, ...(erpOptions.data?.customers || [])])

onMounted(() => {
	if (canManage.value) erpOptions.submit({ project: props.project })
})

async function save() {
	await linkSaver.submit({
		project: props.project,
		erpnext_customer: erp.value.customer || null,
		erpnext_project: erp.value.project || null,
	})
	notify.success('ERPNext links saved')
}
</script>

<template>
	<SettingsHeader title="ERPNext" :description="`${data.project?.project_name || project} · ${data.project?.key || project}`">
		<template #actions>
			<Button v-if="canManage && erpInstalled" variant="solid" theme="gray" :loading="linkSaver.loading" @click="save">Save links</Button>
		</template>
	</SettingsHeader>
	<SettingsBody>
		<div class="flex col g-3" style="padding-top: 8px">
			<template v-if="erpInstalled">
				<p class="t-sm ink-5">Link an ERPNext Project to roll up cost, revenue and gross margin into the Finance tab, and to log billable time.</p>
				<label class="flex col g-1">
					<span class="t-xs ink-5">ERPNext Project</span>
					<NativeSelect v-model="erp.project" :options="erpProjectOptions" placeholder="Select an ERPNext Project" />
				</label>
				<label class="flex col g-1">
					<span class="t-xs ink-5">ERPNext Customer <span class="ink-4">(optional)</span></span>
					<NativeSelect v-model="erp.customer" :options="erpCustomerOptions" placeholder="Select a Customer" />
				</label>
				<p v-if="!canManage" class="t-xs ink-4">Only a project admin can change these links.</p>
			</template>
			<p v-else class="t-sm ink-5">ERPNext is not installed, so project accounting and billable timesheets are unavailable. The flow-time metrics on the Timesheets tab work without it.</p>
		</div>
	</SettingsBody>
</template>
