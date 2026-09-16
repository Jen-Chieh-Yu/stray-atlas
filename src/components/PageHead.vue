<script setup lang="ts">
/** Title block shared by every page: h1 and one lede paragraph. The snapshot
 *  date is stated once, in the site footer (App.vue).
 *
 *  Used by: AboutView.vue, AnimalsView.vue, ShelterListView.vue, MapView.vue
 *  and AnalysisView.vue. The home page has its own hero instead. */
defineProps<{ title: string }>()
</script>

<template>
  <header class="pagehead">
    <h1>{{ title }}</h1>
    <p><slot /></p>
  </header>
</template>

<style scoped>
h1 {
  font-size: clamp(1.6rem, 3.4vw, 2.2rem);
}

p {
  margin: 0.6rem 0 0;
  max-width: 44rem;
  color: var(--ink-secondary);
}
</style>
