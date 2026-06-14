<script setup>
defineProps({
	label: { type: Object, required: true }, // { label_name, color }
})
</script>

<template>
	<span class="pjx-label">
		<span class="pjx-label__dot" :style="{ background: label.color }" />
		{{ label.label_name }}
	</span>
</template>
