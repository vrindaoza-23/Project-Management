<script setup>
import { computed, reactive, ref } from 'vue'
import { createResource, Button, FormControl, Switch, SettingsHeader, SettingsBody, SettingsRow } from 'frappe-ui'
import Icon from '../../Icon.vue'
import SelectField from '../../SelectField.vue'
import { store } from '@/data/store'
import { notify } from '@/utils/feedback'

defineEmits(['back'])

// Blank form until the admin resource loads; secrets never round-trip, so the
// inputs stay empty and only overwrite when the admin types a new value.
const form = reactive({
	enabled: false,
	account: '',
	webhook_secret: '',
	access_token: '',
	move_on_open: true,
	move_on_merge: true,
	close_on_keyword: true,
	post_comment: true,
	repos: [],
})
const meta = reactive({
	has_webhook_secret: false, has_access_token: false, webhook_url: '',
	app_connected: false, app_slug: '', app_installed: false,
})
const forbidden = ref(false)
const showManual = ref(false)

const settings = createResource({
	url: 'projex.github.get_settings',
	auto: true,
	onSuccess: (d) => hydrate(d),
	onError: (e) => (forbidden.value = e?.exc_type === 'PermissionError' || /not permitted|system manager/i.test(e?.messages?.[0] || '')),
})

function hydrate(d) {
	Object.assign(form, {
		enabled: d.enabled, account: d.account || '', webhook_secret: '', access_token: '',
		move_on_open: d.move_on_open, move_on_merge: d.move_on_merge,
		close_on_keyword: d.close_on_keyword, post_comment: d.post_comment,
		repos: (d.repos || []).map((r) => ({ ...r })),
	})
	Object.assign(meta, {
		has_webhook_secret: d.has_webhook_secret, has_access_token: d.has_access_token, webhook_url: d.webhook_url,
		app_connected: d.app_connected, app_slug: d.app_slug || '', app_installed: d.app_installed,
	})
}

const projectOptions = computed(() => store.projects.map((p) => ({ value: p.name, label: p.project_name })))

// --- GitHub App connection flow ---
const appManifest = createResource({ url: 'projex.github_app.app_manifest' })
function connectApp() {
	appManifest.submit().then((d) => {
		// The manifest flow is a form POST navigation (not fetch): GitHub reads
		// the hidden `manifest` field, then redirects back to our callback.
		const f = document.createElement('form')
		f.method = 'POST'
		f.action = d.post_url
		const input = document.createElement('input')
		input.type = 'hidden'
		input.name = 'manifest'
		input.value = d.manifest
		f.appendChild(input)
		document.body.appendChild(f)
		f.submit()
	})
}
const installRes = createResource({ url: 'projex.github_app.install_url' })
function installApp() {
	installRes.submit().then((url) => (window.location.href = url))
}
const disconnectRes = createResource({ url: 'projex.github_app.disconnect_app' })
function disconnectApp() {
	disconnectRes.submit().then(() => {
		settings.reload()
		notify.success('GitHub App disconnected')
	})
}

// --- manual mode ---
const saver = createResource({ url: 'projex.github.save_settings' })
function save() {
	saver.submit({ payload: JSON.stringify({ ...form }) }).then((d) => {
		hydrate(d)
		notify.success('GitHub settings saved')
	})
}
const secretGen = createResource({ url: 'projex.github.generate_secret' })
function generateSecret() {
	secretGen.submit().then((v) => {
		form.webhook_secret = v
		notify.info('Secret generated — paste it into GitHub and Save.')
	})
}

function addRepo() {
	form.repos.push({ repository: '', project: '' })
}
function removeRepo(i) {
	form.repos.splice(i, 1)
}
function copy(text) {
	navigator.clipboard?.writeText(text)
	notify.success('Copied')
}
</script>

<template>
	<SettingsHeader title="GitHub">
		<template #actions>
			<button class="pjx-back" @click="$emit('back')">
				<Icon name="chevron-left" :size="15" /> Integrations
			</button>
			<Button v-if="!forbidden" variant="solid" theme="gray" :loading="saver.loading" @click="save">Save</Button>
		</template>
	</SettingsHeader>

	<SettingsBody>
		<div v-if="forbidden" class="pt-2 text-p-sm text-ink-gray-5">
			Only a System Manager can configure the GitHub integration.
		</div>

		<div v-else-if="settings.data" class="flex flex-col gap-8 pt-1">
			<!-- Connection -->
			<section class="flex flex-col gap-4">
				<div class="flex items-center justify-between gap-4">
					<div class="flex flex-col gap-0.5">
						<span class="text-p-base font-medium text-ink-gray-8">Enabled</span>
						<span class="text-p-sm text-ink-gray-5">Receive webhooks and keep issues in sync with GitHub.</span>
					</div>
					<Switch v-model="form.enabled" />
				</div>

				<!-- Connected via App -->
				<div v-if="meta.app_connected" class="pjx-appcard">
					<span class="pjx-appcard__icon"><Icon name="github" :size="18" /></span>
					<div class="flex flex-col gap-0.5 min-w-0" style="flex: 1">
						<span class="text-p-base font-medium text-ink-gray-8">Connected via GitHub App</span>
						<span class="text-p-sm" :class="meta.app_installed ? 'text-ink-gray-5' : 'text-ink-amber-3'">
							{{ meta.app_slug }} · {{ meta.app_installed ? 'installed' : 'not installed yet — finish setup' }}
						</span>
					</div>
					<Button v-if="!meta.app_installed" variant="solid" theme="gray" :loading="installRes.loading" @click="installApp">Install</Button>
					<Button v-else variant="subtle" :loading="installRes.loading" @click="installApp">Reinstall</Button>
					<Button variant="ghost" :loading="disconnectRes.loading" @click="disconnectApp">
						<template #icon><Icon name="x" :size="15" /></template>
					</Button>
				</div>

				<!-- Not connected: one-click CTA + manual fallback -->
				<template v-else>
					<div class="pjx-cta">
						<div class="flex flex-col gap-0.5 min-w-0" style="flex: 1">
							<span class="text-p-base font-medium text-ink-gray-8">Connect a GitHub App</span>
							<span class="text-p-sm text-ink-gray-5">One click creates the App and wires the webhook — no secrets to copy.</span>
						</div>
						<Button variant="solid" theme="gray" :loading="appManifest.loading" @click="connectApp">
							<template #prefix><Icon name="github" :size="15" /></template>Connect
						</Button>
					</div>

					<button class="pjx-manualtoggle" @click="showManual = !showManual">
						<Icon :name="showManual ? 'chevron-down' : 'chevron-right'" :size="14" />
						Set up manually instead
					</button>

					<div v-if="showManual" class="flex flex-col gap-5">
						<FormControl v-model="form.account" label="GitHub account / organisation" placeholder="e.g. pinecone-labs" />

						<div class="flex flex-col gap-1.5">
							<span class="text-xs text-ink-gray-5">Webhook URL <span class="text-ink-gray-4">— add this in GitHub → Settings → Webhooks</span></span>
							<div class="flex items-center gap-2">
								<code class="pjx-code">{{ meta.webhook_url }}</code>
								<Button variant="subtle" @click="copy(meta.webhook_url)">
									<template #icon><Icon name="copy" :size="14" /></template>
								</Button>
							</div>
						</div>

						<div class="flex flex-col gap-1.5">
							<span class="text-xs text-ink-gray-5">
								Webhook secret
								<span v-if="meta.has_webhook_secret" class="text-ink-gray-4">— configured, leave blank to keep</span>
							</span>
							<div class="flex items-center gap-2">
								<FormControl v-model="form.webhook_secret" type="text" class="flex-1" :placeholder="meta.has_webhook_secret ? '••••••••' : 'Set a secret'" />
								<Button variant="subtle" :loading="secretGen.loading" @click="generateSecret">Generate</Button>
							</div>
						</div>

						<FormControl
							v-model="form.access_token"
							type="password"
							label="Access token"
							:placeholder="meta.has_access_token ? '••••••••' : 'ghp_…'"
							:description="meta.has_access_token ? 'Configured. Optional — used to post comments back and read CI.' : 'Optional — used to post comments back and read CI.'"
						/>
					</div>
				</template>
			</section>

			<!-- Automation -->
			<section class="flex flex-col gap-3">
				<h3 class="text-p-base font-medium text-ink-gray-8">Automation</h3>
				<div class="divide-y divide-outline-gray-1">
					<SettingsRow title="Move to In Progress when a PR opens">
						<Switch v-model="form.move_on_open" />
					</SettingsRow>
					<SettingsRow title="Move to Done when a PR merges">
						<Switch v-model="form.move_on_merge" />
					</SettingsRow>
					<SettingsRow title="Only mark Done on a closing keyword" description="e.g. “closes / fixes PROJ-12” in the PR.">
						<Switch v-model="form.close_on_keyword" />
					</SettingsRow>
					<SettingsRow title="Comment on the issue when a PR links it">
						<Switch v-model="form.post_comment" />
					</SettingsRow>
				</div>
			</section>

			<!-- Repositories -->
			<section class="flex flex-col gap-3">
				<div class="flex items-center justify-between gap-4">
					<div class="flex flex-col gap-0.5">
						<h3 class="text-p-base font-medium text-ink-gray-8">Repositories</h3>
						<span class="text-p-sm text-ink-gray-5">Map each repository to the project its issues live in. Unmapped repos are ignored.</span>
					</div>
					<Button variant="subtle" @click="addRepo">
						<template #prefix><Icon name="plus" :size="14" /></template>Add
					</Button>
				</div>

				<div v-if="form.repos.length" class="flex flex-col gap-2">
					<div v-for="(r, i) in form.repos" :key="i" class="flex items-center gap-2">
						<FormControl v-model="r.repository" type="text" placeholder="owner/name" class="flex-1" />
						<SelectField :options="projectOptions" :model-value="r.project" placeholder="Project" class="flex-1" @change="(v) => (r.project = v)" />
						<Button variant="ghost" @click="removeRepo(i)">
							<template #icon><Icon name="trash-2" :size="15" /></template>
						</Button>
					</div>
				</div>
				<p v-else class="rounded-md border border-dashed border-outline-gray-2 py-4 text-center text-p-sm text-ink-gray-4">
					No repositories mapped yet.
				</p>
			</section>
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
	font-size: 13px;
	color: var(--ink-gray-6);
}
.pjx-code {
	flex: 1;
	min-width: 0;
	overflow-x: auto;
	white-space: nowrap;
	padding: 6px 10px;
	border-radius: 8px;
	background: var(--surface-gray-2);
	color: var(--ink-gray-7);
	font-size: 12px;
	line-height: 1.6;
}
.pjx-appcard,
.pjx-cta {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 12px 14px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 10px;
}
.pjx-appcard {
	background: var(--surface-green-1);
	border-color: var(--outline-green-1);
}
.pjx-appcard__icon {
	display: grid;
	place-items: center;
	width: 34px;
	height: 34px;
	border-radius: 8px;
	background: var(--surface-white, #fff);
	color: var(--ink-gray-8);
	flex-shrink: 0;
}
.pjx-manualtoggle {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	align-self: flex-start;
	background: none;
	border: none;
	padding: 0;
	cursor: pointer;
	font-size: 12px;
	color: var(--ink-gray-5);
}
.pjx-manualtoggle:hover {
	color: var(--ink-gray-7);
}
</style>
