<script setup>
import { computed } from 'vue'
import * as lucide from 'lucide-vue-next'

const props = defineProps({
	name: { type: String, required: true },
	size: { type: [Number, String], default: 16 },
	strokeWidth: { type: [Number, String], default: 1.75 },
})

function pascal(kebab) {
	return kebab
		.split('-')
		.map((s) => s.charAt(0).toUpperCase() + s.slice(1))
		.join('')
}

const comp = computed(() => lucide[pascal(props.name)] || lucide.Square)
</script>

<template>
	<component
		:is="comp"
		:size="Number(size)"
		:stroke-width="Number(strokeWidth)"
		:absolute-stroke-width="true"
	/>
</template>
