<script setup>
/**
 * Native <select>-based picker for use INSIDE frappe-ui Dialogs.
 *
 * frappe-ui's Select/Autocomplete render their menus in a portal, which the
 * Dialog focus-trap makes non-interactive. A native <select> renders inline and
 * is immune to that, so dialog dropdowns actually work. Supports single value
 * (string) and multiple (array of strings, shown as removable chips).
 */
import { computed, ref, watch, nextTick } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
	options: { type: Array, default: () => [] }, // [{ value, label }]
	modelValue: { type: [String, Number, Array, null], default: null },
	multiple: { type: Boolean, default: false },
	placeholder: { type: String, default: 'Select…' },
})
const emit = defineEmits(['update:modelValue', 'change'])

// Keep the native <select>'s DOM value in sync with modelValue even when the
// options arrive asynchronously (otherwise the browser falls back to the
// placeholder once the matching <option> appears after the initial render).
const singleEl = ref(null)
watch(
	[() => props.modelValue, () => props.options],
	() => {
		if (props.multiple) return
		nextTick(() => {
			if (singleEl.value) singleEl.value.value = props.modelValue ?? ''
		})
	},
	{ immediate: true },
)

const selected = computed(() => (Array.isArray(props.modelValue) ? props.modelValue : []))
const available = computed(() => props.options.filter((o) => !selected.value.includes(o.value)))
const labelFor = (v) => props.options.find((o) => o.value === v)?.label ?? v

function onSingle(e) {
	const v = e.target.value || null
	emit('update:modelValue', v)
	emit('change', v)
}
function onAdd(e) {
	const v = e.target.value
	e.target.value = ''
	if (!v) return
	const next = [...selected.value, v]
	emit('update:modelValue', next)
	emit('change', next)
}
function removeItem(v) {
	const next = selected.value.filter((x) => x !== v)
	emit('update:modelValue', next)
	emit('change', next)
}
</script>

<template>
	<!-- multiple: chips + an "add" select -->
	<div v-if="multiple" class="pjx-nsel">
		<div v-if="selected.length" class="pjx-nsel__chips">
			<span v-for="v in selected" :key="v" class="pjx-nsel__chip">
				{{ labelFor(v) }}
				<button type="button" class="pjx-nsel__x" @click="removeItem(v)"><Icon name="x" :size="11" /></button>
			</span>
		</div>
		<div class="pjx-nsel__wrap">
			<select class="pjx-nsel__el" :value="''" @change="onAdd">
				<option value="">{{ selected.length ? 'Add more…' : placeholder }}</option>
				<option v-for="o in available" :key="o.value" :value="o.value">{{ o.label }}</option>
			</select>
			<Icon class="pjx-nsel__chev" name="chevron-down" :size="14" />
		</div>
	</div>

	<!-- single -->
	<div v-else class="pjx-nsel__wrap">
		<select ref="singleEl" class="pjx-nsel__el" :value="modelValue || ''" @change="onSingle">
			<option value="">{{ placeholder }}</option>
			<option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
		</select>
		<Icon class="pjx-nsel__chev" name="chevron-down" :size="14" />
	</div>
</template>

<style scoped>
.pjx-nsel {
	display: flex;
	flex-direction: column;
	gap: 6px;
}
.pjx-nsel__chips {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
}
.pjx-nsel__chip {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 2px 4px 2px 8px;
	font-size: 12px;
	border-radius: 6px;
	background: var(--surface-gray-3);
	color: var(--ink-gray-8);
}
.pjx-nsel__x {
	display: inline-flex;
	border: 0;
	background: transparent;
	cursor: pointer;
	color: var(--ink-gray-5);
	padding: 1px;
	border-radius: 4px;
}
.pjx-nsel__x:hover {
	color: var(--ink-gray-8);
	background: var(--surface-gray-4);
}
.pjx-nsel__wrap {
	position: relative;
	width: 100%;
}
.pjx-nsel__el {
	width: 100%;
	appearance: none;
	-webkit-appearance: none;
	padding: 0 28px 0 10px;
	height: 28px;
	font-size: 13px;
	font-family: var(--font-sans);
	color: var(--ink-gray-8);
	background: var(--surface-gray-2);
	border: 1px solid transparent;
	border-radius: 8px;
	cursor: pointer;
}
.pjx-nsel__el:hover {
	background: var(--surface-gray-3);
}
.pjx-nsel__el:focus {
	outline: none;
	border-color: var(--outline-gray-3);
	background: var(--surface-white);
}
.pjx-nsel__chev {
	position: absolute;
	right: 8px;
	top: 50%;
	transform: translateY(-50%);
	pointer-events: none;
	color: var(--ink-gray-5);
}
</style>
