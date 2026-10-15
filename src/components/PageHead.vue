<script setup lang="ts">
/** Title block shared by every page: h1 and one lede paragraph. The snapshot
 *  date is stated once, in the site footer (App.vue).
 *
 *  `back` is for a page the top bar does not list (資料品質, 資料分析): it
 *  names the place the reader came in from, since the bar cannot.
 *
 *  Used by: AboutView.vue, AnimalsView.vue, ShelterListView.vue, MapView.vue,
 *  QualityView.vue and AnalysisView.vue. The home page has its own hero
 *  instead. */
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import LucideIcon from '@/components/LucideIcon.vue'

defineProps<{ title: string; back?: { to: RouteLocationRaw; label: string } }>()
</script>

<template>
  <header class="pagehead">
    <RouterLink v-if="back" :to="back.to" class="back">
      <LucideIcon name="chevron-left" :size="16" />{{ back.label }}
    </RouterLink>
    <h1>{{ title }}</h1>
    <p><slot /></p>
  </header>
</template>

<style scoped>
.back {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  margin-bottom: 0.5rem;
  color: var(--accent-text);
  font-size: 0.86rem;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

h1 {
  font-size: clamp(1.6rem, 3.4vw, 2.2rem);
}

p {
  margin: 0.6rem 0 0;
  max-width: 44rem;
  color: var(--ink-secondary);
}
</style>
