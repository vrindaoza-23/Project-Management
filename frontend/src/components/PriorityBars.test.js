import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PriorityBars from './PriorityBars.vue'

describe('PriorityBars', () => {
	it('renders 3 bars for a priority level', () => {
		const w = mount(PriorityBars, { props: { priority: 'High' } })
		expect(w.findAll('.pjx-prio__bar').length).toBe(3)
	})

	it('renders the minus icon for None', () => {
		const w = mount(PriorityBars, { props: { priority: 'None' } })
		expect(w.findAll('.pjx-prio__bar').length).toBe(0)
	})
})
