import { createRouter, createWebHistory } from 'vue-router'

/** CLAUDE.md 2.2: the router base, vite's `base` and every data fetch must all
 *  agree on /stray-atlas/. Reading it from BASE_URL keeps them from drifting.
 *
 *  History mode on GitHub Pages needs a 404.html that serves the app, or a
 *  refresh on /shelters/<id> returns the Pages 404. vite.config.ts writes one
 *  at build time.
 *
 *  Used by: main.ts (app.use). Views reach it through useRoute/useRouter.
 */
export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
    { path: '/animals', name: 'animals', component: () => import('@/views/AnimalsView.vue') },
    { path: '/shelters', name: 'shelters', component: () => import('@/views/ShelterListView.vue') },
    { path: '/shelters/:id', name: 'shelter', component: () => import('@/views/ShelterView.vue') },
    { path: '/map', name: 'map', component: () => import('@/views/MapView.vue') },
    { path: '/analysis', name: 'analysis', component: () => import('@/views/AnalysisView.vue') },
    { path: '/about', name: 'about', component: () => import('@/views/AboutView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
