<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import { createResource } from 'frappe-ui'
import StatusDot from '@/components/StatusDot.vue'
import BoardCard from '@/components/BoardCard.vue'
import { notifyError } from '@/utils/feedback'

const props = defineProps({
	issues: { type: Array, default: () => [] },
	statuses: { type: Array, default: () => [] },
	presence: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['open', 'changed'])

const overStatus = ref(null)

const columns = computed(() =>
	[...props.statuses]
		.sort((a, b) => (a.position || 0) - (b.position || 0))
		.map((s) => ({ status: s, items: props.issues.filter((i) => i.status === s.name) })),
)

const updater = createResource({ url: 'projex.api.update_issue' })

// --------------------------------------------------------------------------- //
// Pointer-based drag — reliable on trackpads & every browser, smooth on video.
// The native HTML5 DnD API (draggable=true) was flaky to pick up on trackpads
// and rendered an ugly default ghost; this owns the gesture end-to-end.
// --------------------------------------------------------------------------- //
const THRESHOLD = 5 // px of movement before a press becomes a drag (vs. a click)
let drag = null // { issue, srcEl, startX, startY, offX, offY, ghost, started }

function onPickup({ issue, event, el }) {
	drag = {
		issue,
		srcEl: el,
		startX: event.clientX,
		startY: event.clientY,
		offX: 0,
		offY: 0,
		ghost: null,
		started: false,
	}
	window.addEventListener('pointermove', onMove)
	window.addEventListener('pointerup', onUp, { once: true })
}

function onMove(e) {
	if (!drag) return
	if (!drag.started) {
		if (Math.hypot(e.clientX - drag.startX, e.clientY - drag.startY) < THRESHOLD) return
		beginGhost(e)
	}
	moveGhost(e)
	overStatus.value = columnAt(e.clientX, e.clientY)
}

function beginGhost(e) {
	drag.started = true
	document.body.classList.add('pjx-dragging')
	const rect = drag.srcEl.getBoundingClientRect()
	drag.offX = e.clientX - rect.left
	drag.offY = e.clientY - rect.top
	const g = drag.srcEl.cloneNode(true)
	g.classList.add('pjx-card--ghost')
	g.style.width = `${rect.width}px`
	document.body.appendChild(g)
	drag.ghost = g
	drag.srcEl.classList.add('pjx-card--dragsrc')
}

function moveGhost(e) {
	if (drag.ghost) {
		drag.ghost.style.transform = `translate(${e.clientX - drag.offX}px, ${e.clientY - drag.offY}px) rotate(2.5deg)`
	}
}

// Which column is under the cursor? Ghost has pointer-events:none so it's skipped.
function columnAt(x, y) {
	const el = document.elementFromPoint(x, y)
	const col = el && el.closest('[data-status]')
	return col ? col.getAttribute('data-status') : null
}

async function onUp(e) {
	window.removeEventListener('pointermove', onMove)
	const d = drag
	drag = null
	if (!d) return

	// A press that never crossed the threshold is a click → open the task.
	if (!d.started) {
		emit('open', d.issue.name)
		return
	}

	if (d.ghost) d.ghost.remove()
	d.srcEl.classList.remove('pjx-card--dragsrc')
	document.body.classList.remove('pjx-dragging')

	const target = columnAt(e.clientX, e.clientY)
	overStatus.value = null
	if (!target || target === d.issue.status) return

	const issue = props.issues.find((i) => i.name === d.issue.name)
	if (!issue) return
	const prev = issue.status
	issue.status = target // optimistic
	try {
		await updater.submit({ name: issue.name, fields: JSON.stringify({ status: target }) })
		emit('changed')
	} catch (err) {
		issue.status = prev // rollback
		notifyError(err, 'Could not move task')
	}
}

onBeforeUnmount(() => {
	window.removeEventListener('pointermove', onMove)
	if (drag && drag.ghost) drag.ghost.remove()
	document.body.classList.remove('pjx-dragging')
})
</script>

<template>
	<div class="pjx-board">
		<div class="pjx-board__cols">
			<div
				v-for="col in columns"
				:key="col.status.name"
				class="pjx-col"
				:data-status="col.status.name"
				:class="{ 'is-over': overStatus === col.status.name }"
			>
				<div class="pjx-col__head">
					<StatusDot :status="col.status" />
					<span class="pjx-col__name">{{ col.status.status_name }}</span>
					<span class="pjx-col__count">{{ col.items.length }}</span>
				</div>
				<div class="pjx-col__body">
					<BoardCard
						v-for="it in col.items"
						:key="it.name"
						:issue="it"
						:presence="presence[it.name] || []"
						@pickup="onPickup"
					/>
					<div v-if="!col.items.length" class="pjx-col__empty">Drop tasks here</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.pjx-col.is-over {
	outline: 2px solid var(--outline-blue-2, var(--blue-400));
	outline-offset: -2px;
	background: var(--surface-blue-1, rgba(59, 130, 246, 0.04));
}
</style>
