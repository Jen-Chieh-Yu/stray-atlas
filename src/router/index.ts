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
// Read by App.vue: a full-bleed page lays out its own columns.
declare module 'vue-router' {
  interface RouteMeta {
    fullBleed?: boolean
  }
}

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      // The hero and the orange bands run edge to edge, so the page lays out
      // its own columns instead of sitting inside the shell's .wrap.
      meta: { fullBleed: true },
    },
    { path: '/animals', name: 'animals', component: () => import('@/views/AnimalsView.vue') },
    { path: '/shelters', name: 'shelters', component: () => import('@/views/ShelterListView.vue') },
    { path: '/shelters/:id', name: 'shelter', component: () => import('@/views/ShelterView.vue') },
    { path: '/map', name: 'map', component: () => import('@/views/MapView.vue') },
    { path: '/quality', name: 'quality', component: () => import('@/views/QualityView.vue') },
    { path: '/analysis', name: 'analysis', component: () => import('@/views/AnalysisView.vue') },
    { path: '/about', name: 'about', component: () => import('@/views/AboutView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  // Top of the page on a new path only. A query-only change is a filter, a
  // page of results or an opened dialog, and jumping to the top on those
  // throws away the place the reader was looking at; the views that want a
  // scroll (the pager) do it themselves. Back and forward restore as usual.
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.path === from.path) return false
    return { top: 0 }
  },
})
