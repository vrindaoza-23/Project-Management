<script setup>
import { computed } from 'vue'
import { Avatar } from 'frappe-ui'
import { userById, userName } from '@/data/store'

const props = defineProps({
	users: { type: Array, default: () => [] }, // user ids (emails)
	size: { type: Number, default: 22 },
	max: { type: Number, default: 3 },
})

const shown = computed(() => props.users.slice(0, props.max))
const rest = computed(() => Math.max(0, props.users.length - props.max))
function image(id) {
	return userById(id)?.user_image
}
</script>

<template>
	<span class="pjx-avstack">
		<Avatar
			v-for="id in shown"
			:key="id"
			:label="userName(id)"
			:image="image(id)"
			:size="size <= 18 ? 'sm' : 'md'"
		/>
		<span
			v-if="rest > 0"
			class="pjx-avmore"
			:style="{ width: size + 'px', height: size + 'px', fontSize: size * 0.4 + 'px' }"
			>+{{ rest }}</span
		>
	</span>
</template>
