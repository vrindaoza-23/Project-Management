// ECharts renders CSS `var(...)` colors fine as SVG attributes, but its
// hover/emphasis pass parses the color string to compute highlight styles —
// `var(...)` fails to parse and the hovered slice/bar/line turns invisible.
// Resolve variables to their concrete values at config build time instead.
export function cssColor(color) {
	if (!color?.startsWith?.('var(')) return color
	const name = color.slice(4, -1).trim()
	return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || color
}
