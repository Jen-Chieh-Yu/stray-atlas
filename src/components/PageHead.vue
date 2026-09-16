<script setup lang="ts">
import { useAtlasData } from '@/composables/useAtlasData'

/** Title block shared by every page: h1, one lede paragraph, and the snapshot
 *  stamp at the end of the lede. The stamp used to sit in the site masthead;
 *  it moved here with the draft layout so each page carries its own date.
 *
 *  Used by: HomeView.vue and AboutView.vue (both placeholders for now). */
defineProps<{ title: string }>()

const { stats } = useAtlasData()
</script>

<template>
  <header class="pagehead">
    <h1>{{ title }}</h1>
    <p>
      <slot />
      <span v-if="stats" class="stamp">資料快照 {{ stats.snapshot_date }}</span>
    </p>
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

.stamp {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.05rem 0.6rem;
  border-radius: 999px;
  background: var(--surface-sunk);
  font-size: 0.8rem;
  color: var(--ink-muted);
  font-variant-numeric: tabular-nums;
}
</style>
