<script setup>
import { computed } from 'vue'
import { ICONS, FALLBACK_ICON } from './icons'

const props = defineProps({
	name: { type: String, required: true },
	size: { type: [Number, String], default: 16 },
	strokeWidth: { type: [Number, String], default: 1.75 },
})

const comp = computed(() => ICONS[props.name] || FALLBACK_ICON)
</script>

<template>
	<component
		:is="comp"
		:size="Number(size)"
		:stroke-width="Number(strokeWidth)"
		:absolute-stroke-width="true"
	/>
</template>
