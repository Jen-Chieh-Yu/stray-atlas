import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'

/** Close the ?animal=<id> dialog.
 *
 *  Opening pushed a history entry, so when the entry before it is this same
 *  view without the dialog, going back is the honest close: it pops that
 *  entry instead of leaving a duplicate behind for Back to land on twice.
 *  A dialog opened from a shared link has no such entry; replace then.
 *
 *  Used by: HomeView.vue and AnimalsView.vue. AnimalGrid.vue (still on the
 *  shelter page) keeps its own replace-only close until that page is rebuilt. */
export function closeAnimalDialog(router: Router, route: RouteLocationNormalizedLoaded) {
  const query = { ...route.query }
  delete query.animal
  const target = router.resolve({ path: route.path, query }).fullPath
  const back = (window.history.state as { back?: string | null } | null)?.back
  if (back === target) router.back()
  else void router.replace({ query })
}
