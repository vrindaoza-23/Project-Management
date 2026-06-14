import { createRouter, createWebHistory } from 'vue-router'

const routes = [
	{ path: '/', redirect: '/inbox' },
	{ path: '/inbox', name: 'Inbox', component: () => import('@/pages/InboxView.vue') },
	{ path: '/my-tasks', name: 'MyTasks', component: () => import('@/pages/MyTasksView.vue') },
	{ path: '/roadmap', name: 'Roadmap', component: () => import('@/pages/RoadmapView.vue') },
	{
		path: '/projects/:key',
		name: 'Project',
		component: () => import('@/pages/ProjectView.vue'),
		// `key` is reserved in Vue templates; expose the param as projectKey.
		props: (route) => ({ projectKey: route.params.key }),
	},
	{ path: '/:pathMatch(.*)*', redirect: '/inbox' },
]

// Served under /projex by the Frappe website route.
const router = createRouter({
	history: createWebHistory('/projex'),
	routes,
})

export default router
