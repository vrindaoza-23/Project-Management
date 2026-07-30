<script setup>
import { ref, reactive, computed, watch, h } from 'vue'
import { createResource, call, Dialog, Button, Badge, Dropdown, FormControl } from 'frappe-ui'
import Icon from '@/components/Icon.vue'
import StatusIcon from '@/components/StatusIcon.vue'
import SelectField from '@/components/SelectField.vue'
import { notify, notifyError, confirm, promptText } from '@/utils/feedback'
import { formatMoney, dueLabel, dueTone } from '@/utils/format'

const props = defineProps({ projectKey: { type: String, required: true } })

const plan = createResource({
	url: 'projex.delivery.get_delivery_plan',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
const clients = createResource({
	url: 'projex.portal.list_client_access',
	makeParams: () => ({ project: props.projectKey }),
	auto: true,
})
const templates = createResource({ url: 'projex.project_templates.list_templates', auto: true })

watch(() => props.projectKey, () => { plan.reload(); clients.reload() })

const canManage = computed(() => !!plan.data?.can_manage)
const canInvoice = computed(() => !!plan.data?.can_invoice)
const currency = computed(() => plan.data?.currency || 'USD')
const contractValue = computed(() => plan.data?.contract_value || 0)
const phases = computed(() => plan.data?.phases || [])
const isEmpty = computed(() => !plan.loading && phases.value.length === 0)

const money = (n) => formatMoney(n || 0, currency.value)
const busy = ref(false)

// ---- money per milestone ----
// This is a billing tool, so the money is the point: show the real figure, not
// a buried "% of contract". Prefer an explicit amount; else derive it from the
// milestone's share of the contract value. T&M / non-billable carry no figure.
const isSignedOff = (m) => m.client_signoff_status === 'Approved'
function milestoneAmount(m) {
	if (m.billing_type === 'Time & Materials' || m.billing_type === 'Non-billable') return 0
	if (m.billing_amount) return m.billing_amount
	if (m.billing_percent) return (m.billing_percent / 100) * contractValue.value
	return 0
}
function billingKind(m) {
	if (m.billing_type === 'Time & Materials') return 'Time & materials'
	if (m.billing_type === 'Non-billable') return 'Non-billable'
	return ''
}
const phaseValue = (p) => (p.milestones || []).reduce((s, m) => s + milestoneAmount(m), 0)

// ---- progress summary ----
const allMilestones = computed(() => phases.value.flatMap((p) => p.milestones || []))
const approvedCount = computed(() => allMilestones.value.filter(isSignedOff).length)
const awaitingCount = computed(
	() => allMilestones.value.filter((m) => m.client_signoff_status === 'Pending').length,
)
const progressPct = computed(() =>
	allMilestones.value.length ? Math.round((approvedCount.value / allMilestones.value.length) * 100) : 0,
)
const signedValue = computed(() =>
	allMilestones.value.filter(isSignedOff).reduce((s, m) => s + milestoneAmount(m), 0),
)
const plannedValue = computed(() => contractValue.value || allMilestones.value.reduce((s, m) => s + milestoneAmount(m), 0))

// ---- status → single frappe-ui Badge ----
// A milestone reads as ONE effective state: the client sign-off outcome takes
// precedence (it's the state that matters commercially); otherwise its own
// working status. Two badges saying "Signed off / Approved" is noise.
function milestoneBadge(m) {
	const so = m.client_signoff_status
	if (so === 'Approved') return { theme: 'green', label: 'Signed off' }
	if (so === 'Pending') return { theme: 'blue', label: 'Awaiting client' }
	if (so === 'Changes Requested') return { theme: 'red', label: 'Changes requested' }
	return ({
		Approved: { theme: 'green', label: 'Approved' },
		Delivered: { theme: 'orange', label: 'Delivered' },
		'In Progress': { theme: 'blue', label: 'In progress' },
		Planned: { theme: 'gray', label: 'Planned' },
		Rejected: { theme: 'red', label: 'Changes requested' },
	}[m.status]) || { theme: 'gray', label: m.status }
}
function deliverableBadge(d) {
	return ({
		Draft: { theme: 'gray', label: 'Draft' },
		Submitted: { theme: 'orange', label: 'In review' },
		Approved: { theme: 'green', label: 'Approved' },
		'Changes Requested': { theme: 'red', label: 'Changes requested' },
	}[d.status]) || { theme: 'gray', label: d.status }
}
function billingLabel(m) {
	if (m.billing_type === 'Non-billable') return 'Non-billable'
	if (m.billing_type === 'Time & Materials') return 'Time & materials'
	if (m.billing_amount) return money(m.billing_amount)
	if (m.billing_percent) return `${m.billing_percent}% of contract`
	return m.billing_type
}

// ---- leading status glyph ----
// Same Linear-style glyph the task list puts at the head of every row, so the two
// surfaces scan identically. We derive the shape/color from the badge's theme
// (which already encodes the effective state) rather than duplicating the mapping.
function statusGlyph(theme, label) {
	const category = { green: 'completed', blue: 'started', orange: 'started', red: 'started', gray: 'unstarted' }[theme] || 'unstarted'
	return { category, color_theme: theme === 'orange' ? 'amber' : theme, status_name: label }
}
const milestoneGlyph = (m) => { const b = milestoneBadge(m); return statusGlyph(b.theme, b.label) }
const deliverableGlyph = (d) => { const b = deliverableBadge(d); return statusGlyph(b.theme, b.label) }

// ---- collapse (per phase) — mirrors the task list's collapsible groups ----
const collapsed = reactive({})
const toggleGroup = (key) => { collapsed[key] = !collapsed[key] }

async function run(fn, okMsg) {
	busy.value = true
	try {
		await fn()
		if (okMsg) notify.success(okMsg)
		plan.reload()
	} catch (e) {
		notifyError(e)
	} finally {
		busy.value = false
	}
}

// ---- phases ----
async function addPhase() {
	const name = await promptText({ title: 'Add phase', label: 'Phase name', placeholder: 'e.g. Discovery' })
	if (!name) return
	run(() => call('projex.delivery.create_phase', { project: props.projectKey, phase_name: name, position: phases.value.length }), 'Phase added')
}
async function delPhase(p) {
	if (!(await confirm({ title: 'Delete phase?', message: `“${p.phase_name}” — its milestones are kept (unphased).`, theme: 'red', confirmLabel: 'Delete' }))) return
	run(() => call('projex.delivery.delete_phase', { name: p.name }), 'Phase deleted')
}

// ---- deliverables ----
async function addDeliverable(m) {
	const name = await promptText({ title: 'Add deliverable', label: 'Deliverable', placeholder: 'e.g. Signed BRD' })
	if (!name) return
	run(() => call('projex.delivery.create_deliverable', { milestone: m.name, deliverable_name: name }), 'Deliverable added')
}
function toggleDeliverable(d) {
	// Draft → Submitted (send to client for review); Submitted → Draft (pull back).
	const next = d.status === 'Draft' ? 'Submitted' : 'Draft'
	run(() => call('projex.delivery.update_deliverable', { name: d.name, status: next }))
}
async function delDeliverable(d) {
	if (!(await confirm({ title: 'Delete deliverable?', message: d.deliverable_name, theme: 'red', confirmLabel: 'Delete' }))) return
	run(() => call('projex.delivery.delete_deliverable', { name: d.name }))
}

// ---- sign-off (partner side) ----
function requestSignoff(m) {
	run(() => call('projex.delivery.request_signoff', { milestone: m.name }), 'Sign-off requested from client')
}
async function recordSignoff(m, outcome) {
	const note = await promptText({ title: `Record: ${outcome}`, label: 'Note (optional)', confirmLabel: 'Record' })
	if (note === null) return
	run(() => call('projex.delivery.record_signoff', { milestone: m.name, outcome, note }), 'Sign-off recorded')
}

// ---- billing ----
async function invoiceMilestone(m) {
	if (!(await confirm({ title: 'Generate invoice?', message: `Create a draft ERPNext Sales Invoice for “${m.milestone_name}” (${billingLabel(m)}).`, confirmLabel: 'Generate' }))) return
	run(async () => {
		const r = await call('projex.billing.generate_milestone_invoice', { milestone: m.name })
		notify.success(`Draft invoice ${r.sales_invoice} created`)
	})
}
async function billTime() {
	if (!(await confirm({ title: 'Bill unbilled time?', message: 'Create a draft T&M Sales Invoice from all unbilled billable time on this project, at rate-card rates.', confirmLabel: 'Generate' }))) return
	run(async () => {
		const r = await call('projex.billing.generate_tm_invoice', { project: props.projectKey })
		notify.success(`Draft invoice ${r.sales_invoice} — ${r.hours}h across ${r.lines} role(s)`)
	})
}

// ---- action menus (frappe-ui Dropdown) ----
const menuIcon = (name) => ({ render: () => h(Icon, { name, size: 15 }) })
const canBillMilestone = (m) => canInvoice.value && (m.billing_type === 'Fixed' || m.billing_type === 'Retainer')

function phaseMenu(p) {
	return [
		{ label: 'Add milestone', icon: menuIcon('plus'), onClick: () => openMilestone(p.name) },
		{ label: 'Delete phase', icon: menuIcon('trash-2'), theme: 'red', onClick: () => delPhase(p) },
	]
}
function milestoneMenu(m) {
	const items = [{ label: 'Add deliverable', icon: menuIcon('plus'), onClick: () => addDeliverable(m) }]
	if (m.client_signoff_status !== 'Approved' && m.client_signoff_status !== 'Pending')
		items.push({ label: 'Request sign-off', icon: menuIcon('megaphone'), onClick: () => requestSignoff(m) })
	if (m.client_signoff_status !== 'Approved')
		items.push({ label: 'Mark approved', icon: menuIcon('check'), onClick: () => recordSignoff(m, 'Approved') })
	if (!m.invoiced && canBillMilestone(m))
		items.push({ label: 'Generate invoice', icon: menuIcon('wallet'), onClick: () => invoiceMilestone(m) })
	items.push({ label: 'Delete milestone', icon: menuIcon('trash-2'), theme: 'red', onClick: () => delMilestone(m) })
	return items
}
function deliverableMenu(d) {
	const items = []
	if (d.status === 'Draft') items.push({ label: 'Send to client', icon: menuIcon('arrow-right'), onClick: () => toggleDeliverable(d) })
	else if (d.status === 'Submitted') items.push({ label: 'Pull back', icon: menuIcon('undo-2'), onClick: () => toggleDeliverable(d) })
	items.push({ label: 'Delete', icon: menuIcon('trash-2'), theme: 'red', onClick: () => delDeliverable(d) })
	return items
}

// ---- templates ----
const showTemplate = ref(false)
const tpl = reactive({ template: '', start_date: new Date().toISOString().slice(0, 10) })
const templateOptions = computed(() => (templates.data || []).map((t) => ({ value: t.name, label: t.template_name })))
function openTemplate() {
	tpl.template = templateOptions.value[0]?.value || ''
	tpl.start_date = new Date().toISOString().slice(0, 10)
	showTemplate.value = true
}
async function applyTemplate() {
	if (!tpl.template) return
	showTemplate.value = false
	run(async () => {
		const r = await call('projex.project_templates.instantiate_template', {
			template: tpl.template, project: props.projectKey, start_date: tpl.start_date,
		})
		const c = r.created
		notify.success(`Added ${c.phases} phases, ${c.tasks} tasks, ${c.milestones} milestones`)
	})
}

// ---- add milestone dialog ----
const showMs = ref(false)
const ms = reactive({ milestone_name: '', phase: '', billing_type: 'Fixed', billing_amount: null, billing_percent: null, target_date: '' })
const BILLING_TYPES = ['Fixed', 'Time & Materials', 'Retainer', 'Non-billable'].map((v) => ({ value: v, label: v }))
const phaseOptions = computed(() => [
	{ value: '', label: 'No phase' },
	...phases.value.filter((p) => !p.synthetic).map((p) => ({ value: p.name, label: p.phase_name })),
])
function openMilestone(phaseName = '') {
	Object.assign(ms, { milestone_name: '', phase: phaseName, billing_type: 'Fixed', billing_amount: null, billing_percent: null, target_date: '' })
	showMs.value = true
}
async function saveMilestone() {
	if (!ms.milestone_name.trim()) return notify.warning('Name the milestone')
	showMs.value = false
	run(() => call('projex.delivery.create_milestone', {
		project: props.projectKey, milestone_name: ms.milestone_name.trim(), phase: ms.phase || null,
		billing_type: ms.billing_type, billing_amount: ms.billing_amount || 0,
		billing_percent: ms.billing_percent || 0, target_date: ms.target_date || null,
	}), 'Milestone added')
}
async function delMilestone(m) {
	if (!(await confirm({ title: 'Delete milestone?', message: `“${m.milestone_name}” and its deliverables.`, theme: 'red', confirmLabel: 'Delete' }))) return
	run(() => call('projex.delivery.delete_milestone', { name: m.name }))
}

// ---- clients ----
const showClients = ref(false)
async function grantClient() {
	const email = await promptText({ title: 'Grant portal access', label: 'Client user email', placeholder: 'contact@customer.com', confirmLabel: 'Grant' })
	if (!email) return
	busy.value = true
	try {
		await call('projex.portal.grant_client_access', { project: props.projectKey, email })
		notify.success('Access granted')
		clients.reload()
	} catch (e) { notifyError(e) } finally { busy.value = false }
}
async function revokeClient(row) {
	if (!(await confirm({ title: 'Revoke access?', message: row.user, theme: 'red', confirmLabel: 'Revoke' }))) return
	await call('projex.portal.revoke_client_access', { project: props.projectKey, email: row.user })
	clients.reload()
}
</script>

<template>
	<div class="pjx-del">
		<!-- toolbar: compact progress summary on the left, surface actions on the
		     right — same bar the Tasks surface puts under the tab header. -->
		<div class="pjx-del__bar">
			<div v-if="!isEmpty" class="pjx-del__summary">
				<span class="pjx-del__pct">{{ progressPct }}<span class="pjx-del__pctu">%</span></span>
				<div class="pjx-del__track"><i :style="{ width: progressPct + '%' }" /></div>
				<span class="pjx-del__cap">
					<template v-if="plannedValue"><span class="pjx-del__val">{{ money(signedValue) }}</span> of {{ money(plannedValue) }} signed off</template>
					<template v-else>{{ approvedCount }} of {{ allMilestones.length }} milestones signed off</template>
					<template v-if="awaitingCount"> · {{ awaitingCount }} awaiting client</template>
				</span>
			</div>
			<span class="pjx-spacer" />
			<div v-if="canManage" class="pjx-del__act">
				<Button variant="ghost" theme="gray" @click="showClients = !showClients">
					<template #prefix><Icon name="users" :size="15" /></template>Clients
				</Button>
				<Button v-if="canInvoice" variant="ghost" theme="gray" :loading="busy" @click="billTime">
					<template #prefix><Icon name="wallet" :size="15" /></template>Bill time
				</Button>
				<Button variant="solid" theme="gray" @click="openMilestone()">
					<template #prefix><Icon name="plus" :size="15" /></template>Milestone
				</Button>
			</div>
		</div>

		<!-- clients panel -->
		<div v-if="canManage && showClients" class="pjx-cli">
			<div class="pjx-cli__h">
				<span>Client portal access</span>
				<Button variant="ghost" size="sm" @click="grantClient">
					<template #prefix><Icon name="plus" :size="13" /></template>Grant access
				</Button>
			</div>
			<div v-for="c in clients.data || []" :key="c.name" class="pjx-cli__row">
				<Icon name="user" :size="15" class="ink-4" />
				<span class="pjx-cli__name">{{ c.user }}</span>
				<span v-if="c.customer" class="pjx-dim">{{ c.customer }}</span>
				<span class="pjx-spacer" />
				<button class="pjx-more" title="Revoke" @click="revokeClient(c)"><Icon name="x" :size="15" /></button>
			</div>
			<div v-if="!(clients.data || []).length" class="pjx-dim pjx-cli__hint">
				Grant a customer contact access so they can track status and sign off deliverables at <code>/projex-portal</code>.
			</div>
		</div>

		<!-- empty state -->
		<div v-if="isEmpty" class="pjx-del__empty">
			<Icon name="target" :size="26" class="ink-4" />
			<h3>No delivery plan yet</h3>
			<p>Lay the implementation out as phases, billing milestones and deliverables — or start from a template.</p>
			<div v-if="canManage" class="pjx-del__emptyact">
				<Button variant="solid" theme="gray" @click="openTemplate">
					<template #prefix><Icon name="layers" :size="14" /></template>Start from template
				</Button>
				<Button variant="ghost" @click="addPhase">Add phase</Button>
			</div>
		</div>

		<!-- phases as collapsible groups; each milestone/deliverable is a task-style row -->
		<div v-if="!isEmpty" class="pjx-del__groups">
			<div v-for="p in phases" :key="p.name" class="pjx-pgroup">
				<div class="pjx-phead">
					<button class="pjx-ghead" :aria-expanded="!collapsed[p.name]" @click="toggleGroup(p.name)">
						<Icon name="chevron-down" :size="16" class="pjx-ghead__chev" :class="{ 'is-collapsed': collapsed[p.name] }" />
						<span class="pjx-grouphead__name">{{ p.phase_name }}</span>
						<span class="pjx-grouphead__count">{{ (p.milestones || []).length }}</span>
					</button>
					<span v-if="(p.milestones || []).length > 1 && phaseValue(p)" class="pjx-phase__val">{{ money(phaseValue(p)) }}</span>
					<Dropdown v-if="canManage && !p.synthetic" :options="phaseMenu(p)" placement="left">
						<button class="pjx-more" title="Phase actions"><Icon name="ellipsis" :size="16" /></button>
					</Dropdown>
				</div>

				<div v-if="!collapsed[p.name]" class="pjx-pgrouprows">
					<template v-for="m in p.milestones" :key="m.name">
						<!-- milestone row -->
						<div class="pjx-mrow">
							<StatusIcon :status="milestoneGlyph(m)" :size="16" />
							<div class="pjx-mrow__name">
								<span class="pjx-title2">{{ m.milestone_name }}</span>
								<span v-if="billingKind(m)" class="pjx-kind">{{ billingKind(m) }}</span>
								<a
									v-if="m.invoiced"
									class="pjx-inv"
									:href="`/app/sales-invoice/${encodeURIComponent(m.sales_invoice)}`"
									target="_blank"
									rel="noopener"
									@click.stop
								><Icon name="external-link" :size="12" />{{ m.sales_invoice }}</a>
							</div>
							<span class="pjx-amt">
								<template v-if="milestoneAmount(m)">{{ money(milestoneAmount(m)) }}<span v-if="m.billing_percent" class="pjx-ms__pct"> · {{ m.billing_percent }}%</span></template>
							</span>
							<span class="pjx-due2">
								<span v-if="!isSignedOff(m) && m.target_date" class="pjx-due" :class="`is-${dueTone(m.target_date)}`">Due {{ dueLabel(m.target_date) }}</span>
							</span>
							<span class="pjx-badgecell"><Badge :theme="milestoneBadge(m).theme" variant="subtle" size="sm">{{ milestoneBadge(m).label }}</Badge></span>
							<Dropdown v-if="canManage" :options="milestoneMenu(m)" placement="left">
								<button class="pjx-more" title="Milestone actions"><Icon name="ellipsis" :size="16" /></button>
							</Dropdown>
							<span v-else class="pjx-menuslot" />
						</div>

						<!-- deliverables — indented rows under the milestone -->
						<div v-if="(m.deliverables || []).length || canManage" class="pjx-dels2">
							<div v-for="d in m.deliverables" :key="d.name" class="pjx-drow2">
								<StatusIcon :status="deliverableGlyph(d)" :size="14" class="pjx-drow2__ico" />
								<span class="pjx-drow2__name">{{ d.deliverable_name }}</span>
								<span v-if="d.review_note" class="pjx-drow2__note">{{ d.review_note }}</span>
								<span class="pjx-spacer" />
								<span class="pjx-badgecell"><Badge :theme="deliverableBadge(d).theme" variant="subtle" size="sm">{{ deliverableBadge(d).label }}</Badge></span>
								<Dropdown v-if="canManage" :options="deliverableMenu(d)" placement="left">
									<button class="pjx-more" title="Deliverable actions"><Icon name="ellipsis" :size="15" /></button>
								</Dropdown>
								<span v-else class="pjx-menuslot" />
							</div>
							<button v-if="canManage" class="pjx-addrow" @click="addDeliverable(m)">
								<Icon name="plus" :size="14" />Deliverable
							</button>
						</div>
					</template>
					<div v-if="!(p.milestones || []).length" class="pjx-dim pjx-phase__none">No milestones yet.</div>
				</div>
			</div>
		</div>

		<!-- add-milestone dialog -->
		<Dialog :model-value="showMs" @update:model-value="(v) => (showMs = v)">
			<template #body-title><h3 class="t-lg" style="font-weight: 600">New milestone</h3></template>
			<template #body-content>
				<div class="flex col g-3" style="padding-top: 4px">
					<FormControl v-model="ms.milestone_name" type="text" label="Milestone name" placeholder="e.g. UAT sign-off" autofocus />
					<div class="flex g-3 wrap">
						<div class="flex col g-1" style="min-width: 190px; flex: 1">
							<span class="t-xs ink-5">Phase</span>
							<SelectField :options="phaseOptions" :model-value="ms.phase" @change="(v) => (ms.phase = v || '')" />
						</div>
						<div class="flex col g-1" style="min-width: 190px; flex: 1">
							<span class="t-xs ink-5">Billing type</span>
							<SelectField :options="BILLING_TYPES" :model-value="ms.billing_type" @change="(v) => (ms.billing_type = v)" />
						</div>
					</div>
					<div class="flex g-3 wrap" v-if="ms.billing_type === 'Fixed' || ms.billing_type === 'Retainer'">
						<div style="flex: 1; min-width: 150px">
							<FormControl v-model.number="ms.billing_amount" type="number" label="Amount" placeholder="0" />
						</div>
						<div v-if="ms.billing_type === 'Fixed'" style="flex: 1; min-width: 150px">
							<FormControl v-model.number="ms.billing_percent" type="number" label="or % of contract" placeholder="0" />
						</div>
					</div>
					<FormControl v-model="ms.target_date" type="date" label="Target date" />
				</div>
			</template>
			<template #actions>
				<div class="flex" style="gap: 8px; justify-content: flex-end; width: 100%">
					<Button variant="subtle" theme="gray" @click="showMs = false">Cancel</Button>
					<Button variant="solid" theme="gray" :loading="busy" @click="saveMilestone">Add milestone</Button>
				</div>
			</template>
		</Dialog>

		<!-- apply-template dialog -->
		<Dialog :model-value="showTemplate" @update:model-value="(v) => (showTemplate = v)">
			<template #body-title><h3 class="t-lg" style="font-weight: 600">Start from a template</h3></template>
			<template #body-content>
				<div class="flex col g-3" style="padding-top: 4px">
					<div class="flex col g-1">
						<span class="t-xs ink-5">Template</span>
						<SelectField :options="templateOptions" :model-value="tpl.template" @change="(v) => (tpl.template = v)" />
					</div>
					<FormControl v-model="tpl.start_date" type="date" label="Start date" />
					<div class="pjx-dim t-xs">Phases, tasks and milestones are created and dated relative to this start date.</div>
				</div>
			</template>
			<template #actions>
				<div class="flex" style="gap: 8px; justify-content: flex-end; width: 100%">
					<Button variant="subtle" theme="gray" @click="showTemplate = false">Cancel</Button>
					<Button variant="solid" theme="gray" :loading="busy" @click="applyTemplate">Apply template</Button>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<style scoped>
.pjx-del { padding-bottom: 64px; }
.pjx-spacer { flex: 1; }
.pjx-dim { color: var(--ink-gray-5); }

/* toolbar — the same bar the Tasks surface uses under the tab header (20px gutter) */
.pjx-del__bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; padding: 12px 20px 8px; }
.pjx-del__summary { display: flex; align-items: center; gap: 10px; min-width: 0; }
.pjx-del__pct { font-size: 15px; font-weight: 600; color: var(--ink-gray-9); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
.pjx-del__pctu { font-size: 12px; font-weight: 500; color: var(--ink-gray-5); margin-left: 1px; }
.pjx-del__track { width: 96px; height: 6px; border-radius: 999px; background: var(--surface-gray-3); overflow: hidden; flex: none; }
.pjx-del__track > i { display: block; height: 100%; background: var(--ink-gray-9); border-radius: 999px; transition: width 0.3s ease; }
.pjx-del__cap { font-size: 13px; color: var(--ink-gray-5); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pjx-del__val { color: var(--ink-gray-8); font-weight: 550; font-variant-numeric: tabular-nums; }
.pjx-del__act { display: flex; gap: 6px; flex-shrink: 0; }

/* phase groups — chevron + name + count, exactly like the task list's groups */
.pjx-del__groups { padding-top: 4px; }
.pjx-phead { display: flex; align-items: center; gap: 8px; padding: 0 20px; }
.pjx-ghead { flex: 1; display: flex; align-items: center; gap: 9px; padding: 12px 0 8px; background: none; border: none; cursor: pointer; font-size: 13px; text-align: left; }
.pjx-ghead__chev { color: var(--ink-gray-4); transition: transform 0.15s ease; flex: none; }
.pjx-ghead__chev.is-collapsed { transform: rotate(-90deg); }
.pjx-grouphead__name { font-weight: 600; color: var(--ink-gray-8); letter-spacing: -0.006em; }
.pjx-grouphead__count { color: var(--ink-gray-5); font-variant-numeric: tabular-nums; }
.pjx-phase__val { font-size: 12px; font-weight: 550; color: var(--ink-gray-6); font-variant-numeric: tabular-nums; }
.pjx-pgrouprows { padding-bottom: 18px; }
.pjx-phase__none { font-size: 13px; color: var(--ink-gray-5); padding: 4px 20px 8px 46px; }

/* milestone row — a task-style grid row: glyph | name | amount | due | badge | menu */
.pjx-mrow { display: grid; grid-template-columns: 18px minmax(0, 1fr) 118px 96px 132px 24px; gap: 10px; align-items: center; padding: 0 20px; min-height: 46px; border-radius: 8px; }
.pjx-mrow:hover { background: var(--surface-gray-1); }
.pjx-mrow__name { display: flex; align-items: center; gap: 8px; min-width: 0; }
.pjx-title2 { font-size: 13.5px; font-weight: 550; color: var(--ink-gray-9); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pjx-kind { font-size: 12px; color: var(--ink-gray-5); flex: none; }
.pjx-amt { font-size: 13px; font-weight: 550; color: var(--ink-gray-8); font-variant-numeric: tabular-nums; text-align: right; }
.pjx-ms__pct { font-weight: 450; color: var(--ink-gray-5); }
.pjx-due2 { font-size: 12.5px; text-align: right; }
.pjx-due { color: var(--ink-gray-6); white-space: nowrap; }
.pjx-due.is-overdue { color: var(--ink-red-3); font-weight: 500; }
.pjx-due.is-today { color: var(--ink-amber-3); font-weight: 500; }
.pjx-badgecell { display: flex; justify-content: flex-end; min-width: 0; }
.pjx-inv { display: inline-flex; align-items: center; gap: 4px; color: var(--ink-green-3); text-decoration: none; flex: none; }
.pjx-inv:hover { text-decoration: underline; }

/* deliverables — indented rows under their milestone, badges share the milestone's right lane */
.pjx-dels2 { position: relative; }
.pjx-dels2::before { content: ''; position: absolute; left: 30px; top: 1px; bottom: 5px; width: 2px; border-radius: 2px; background: var(--outline-gray-1); }
.pjx-drow2 { display: flex; align-items: center; gap: 10px; min-height: 34px; padding: 0 20px 0 46px; font-size: 13px; border-radius: 8px; }
.pjx-drow2:hover { background: var(--surface-gray-1); }
.pjx-drow2__ico { flex: none; opacity: 0.9; }
.pjx-drow2__name { color: var(--ink-gray-8); white-space: nowrap; }
.pjx-drow2__note { color: var(--ink-gray-4); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 320px; }
.pjx-addrow { display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; color: var(--ink-gray-5); background: none; border: none; cursor: pointer; padding: 6px 20px 6px 46px; border-radius: 6px; }
.pjx-addrow:hover { color: var(--ink-gray-8); }

/* the one, consistent icon-button used for every row menu — reveal on hover */
.pjx-more { background: none; border: none; cursor: pointer; color: var(--ink-gray-4); width: 24px; height: 24px; border-radius: 6px; display: inline-grid; place-items: center; opacity: 0; transition: opacity 0.12s, background 0.12s, color 0.12s; }
.pjx-menuslot { width: 24px; flex: none; }
.pjx-phead:hover .pjx-more,
.pjx-mrow:hover .pjx-more,
.pjx-drow2:hover .pjx-more,
.pjx-cli__row:hover .pjx-more,
.pjx-more:focus-visible { opacity: 1; }
.pjx-more:hover { background: var(--surface-gray-3); color: var(--ink-gray-7); }

/* clients panel */
.pjx-cli { border: 1px solid var(--outline-gray-1); border-radius: 10px; background: var(--surface-white); padding: 6px 14px 12px; margin: 0 20px 8px; }
.pjx-cli__h { display: flex; align-items: center; justify-content: space-between; font-size: 13px; font-weight: 600; color: var(--ink-gray-7); padding: 8px 0; }
.pjx-cli__row { display: flex; align-items: center; gap: 8px; font-size: 13px; padding: 7px 0; border-top: 1px solid var(--outline-gray-1); }
.pjx-cli__name { color: var(--ink-gray-8); }
.pjx-cli__hint { font-size: 12.5px; padding: 8px 0 2px; line-height: 1.5; }
.pjx-cli__hint code { font-size: 12px; background: var(--surface-gray-2); padding: 1px 5px; border-radius: 4px; }

/* empty state */
.pjx-del__empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; min-height: 340px; text-align: center; }
.pjx-del__empty h3 { font-size: 15px; font-weight: 600; color: var(--ink-gray-8); }
.pjx-del__empty p { font-size: 13px; color: var(--ink-gray-5); max-width: 400px; line-height: 1.5; }
.pjx-del__emptyact { display: flex; gap: 8px; margin-top: 8px; }
</style>
