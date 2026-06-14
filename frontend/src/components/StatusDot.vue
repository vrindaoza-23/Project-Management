<script setup>
import { computed } from 'vue'

const props = defineProps({
	status: { type: Object, default: null }, // { color_theme, dot_hollow, category }
	size: { type: Number, default: 9 },
})

const DOT = {
	gray: 'var(--gray-500)',
	blue: 'var(--blue-500)',
	amber: 'var(--amber-500)',
	green: 'var(--green-600)',
	red: 'var(--red-500)',
	purple: 'var(--purple-500)',
}

const hollow = computed(() => props.status?.dot_hollow)
const color = computed(() => DOT[props.status?.color_theme] || 'var(--gray-500)')
</script>

<template>
	<span
		class="pjx-dot"
		:class="{ 'pjx-dot--hollow': hollow }"
		:style="{ width: size + 'px', height: size + 'px', background: hollow ? 'transparent' : color }"
		:title="status?.status_name"
	/>
</template>
