<script setup>
import { computed } from 'vue'
import { SettingsHeader, SettingsBody } from 'frappe-ui'
import Icon from '../../Icon.vue'

// ERPNext has no credentials to enter: it's "connected" when the app is present
// on the site. This panel is pure status + what it unlocks. Per-project links
// (which ERPNext Customer/Project a projex project rolls up into) still live in
// Project settings, because that binding is genuinely per-project.
const props = defineProps({
	status: { type: Object, required: true }, // integration_status payload
})
defineEmits(['back'])

const installed = computed(() => !!props.status.erpnext)
</script>

<template>
	<SettingsHeader title="ERPNext">
		<template #actions>
			<button class="pjx-back t-sm ink-6" @click="$emit('back')">
				<Icon name="chevron-left" :size="15" /> Integrations
			</button>
		</template>
	</SettingsHeader>
	<SettingsBody>
		<div class="flex col g-3" style="padding-top: 8px">
			<div class="pjx-status" :class="installed ? 'is-on' : 'is-off'">
				<Icon :name="installed ? 'circle-check-big' : 'circle-dot'" :size="16" />
				<span>{{ installed ? 'Detected on your site' : 'Not installed' }}</span>
			</div>

			<template v-if="installed">
				<p class="t-sm ink-5">
					ERPNext is installed, so projects can roll up cost, revenue and gross margin into the
					Finance tab, and issues can log billable time to ERPNext Timesheets.
				</p>
				<p class="t-xs ink-4">
					Link a project to an ERPNext Customer/Project from that project's settings under Integrations.
				</p>
			</template>
			<p v-else class="t-sm ink-5">
				ERPNext isn't installed on this site, so project accounting and billable timesheets are
				unavailable. Flow-time metrics on the Timesheets tab work without it. Install the ERPNext app
				on your bench to enable the finance features.
			</p>
		</div>
	</SettingsBody>
</template>

<style scoped>
.pjx-back {
	display: inline-flex;
	align-items: center;
	gap: 2px;
	background: none;
	border: none;
	cursor: pointer;
	padding: 0;
}
.pjx-status {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	align-self: flex-start;
	padding: 4px 10px;
	border-radius: 6px;
	font-size: 13px;
	font-weight: 450;
}
.pjx-status.is-on {
	color: var(--ink-green-3);
	background: var(--surface-green-1);
	border: 1px solid var(--outline-green-1);
}
.pjx-status.is-off {
	color: var(--ink-gray-6);
	background: var(--surface-gray-1);
	border: 1px solid var(--outline-gray-1);
}
</style>
