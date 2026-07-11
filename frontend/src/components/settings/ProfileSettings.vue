<script setup>
import { computed, reactive } from 'vue'
import {
	Avatar,
	Button,
	FormControl,
	SettingsBody,
	SettingsHeader,
	createResource,
} from 'frappe-ui'
import { store, reloadBootstrap, userById } from '@/data/store'
import { notify, notifyError } from '@/utils/feedback'

const me = computed(() => userById(store.user))
const form = reactive({ first_name: '', last_name: '', bio: '' })

// Loaded on tab open (this panel mounts lazily inside the settings dialog).
const profile = createResource({
	url: 'frappe.client.get_value',
	params: {
		doctype: 'User',
		filters: store.user,
		fieldname: ['first_name', 'last_name', 'bio'],
	},
	auto: true,
	onSuccess(d) {
		form.first_name = d.first_name || ''
		form.last_name = d.last_name || ''
		form.bio = d.bio || ''
	},
})

const saver = createResource({ url: 'frappe.client.set_value' })
async function save() {
	try {
		await saver.submit({
			doctype: 'User',
			name: store.user,
			fieldname: { ...form },
		})
		reloadBootstrap()
		notify.success('Profile updated')
	} catch (e) {
		notifyError(e, 'Could not update profile')
	}
}
</script>

<template>
	<SettingsHeader title="Profile" />
	<SettingsBody>
		<div class="flex flex-col gap-6">
			<div class="flex items-center gap-4">
				<Avatar size="2xl" :image="me?.user_image" :label="me?.full_name || store.user" />
				<div>
					<div class="text-base font-medium text-ink-gray-8">Profile picture</div>
					<div class="text-sm text-ink-gray-6">Helps people recognise you</div>
				</div>
			</div>
			<div class="grid grid-cols-2 gap-4">
				<FormControl v-model="form.first_name" label="First name" :disabled="profile.loading" />
				<FormControl v-model="form.last_name" label="Last name" :disabled="profile.loading" />
			</div>
			<FormControl v-model="form.bio" type="textarea" label="Bio" :disabled="profile.loading" />
			<div>
				<Button variant="solid" :loading="saver.loading" @click="save">Save changes</Button>
			</div>
		</div>
	</SettingsBody>
</template>
