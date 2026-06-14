<script setup>
import Icon from './Icon.vue'
defineProps({ chips: { type: Array, default: () => [] } }) // [{ k, op, v }]
</script>

<template>
	<div class="pjx-chips">
		<span v-for="(c, i) in chips" :key="i" class="pjx-chip">
			<span class="pjx-chip__k">{{ c.k }}{{ c.op ? ' ' + c.op : '' }}</span>
			<span class="pjx-chip__v">{{ c.v }}</span>
		</span>
		<button class="pjx-chip pjx-chip--add"><Icon name="plus" :size="13" /> Filter</button>
	</div>
</template>
