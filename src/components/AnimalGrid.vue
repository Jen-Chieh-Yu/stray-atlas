<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AnimalDialog from '@/components/AnimalDialog.vue'
import { daysInShelter } from '@/composables/useAtlasData'
import type { Animal, KindFilter, Shelter } from '@/types'

const props = defineProps<{
  animals: Animal[]
  snapshotDate: string
  /** Present on the browse-everything page, where a card has to say where the
   *  animal is; omitted on a shelter's own page, where it would repeat. */
  shelters?: Map<string, Shelter>
}>()

const route = useRoute()
const router = useRouter()

type Sort = 'longest' | 'shortest'

const kind = ref<KindFilter>('all')
const variety = ref('all')
const bucket = ref<number | null>(null)
const sort = ref<Sort>('longest')
const broken = ref(new Set<string>())

const PER_PAGE = 24

const BUCKETS: { label: string; min: number; max: number | null }[] = [
  { label: '30 天內', min: 0, max: 30 },
  { label: '31–90 天', min: 31, max: 90 },
  { label: '91–365 天', min: 91, max: 365 },
  { label: '1–2 年', min: 366, max: 730 },
  { label: '2 年以上', min: 731, max: null },
]

const SORTS: { id: Sort; label: string }[] = [
  { id: 'longest', label: '已在所天數由長到短' },
  { id: 'shortest', label: '已在所天數由短到長' },
]

const SEX: Record<string, string> = { M: '公', F: '母', N: '未填' }
const BODY: Record<string, string> = { SMALL: '小型', MEDIUM: '中型', BIG: '大型' }
const AGE: Record<string, string> = { ADULT: '成體', CHILD: '幼體' }

function days(animal: Animal): number | null {
  return daysInShelter(animal.created, props.snapshotDate)
}

/** Short form for the badge over the photo: years past one year, days below. */
function badge(value: number | null): string {
  if (value === null) return '天數未知'
  if (value < 30) return `在所 ${value} 天`
  if (value < 365) return `在所 ${value} 天`
  return `在所 ${(value / 365).toFixed(1)} 年`
}

/** The badge over the photo already carries the round figure in years, so the
 *  body line gives the exact day count and nothing else — spelling both out
 *  wrapped every card in the grid onto a second line. */
function label(value: number | null): string {
  return value === null ? '天數未知' : `已在所 ${value.toLocaleString('zh-TW')} 天`
}

const kindCounts = computed(() => {
  const counts = new Map<string, number>()
  for (const animal of props.animals) {
    counts.set(animal.kind, (counts.get(animal.kind) ?? 0) + 1)
  }
  return counts
})

const byKind = computed(() =>
  kind.value === 'all'
    ? props.animals
    : props.animals.filter((animal) => animal.kind === kind.value),
)

/** A dropdown rather than chips: this list is dozens of entries at one shelter
 *  and two at another, so its length is not known in advance — which is where
 *  a fixed row of chips stops working. Scoped to the kind already chosen. */
const varieties = computed(() => {
  const counts = new Map<string, number>()
  for (const animal of byKind.value) {
    const name = animal.variety || '未填品種'
    counts.set(name, (counts.get(name) ?? 0) + 1)
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-TW'))
})

const filtered = computed(() => {
  const list = byKind.value.filter((animal) => {
    if (variety.value !== 'all' && (animal.variety || '未填品種') !== variety.value) return false
    if (bucket.value === null) return true
    const band = BUCKETS[bucket.value]
    const value = days(animal)
    if (value === null) return false
    return value >= band.min && (band.max === null || value <= band.max)
  })
  // The file arrives oldest-first; reversing is cheaper than re-sorting.
  return sort.value === 'longest' ? list : [...list].reverse()
})

const pageCount = computed(() => Math.max(1, Math.ceil(filtered.value.length / PER_PAGE)))

/** The page number lives in the query string, like the open animal does.
 *  Reading it back rather than holding it in local state means Back returns to
 *  the page the reader came from, a link points at the right page, and closing
 *  the dialog does not drop them at the top of the list again. */
const page = computed(() => {
  const raw = Number(route.query.page)
  if (!Number.isInteger(raw) || raw < 1) return 1
  return Math.min(raw, pageCount.value)
})

const visible = computed(() =>
  filtered.value.slice((page.value - 1) * PER_PAGE, page.value * PER_PAGE),
)

const firstIndex = computed(() =>
  filtered.value.length === 0 ? 0 : (page.value - 1) * PER_PAGE + 1,
)
const lastIndex = computed(() => Math.min(page.value * PER_PAGE, filtered.value.length))

/** 345 pages at the widest, so the pager shows the ends, a window around the
 *  current page, and gaps for everything between. */
const pageItems = computed<(number | 'gap')[]>(() => {
  const total = pageCount.value
  const current = page.value
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)

  const window = new Set([1, total, current, current - 1, current + 1])
  if (current <= 3) [2, 3, 4].forEach((n) => window.add(n))
  if (current >= total - 2) [total - 3, total - 2, total - 1].forEach((n) => window.add(n))

  const pages = [...window].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b)
  const items: (number | 'gap')[] = []
  let previous = 0
  for (const value of pages) {
    if (value - previous > 1) items.push('gap')
    items.push(value)
    previous = value
  }
  return items
})

function goTo(next: number, replace = false) {
  const target = Math.min(Math.max(next, 1), pageCount.value)
  const query = { ...route.query }
  if (target === 1) delete query.page
  else query.page = String(target)
  const to = { query }
  void (replace ? router.replace(to) : router.push(to))
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const touched = computed(
  () => kind.value !== 'all' || variety.value !== 'all' || bucket.value !== null,
)

function reset() {
  kind.value = 'all'
  variety.value = 'all'
  bucket.value = null
}

// A narrower result set can leave the reader on a page that no longer exists;
// replace rather than push, so Back does not walk through phantom pages.
watch([() => props.animals, kind, variety, bucket, sort], () => {
  if (route.query.page) goTo(1, true)
})

watch(pageCount, (count) => {
  if (page.value > count) goTo(count, true)
})

watch(kind, () => {
  variety.value = 'all'
})

/** The open animal lives in the query string. A dialog keeps the reader's
 *  scroll position and filters, which a navigation would lose after several
 *  hundred cards; the URL keeps what a separate page would have given — the
 *  view stays linkable and Back closes it. */
const openAnimal = computed<Animal | null>(() => {
  const id = route.query.animal
  if (typeof id !== 'string') return null
  return props.animals.find((animal) => animal.id === id) ?? null
})

function open(animal: Animal) {
  void router.push({ query: { ...route.query, animal: animal.id } })
}

function close() {
  const query = { ...route.query }
  delete query.animal
  void router.replace({ query })
}

// A filter that hides the open animal should not leave the dialog showing
// something the list behind it no longer contains.
watch(filtered, (list) => {
  const current = openAnimal.value
  if (current && !list.some((animal) => animal.id === current.id)) close()
})
</script>

<template>
  <div>
    <section class="card filters">
      <!-- The scope controls (county, shelter) belong to the page, not to this
           component, but they read as one filter panel — so the page injects
           them here rather than stacking a second card above. -->
      <div v-if="$slots.scope" class="scope">
        <slot name="scope" />
      </div>

      <div class="rows">
        <div class="row">
          <fieldset>
            <legend>動物類型</legend>
            <button
              type="button"
              :class="{ chip: true, small: true, on: kind === 'all' }"
              @click="kind = 'all'"
            >
              全部
            </button>
            <button
              v-for="option in (['狗', '貓'] as const)"
              :key="option"
              type="button"
              :class="{ chip: true, small: true, on: kind === option }"
              @click="kind = option"
            >
              {{ option }}（{{ (kindCounts.get(option) ?? 0).toLocaleString('zh-TW') }}）
            </button>
          </fieldset>

          <div class="select-field">
            <label for="variety">品種</label>
            <select id="variety" v-model="variety">
              <option value="all">全品種（{{ byKind.length.toLocaleString('zh-TW') }} 隻）</option>
              <option v-for="[name, count] in varieties" :key="name" :value="name">
                {{ name }}（{{ count.toLocaleString('zh-TW') }}）
              </option>
            </select>
          </div>
        </div>

        <fieldset>
          <legend>已在所天數</legend>
          <button
            type="button"
            :class="{ chip: true, small: true, on: bucket === null }"
            @click="bucket = null"
          >
            不限
          </button>
          <button
            v-for="(band, index) in BUCKETS"
            :key="band.label"
            type="button"
            :class="{ chip: true, small: true, on: bucket === index }"
            @click="bucket = index"
          >
            {{ band.label }}
          </button>
        </fieldset>
      </div>
    </section>

    <div class="resultbar">
      <p class="count">
        符合條件 <strong>{{ filtered.length.toLocaleString('zh-TW') }}</strong> 隻，{{
          sort === 'longest' ? '依已在所天數由長到短排列' : '依已在所天數由短到長排列'
        }}。<span v-if="filtered.length" class="range">
          目前顯示第 {{ firstIndex.toLocaleString('zh-TW') }}–{{
            lastIndex.toLocaleString('zh-TW')
          }} 筆
        </span>
      </p>

      <div class="tools">
        <button v-if="touched" type="button" class="linkish" @click="reset">清除篩選</button>
        <span v-if="touched" class="divider" aria-hidden="true">|</span>
        <label class="sort">
          排序
          <select v-model="sort">
            <option v-for="option in SORTS" :key="option.id" :value="option.id">
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>
    </div>

    <ul class="grid">
      <li v-for="animal in visible" :key="animal.id">
        <button type="button" class="card animal" @click="open(animal)">
          <div class="photo">
            <img
              v-if="animal.photo && !broken.has(animal.id)"
              :src="animal.photo"
              :alt="`${animal.variety}，${SEX[animal.sex] ?? animal.sex}`"
              loading="lazy"
              decoding="async"
              referrerpolicy="no-referrer"
              @error="broken.add(animal.id)"
            />
            <span v-else class="no-photo">
              <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                <path
                  d="M3 5h18v14H3z M3 16l5-5 4 4 3-3 6 6"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                  stroke-linejoin="round"
                />
              </svg>
              {{ animal.photo ? '照片無法載入' : '無照片' }}
            </span>
            <span class="badge">{{ badge(days(animal)) }}</span>
          </div>

          <div class="body">
            <p class="head">
              <span class="variety">{{ animal.variety || '未填品種' }}</span>
              <span class="subid">#{{ animal.subid }}</span>
            </p>
            <p class="meta">
              {{ SEX[animal.sex] ?? animal.sex }} ·
              {{ BODY[animal.body] ?? animal.body }} ·
              {{ AGE[animal.age] ?? '年齡未填' }}
              <template v-if="animal.colour"> · {{ animal.colour }}</template>
            </p>
            <p class="days">{{ label(days(animal)) }}</p>
            <p v-if="shelters" class="where">
              {{ shelters.get(animal.shelter)?.name ?? '未知收容所' }}
              <span v-if="shelters.get(animal.shelter)?.tel" class="tel">
                {{ shelters.get(animal.shelter)?.tel }}
              </span>
            </p>
          </div>
        </button>
      </li>
    </ul>

    <nav v-if="filtered.length" class="pager" aria-label="分頁">
      <button
        type="button"
        class="page-btn"
        :disabled="page === 1"
        aria-label="上一頁"
        @click="goTo(page - 1)"
      >
        ‹ 上一頁
      </button>

      <ul class="pages">
        <li v-for="(item, index) in pageItems" :key="`${item}-${index}`">
          <span v-if="item === 'gap'" class="gap" aria-hidden="true">…</span>
          <button
            v-else
            type="button"
            :class="{ 'page-btn': true, num: true, on: item === page }"
            :aria-current="item === page ? 'page' : undefined"
            @click="goTo(item)"
          >
            {{ item }}
          </button>
        </li>
      </ul>

      <button
        type="button"
        class="page-btn"
        :disabled="page === pageCount"
        aria-label="下一頁"
        @click="goTo(page + 1)"
      >
        下一頁 ›
      </button>
    </nav>

    <p class="progress">
      <template v-if="filtered.length">
        第 {{ page.toLocaleString('zh-TW') }} / {{ pageCount.toLocaleString('zh-TW') }} 頁 · 每頁
        {{ PER_PAGE }} 筆 · 共 {{ filtered.length.toLocaleString('zh-TW') }} 筆
      </template>
      <template v-else>沒有符合條件的動物。</template>
    </p>

    <AnimalDialog
      v-if="openAnimal"
      :animal="openAnimal"
      :snapshot-date="snapshotDate"
      :shelter="shelters?.get(openAnimal.shelter)"
      @close="close"
    />
  </div>
</template>

<style scoped>
.filters {
  padding: 0;
  margin-bottom: 1rem;
}

.scope {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem 2.5rem;
  padding: 1.1rem 1.25rem;
  border-bottom: 1px solid var(--hairline);
}

.rows {
  display: grid;
  gap: 0.85rem;
  padding: 1.1rem 1.25rem;
}

.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.9rem 2rem;
}

fieldset {
  border: 0;
  margin: 0;
  padding: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
}

legend {
  float: left;
  margin-right: 0.6rem;
  font-size: 0.85rem;
  color: var(--ink-muted);
}

.select-field {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.select-field label {
  font-size: 0.85rem;
  color: var(--ink-muted);
}

select {
  font: inherit;
  font-size: 0.85rem;
  padding: 0.32rem 0.65rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--hairline);
  background: var(--surface);
  color: var(--ink);
  max-width: 16rem;
}

select:hover {
  border-color: var(--ramp-3);
}

.resultbar {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.9rem;
}

.count {
  margin: 0;
  font-size: 0.9rem;
  color: var(--ink-secondary);
}

.count strong {
  color: var(--accent-text);
  font-variant-numeric: tabular-nums;
}

.tools {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.85rem;
  color: var(--ink-muted);
}

.linkish {
  font: inherit;
  border: 0;
  background: none;
  color: var(--ink-secondary);
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.linkish:hover {
  color: var(--accent-text);
}

.divider {
  color: var(--hairline);
}

.sort {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  /* Equal-height rows, so a two-line breed name does not make one card taller
     than its neighbours. */
  grid-auto-rows: 1fr;
}

.animal {
  padding: 0;
  overflow: hidden;
  display: grid;
  grid-template-rows: auto 1fr;
  width: 100%;
  height: 100%;
  text-align: left;
  font: inherit;
  color: inherit;
  cursor: pointer;
  transition:
    border-color 120ms ease,
    transform 120ms ease;
}

.animal:hover {
  border-color: var(--ramp-3);
  transform: translateY(-2px);
}

.animal:focus-visible {
  outline: 2px solid var(--ramp-4);
  outline-offset: 2px;
}

.photo {
  /* Absolute positioning rather than height:100% on the image: in normal flow
     the image's intrinsic height resolves against a container whose own height
     comes from aspect-ratio, so a portrait photo stretched its card and the
     grid came out ragged. */
  position: relative;
  aspect-ratio: 4 / 3;
  background: var(--surface-sunk);
  display: grid;
  place-items: center;
  overflow: hidden;
}

.photo img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.no-photo {
  display: grid;
  justify-items: center;
  gap: 0.3rem;
  font-size: 0.78rem;
  color: var(--ink-muted);
}

.badge {
  position: absolute;
  top: 0.5rem;
  left: 0.5rem;
  padding: 0.12rem 0.5rem;
  border-radius: var(--radius-sm);
  background: var(--surface);
  border: 1px solid var(--hairline);
  font-size: 0.74rem;
  color: var(--ink-secondary);
  font-variant-numeric: tabular-nums;
}

.body {
  padding: 0.75rem 0.9rem 0.9rem;
  display: grid;
  gap: 0.25rem;
  align-content: start;
}

.head {
  margin: 0;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
}

.variety {
  font-weight: 600;
}

.subid {
  font-size: 0.7rem;
  color: var(--ink-muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.meta {
  margin: 0;
  font-size: 0.82rem;
  color: var(--ink-secondary);
}

.days {
  margin: 0.2rem 0 0;
  padding-top: 0.45rem;
  border-top: 1px solid var(--hairline);
  font-size: 0.85rem;
  color: var(--accent-text);
  font-variant-numeric: tabular-nums;
}

.where {
  margin: 0;
  font-size: 0.78rem;
  color: var(--ink-muted);
  display: grid;
  gap: 0.1rem;
}

.tel {
  font-variant-numeric: tabular-nums;
}

.range {
  color: var(--ink-muted);
  margin-left: 0.35rem;
  font-variant-numeric: tabular-nums;
}

.pager {
  margin-top: 1.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.pages {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.page-btn {
  font: inherit;
  font-size: 0.85rem;
  padding: 0.34rem 0.7rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--hairline);
  background: var(--surface);
  color: var(--ink-secondary);
  cursor: pointer;
  transition: all 120ms ease;
  font-variant-numeric: tabular-nums;
}

.page-btn.num {
  min-width: 2.35rem;
}

.page-btn:hover:not(:disabled) {
  border-color: var(--ramp-3);
  color: var(--ink);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.page-btn.on {
  background: var(--ramp-4);
  border-color: var(--ramp-4);
  color: #fff;
}

.gap {
  display: inline-block;
  padding: 0 0.2rem;
  color: var(--ink-muted);
}

.progress {
  margin: 0.85rem 0 0;
  text-align: center;
  font-size: 0.8rem;
  color: var(--ink-muted);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 700px) {
  .row {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>
