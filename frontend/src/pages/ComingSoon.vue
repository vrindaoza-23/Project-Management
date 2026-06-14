<script setup>
import Icon from '@/components/Icon.vue'
defineProps({ icon: { type: String, default: 'sparkles' }, label: { type: String, default: '' } })
</script>

<template>
	<div class="pjx-soon">
		<span class="pjx-soon__icon"><Icon :name="icon" :size="20" /></span>
		<div class="t-base ink-7" style="font-weight: 500">{{ label }}</div>
		<div class="t-sm ink-4">Wired in an upcoming vertical slice.</div>
	</div>
</template>
