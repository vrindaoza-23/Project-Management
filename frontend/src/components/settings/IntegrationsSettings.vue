<script setup>
import { ref, computed } from 'vue'
import { createResource, SettingsHeader, SettingsBody } from 'frappe-ui'
import Icon from '../Icon.vue'
import ErpNextIntegration from './integrations/ErpNextIntegration.vue'
import GithubIntegration from './integrations/GithubIntegration.vue'

// The gallery is a registry — one row per integration. Adding another is a new
// entry here plus its detail component; the nav item and layout don't change.
// `state` reads the shared integration_status payload to render each card's badge.
const INTEGRATIONS = [
	{
		key: 'erpnext',
		label: 'ERPNext',
		icon: 'link-2',
		blurb: 'Roll cost, revenue and margin into Finance, and log billable time.',
		component: ErpNextIntegration,
		state: (s) => (s.erpnext ? { label: 'Detected', tone: 'on' } : { label: 'Not installed', tone: 'off' }),
	},
	{
		key: 'github',
		label: 'GitHub',
		icon: 'github',
		blurb: 'Link pull requests to issues and move them as code ships.',
		component: GithubIntegration,
		state: (s) => (s.github ? { label: 'Connected', tone: 'on' } : { label: 'Set up', tone: 'soon' }),
	},
]

// Planned integrations — shown so the roadmap is visible, but not yet wired up.
const UPCOMING = [
	{ key: 'slack', label: 'Slack', icon: 'slack', blurb: 'Mirror notifications, unfurl issue links, create issues from chat.' },
	{ key: 'gitlab', label: 'GitLab', icon: 'gitlab', blurb: 'Link merge requests to issues and move them as code ships.' },
	{ key: 'bitbucket', label: 'Bitbucket', icon: 'git-branch', blurb: 'Link pull requests and branches to issues.' },
	{ key: 'crm', label: 'Frappe CRM', icon: 'briefcase', blurb: 'Turn deals into delivery projects, synced natively.' },
	{ key: 'helpdesk', label: 'Frappe Helpdesk', icon: 'life-buoy', blurb: 'Escalate support tickets into tracked issues.' },
	{ key: 'sentry', label: 'Sentry', icon: 'bug', blurb: 'Turn error spikes into issues automatically.' },
	{ key: 'figma', label: 'Figma', icon: 'figma', blurb: 'Preview linked designs right on the issue.' },
	{ key: 'gcal', label: 'Google Calendar', icon: 'calendar', blurb: 'Put cycles and due dates on your calendar.' },
]

const status = createResource({ url: 'projex.api.integration_status', auto: true })
const payload = computed(() => status.data || {})

const selected = ref('')
const current = computed(() => INTEGRATIONS.find((i) => i.key === selected.value))
</script>

<template>
	<component :is="current.component" v-if="current" :status="payload" @back="selected = ''" />

	<template v-else>
		<SettingsHeader title="Integrations" description="Connect Projex to the tools your team already uses." />
		<SettingsBody>
			<div class="flex col g-2" style="padding-top: 8px">
				<button v-for="i in INTEGRATIONS" :key="i.key" class="pjx-intg" @click="selected = i.key">
					<span class="pjx-intg-icon"><Icon :name="i.icon" :size="18" /></span>
					<span class="flex col g-1 pjx-intg-body">
						<span class="t-sm ink-8" style="font-weight: 500">{{ i.label }}</span>
						<span class="t-xs ink-5">{{ i.blurb }}</span>
					</span>
					<span class="pjx-intg-badge" :class="`is-${i.state(payload).tone}`">{{ i.state(payload).label }}</span>
					<Icon name="chevron-right" :size="16" class="ink-4 shrink-0" />
				</button>
			</div>

			<div class="pjx-intg-uphead t-xs ink-5">Upcoming</div>
			<div class="flex col g-2">
				<div v-for="i in UPCOMING" :key="i.key" class="pjx-intg is-upcoming">
					<span class="pjx-intg-icon"><Icon :name="i.icon" :size="18" /></span>
					<span class="flex col g-1 pjx-intg-body">
						<span class="t-sm ink-8" style="font-weight: 500">{{ i.label }}</span>
						<span class="t-xs ink-5">{{ i.blurb }}</span>
					</span>
					<span class="pjx-intg-badge is-soon">Upcoming</span>
				</div>
			</div>
		</SettingsBody>
	</template>
</template>

<style scoped>
.pjx-intg {
	display: flex;
	align-items: center;
	gap: 12px;
	width: 100%;
	padding: 12px;
	border: 1px solid var(--outline-gray-1);
	border-radius: 8px;
	background: none;
	cursor: pointer;
	text-align: left;
}
.pjx-intg:hover {
	background: var(--surface-gray-1);
}
.pjx-intg.is-upcoming {
	cursor: default;
	opacity: 0.72;
}
.pjx-intg.is-upcoming:hover {
	background: none;
}
.pjx-intg-uphead {
	margin: 20px 0 8px;
	font-weight: 500;
	text-transform: uppercase;
	letter-spacing: 0.04em;
}
.pjx-intg-icon {
	display: grid;
	place-items: center;
	width: 34px;
	height: 34px;
	border-radius: 8px;
	background: var(--surface-gray-2);
	color: var(--ink-gray-7);
	flex-shrink: 0;
}
.pjx-intg-body {
	flex: 1;
	min-width: 0;
}
.pjx-intg-badge {
	flex-shrink: 0;
	padding: 2px 8px;
	border-radius: 999px;
	font-size: 11px;
	font-weight: 500;
	white-space: nowrap;
}
.pjx-intg-badge.is-on {
	color: var(--ink-green-3);
	background: var(--surface-green-1);
}
.pjx-intg-badge.is-off,
.pjx-intg-badge.is-soon {
	color: var(--ink-gray-6);
	background: var(--surface-gray-2);
}
</style>
