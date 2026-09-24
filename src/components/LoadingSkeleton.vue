<script setup lang="ts">
/** The placeholder a page shows while its data is on the way (DESIGN.md §14).
 *
 *  Three shapes, because the pages have three: 'cards' is the round-photo grid
 *  on the home and animals pages, 'rows' is the shelter list, and 'block' is a
 *  single card-sized rectangle for the pages whose first content is one large
 *  card — the map and the two analysis pages. Rows there would promise a list
 *  that never arrives, which is the one thing a skeleton must not do.
 *
 *  Nothing is shown for the first 150 ms. Every data file is fetched at most
 *  once per visit (useAtlasData.ts), so a reader who switches tabs and comes
 *  back gets the page immediately; without the delay that reader sees a flash
 *  of grey boxes, which reads worse than the sentence this replaces. On a
 *  local dev server nothing is ever shown, because nothing ever takes 150 ms:
 *  throttle the network in the browser's dev tools to see it at all.
 *
 *  The shapes are aria-hidden and one role="status" line carries the state, so
 *  a screen reader hears 載入中 once rather than a list of empty boxes. The
 *  line is inside the delayed block on purpose: it is announced when it
 *  appears, and a cached page never announces anything.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

withDefaults(
  defineProps<{
    variant?: 'cards' | 'rows' | 'block'
    /** Ignored by 'block'. Enough to fill the fold, not the whole page: the
     *  skeleton is a promise about the layout, not about the row count. */
    count?: number
    /** Names what the wait is for, on the two pages that wait on a big file. */
    hint?: string
  }>(),
  { variant: 'rows', count: 4, hint: '' },
)

const shown = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined

onMounted(() => {
  timer = setTimeout(() => (shown.value = true), 150)
})
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <div v-if="shown" class="loading">
    <p class="say" role="status">載入中…<template v-if="hint">（{{ hint }}）</template></p>

    <div v-if="variant === 'cards'" class="cards" aria-hidden="true">
      <div v-for="index in count" :key="index" class="card">
        <span class="sk avatar"></span>
        <span class="sk line w70"></span>
        <span class="sk line w45"></span>
        <span class="sk bar"></span>
      </div>
    </div>

    <div v-else-if="variant === 'rows'" class="rows" aria-hidden="true">
      <div v-for="index in count" :key="index" class="row">
        <span class="sk line w60"></span>
        <span class="sk line w35"></span>
        <span class="sk line w25"></span>
      </div>
    </div>

    <div v-else class="block" aria-hidden="true">
      <span class="sk line w35"></span>
      <span class="sk area"></span>
    </div>
  </div>
</template>

<style scoped>
.say {
  margin: 0 0 1rem;
  color: var(--ink-muted);
}

/* --no-data is the map's "no data" grey. Reused rather than a new value: a
   placeholder and an empty county mean the same thing, "nothing here yet". */
.sk {
  position: relative;
  display: block;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: var(--no-data);
}

/* One pass of the page colour, not a pulse: a pulsing block competes with the
   reveal fade every section already has (src/lib/reveal.ts). --plane rather
   than --surface because the widest shapes sit on cards that are already
   --surface, where a --surface sweep is invisible. */
.sk::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, var(--plane), transparent);
  animation: sweep 1.25s ease-in-out infinite;
}

@keyframes sweep {
  to {
    transform: translateX(100%);
  }
}

.line {
  height: 12px;
}

.w70 {
  width: 70%;
}

.w60 {
  width: 60%;
}

.w45 {
  width: 45%;
}

.w35 {
  width: 35%;
}

.w25 {
  width: 25%;
}

/* ── cards: AnimalCard's shape, in AnimalsView's grid and at its breakpoint ── */
.cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 2rem 1.5rem;
}

.card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
}

.avatar {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 999px;
}

.bar {
  width: 100%;
  height: 4px;
  border-radius: 999px;
}

/* ── rows: the shelter list's row card ── */
.rows {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.1rem 1.3rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
}

/* ── block: one card, for a page that opens on a chart or a map ── */
.block {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1.5rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
}

/* The charts are drawn on a 900 × 360 viewBox at width: 100%, so the space
   the first one will occupy is that ratio, whatever the column is doing. */
.area {
  aspect-ratio: 900 / 360;
  min-height: 180px;
}

@media (max-width: 820px) {
  .cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* The sweep is decoration; the layout it reserves is the point. */
@media (prefers-reduced-motion: reduce) {
  .sk::after {
    display: none;
  }
}
</style>
