<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({ priority: { type: String, default: 'None' } })

// bars filled + color; urgent = red, others monochrome (matches design tokens).
const META = {
	Urgent: { bars: 3, color: 'var(--ink-red-3)' },
	High: { bars: 3, color: 'var(--ink-gray-8)' },
	Medium: { bars: 2, color: 'var(--ink-gray-6)' },
	Low: { bars: 1, color: 'var(--ink-gray-4)' },
	None: { bars: 0, color: 'var(--ink-gray-4)' },
}
const m = computed(() => META[props.priority] || META.None)
</script>

<template>
	<span class="pjx-prio" :style="{ color: m.color }" :title="priority">
		<Icon v-if="m.bars === 0" name="minus" :size="12" />
		<template v-else>
			<span
				v-for="i in 3"
				:key="i"
				class="pjx-prio__bar"
				:style="{ height: 5 + (i - 1) * 3 + 'px', opacity: i <= m.bars ? 1 : 0.22 }"
			/>
		</template>
	</span>
</template>
