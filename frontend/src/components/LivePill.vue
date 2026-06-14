<script setup>
import AvatarStack from './AvatarStack.vue'
defineProps({ users: { type: Array, default: () => [] } })
</script>

<template>
	<span v-if="users.length" class="pjx-livewrap" title="Viewing now">
		<span class="pjx-livedot" />
		<AvatarStack :users="users" :size="14" :max="2" />
	</span>
</template>
