<script setup>
import { computed } from 'vue'
import { Autocomplete } from 'frappe-ui'

/**
 * Thin wrapper over frappe-ui Autocomplete that speaks plain values
 * (string for single, array of strings for multiple). Use this inside
 * frappe-ui Dialogs — Autocomplete handles the dialog focus-trap correctly,
 * unlike a body-teleported custom popover.
 */
const props = defineProps({
	options: { type: Array, default: () => [] }, // [{ value, label }]
	modelValue: { type: [Array, String, Number, Object, null], default: null },
	multiple: { type: Boolean, default: false },
	placeholder: { type: String, default: 'Select…' },
})
const emit = defineEmits(['update:modelValue', 'change'])

const fOptions = computed(() => props.options.map((o) => ({ label: o.label, value: o.value })))

function onChange(val) {
	let out
	if (props.multiple) out = (val || []).map((v) => (v && v.value !== undefined ? v.value : v))
	else out = val ? (val.value !== undefined ? val.value : val) : null
	emit('update:modelValue', out)
	emit('change', out)
}
</script>

<template>
	<Autocomplete
		:multiple="multiple"
		:options="fOptions"
		:model-value="modelValue"
		:placeholder="placeholder"
		@change="onChange"
	/>
</template>
