<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AnimalCard from '@/components/AnimalCard.vue'
import AnimalDialog from '@/components/AnimalDialog.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import PageHead from '@/components/PageHead.vue'
import { useRoster } from '@/composables/useRoster'
import { closeAnimalDialog } from '@/lib/dialogRoute'
import {
  BODY_LABEL,
  DAY_BANDS,
  SEX_LABEL,
  SORTS,
  AGE_LABEL,
  formatCount,
  inBand,
  parseAnimalQuery,
  tally,
  KIND_PARAM,
} from '@/lib/animals'
import type { AnimalQuery, DayBandKey } from '@/lib/animals'
import type { Animal, Kind } from '@/types'

const route = useRoute()
const router = useRouter()

const {
  animals,
  shelters,
  snapshotDate,
  loading,
  error,
  shelterById,
  placeOf,
  countyOf,
  daysOf,
  percentileOf,
  longestId,
} = useRoster()

/** Sixteen a page on a fixed four-column grid (two below 820px), so every
 *  full page ends on a complete row (decided 2026-09-15). */
const PER_PAGE = 16

const KINDS: Kind[] = ['狗', '貓', '其他']

/* ── Filters live in the URL ───────────────────────────────────────────────
 * The query string is the only copy of the filter state. The home page links
 * straight into it, Back steps through it, and a filtered view can be shared.
 * Controls read from `filters` and write through `update`. */

const knownVarieties = computed(
  () => new Set(animals.value.map((animal) => animal.variety || '未填品種')),
)

/** Free-text values are checked against the data here: a county, shelter or
 *  variety that is not in this snapshot is dropped, so an old link widens the
 *  list instead of emptying it. */
const filters = computed<AnimalQuery>(() => {
  const query = parseAnimalQuery(route.query)
  if (animals.value.length === 0) return query
  const counties = new Set(shelters.value.map((shelter) => shelter.county))
  return {
    ...query,
    county: query.county && counties.has(query.county) ? query.county : undefined,
    shelter: query.shelter && shelterById.value.has(query.shelter) ? query.shelter : undefined,
    variety: query.variety && knownVarieties.value.has(query.variety) ? query.variety : undefined,
  }
})

type FilterKey = Exclude<keyof AnimalQuery, 'sort'>

function update(patch: Partial<AnimalQuery>) {
  const next: AnimalQuery = { ...filters.value, ...patch }
  const query: Record<string, string> = {}
  if (next.kind) query.kind = KIND_PARAM[next.kind]
  for (const key of ['county', 'shelter', 'variety', 'sex', 'body', 'age', 'days', 'daysFrom', 'q'] as const) {
    const value = next[key]
    if (value) query[key] = value
  }
  if (next.sort === 'shortest') query.sort = 'shortest'
  // A filter change starts again from page 1 and closes nothing but the pager.
  // Replace rather than push: toggling five chips should not take five Backs.
  void router.replace({ query })
}

function clearAll() {
  void router.replace({ query: filters.value.sort ? { sort: filters.value.sort } : {} })
}

/* ── Matching ──────────────────────────────────────────────────────────── */

function matchesDays(animal: Animal, query: AnimalQuery): boolean {
  if (query.days) {
    const band = DAY_BANDS.find((item) => item.key === query.days)!
    return inBand(daysOf(animal), band.min, band.max)
  }
  if (query.daysFrom) {
    const band = DAY_BANDS.find((item) => item.key === query.daysFrom)!
    return inBand(daysOf(animal), band.min, null)
  }
  return true
}

/** Every word must hit the county, the shelter or the variety — the three
 *  things the home page's search box promises. */
function matchesText(animal: Animal, text: string | undefined): boolean {
  if (!text) return true
  const haystack = `${countyOf(animal)} ${placeOf(animal)} ${animal.variety}`
  return text.split(/\s+/).every((word) => haystack.includes(word))
}

/** All filters except `skip`. Each control counts against this, so its
 *  numbers answer "how many would I get if I picked this". */
function matching(skip: FilterKey | null): Animal[] {
  const query = filters.value
  return animals.value.filter((animal) => {
    if (skip !== 'kind' && query.kind && animal.kind !== query.kind) return false
    if (skip !== 'county' && query.county && countyOf(animal) !== query.county) return false
    if (skip !== 'shelter' && query.shelter && animal.shelter !== query.shelter) return false
    if (skip !== 'variety' && query.variety && (animal.variety || '未填品種') !== query.variety)
      return false
    if (skip !== 'sex' && query.sex && animal.sex !== query.sex) return false
    if (skip !== 'body' && query.body && animal.body !== query.body) return false
    if (skip !== 'age' && query.age && animal.age !== query.age) return false
    if (skip !== 'days' && !matchesDays(animal, query)) return false
    if (skip !== 'q' && !matchesText(animal, query.q)) return false
    return true
  })
}

const results = computed(() => {
  const list = matching(null)
  const direction = filters.value.sort === 'shortest' ? 1 : -1
  return [...list].sort((a, b) => direction * ((daysOf(a) ?? -1) - (daysOf(b) ?? -1)))
})

/* ── Options with counts ───────────────────────────────────────────────── */

function countBy(skip: FilterKey, key: (animal: Animal) => string) {
  return new Map(tally(matching(skip), key))
}

const countyOptions = computed(() => {
  const counts = countBy('county', countyOf)
  const names = [...new Set(shelters.value.map((shelter) => shelter.county))]
  return names
    .map((name) => ({ name, count: counts.get(name) ?? 0 }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, 'zh-TW'))
})

/** Shelters follow the county already chosen. */
const shelterOptions = computed(() => {
  const counts = countBy('shelter', (animal) => animal.shelter)
  return shelters.value
    .filter((shelter) => !filters.value.county || shelter.county === filters.value.county)
    .map((shelter) => ({ id: shelter.id, name: shelter.name, count: counts.get(shelter.id) ?? 0 }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, 'zh-TW'))
})

const kindCounts = computed(() => countBy('kind', (animal) => animal.kind))
const kindTotal = computed(() => matching('kind').length)
const countyTotal = computed(() => matching('county').length)

/** A dropdown, not chips: its length is unknown in advance (dozens at one
 *  shelter, two at another). A variety the other filters rule out is still
 *  listed when it is the one selected, so the control never shows a blank. */
const varietyOptions = computed(() => {
  const options = tally(matching('variety'), (animal) => animal.variety || '未填品種')
  const chosen = filters.value.variety
  if (chosen && !options.some(([name]) => name === chosen)) options.push([chosen, 0])
  return options
})

const sexCounts = computed(() => countBy('sex', (animal) => animal.sex))
const bodyCounts = computed(() => countBy('body', (animal) => animal.body))

const bandCounts = computed(() => {
  const list = matching('days')
  return DAY_BANDS.map((band) => list.filter((animal) => inBand(daysOf(animal), band.min, band.max)).length)
})

function bandOn(key: DayBandKey): boolean {
  const { days, daysFrom } = filters.value
  if (days) return days === key
  if (!daysFrom) return false
  const from = DAY_BANDS.findIndex((band) => band.key === daysFrom)
  return DAY_BANDS.findIndex((band) => band.key === key) >= from
}

/* ── Applied tags ──────────────────────────────────────────────────────── */

const applied = computed(() => {
  const query = filters.value
  const tags: { label: string; clear: Partial<AnimalQuery> }[] = []
  if (query.q) tags.push({ label: `搜尋「${query.q}」`, clear: { q: undefined } })
  if (query.county) tags.push({ label: query.county, clear: { county: undefined, shelter: undefined } })
  if (query.shelter) {
    tags.push({
      label: shelterById.value.get(query.shelter)?.name ?? '指定收容所',
      clear: { shelter: undefined },
    })
  }
  if (query.kind) tags.push({ label: query.kind, clear: { kind: undefined, variety: undefined } })
  if (query.variety) tags.push({ label: query.variety, clear: { variety: undefined } })
  if (query.sex) tags.push({ label: SEX_LABEL[query.sex], clear: { sex: undefined } })
  if (query.body) tags.push({ label: BODY_LABEL[query.body], clear: { body: undefined } })
  // No age row in the draft; the home page links here with one, so it shows as a tag.
  if (query.age) tags.push({ label: AGE_LABEL[query.age], clear: { age: undefined } })
  if (query.days) {
    const band = DAY_BANDS.find((item) => item.key === query.days)!
    tags.push({ label: `已在所 ${band.label}`, clear: { days: undefined } })
  } else if (query.daysFrom) {
    const band = DAY_BANDS.find((item) => item.key === query.daysFrom)!
    tags.push({ label: `已在所 ${formatCount(Math.ceil((band.min - 1) / 365))} 年以上`, clear: { daysFrom: undefined } })
  }
  return tags
})

/* ── Pages ─────────────────────────────────────────────────────────────── */

const pageCount = computed(() => Math.max(1, Math.ceil(results.value.length / PER_PAGE)))

/** The page lives in the query string like everything else, so Back returns to
 *  it and closing the dialog leaves the reader where they were. */
const page = computed(() => {
  const raw = Number(route.query.page)
  if (!Number.isInteger(raw) || raw < 1) return 1
  return Math.min(raw, pageCount.value)
})

const visible = computed(() =>
  results.value.slice((page.value - 1) * PER_PAGE, page.value * PER_PAGE),
)

const firstIndex = computed(() => (results.value.length === 0 ? 0 : (page.value - 1) * PER_PAGE + 1))
const lastIndex = computed(() => Math.min(page.value * PER_PAGE, results.value.length))

/** Up to a few hundred pages, so: both ends, a window round the current page,
 *  and a gap for the rest. */
const pageItems = computed<(number | 'gap')[]>(() => {
  const total = pageCount.value
  const current = page.value
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)
  const shown = new Set([1, total, current - 1, current, current + 1])
  if (current <= 4) [2, 3, 4, 5].forEach((n) => shown.add(n))
  if (current >= total - 3) [total - 4, total - 3, total - 2, total - 1].forEach((n) => shown.add(n))
  const pages = [...shown].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b)
  const items: (number | 'gap')[] = []
  let previous = 0
  for (const value of pages) {
    if (value - previous > 1) items.push('gap')
    items.push(value)
    previous = value
  }
  return items
})

function pageLink(target: number) {
  const query = { ...route.query }
  delete query.animal
  if (target <= 1) delete query.page
  else query.page = String(target)
  return { query }
}

function goTo(target: number) {
  void router.push(pageLink(Math.min(Math.max(target, 1), pageCount.value)))
  scrollToResults()
}

function scrollToResults() {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  document.getElementById('results')?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth' })
}

/* ── Detail dialog ─────────────────────────────────────────────────────── */

const openAnimal = computed<Animal | null>(() => {
  const id = route.query.animal
  if (typeof id !== 'string') return null
  return animals.value.find((animal) => animal.id === id) ?? null
})

function open(animal: Animal) {
  void router.push({ query: { ...route.query, animal: animal.id } })
}

function close() {
  closeAnimalDialog(router, route)
}

const noPhotoShare = computed(() => {
  const total = animals.value.length
  if (total === 0) return '—'
  return ((animals.value.filter((animal) => !animal.photo).length / total) * 100).toFixed(1)
})

function onSelect(key: 'county' | 'shelter' | 'variety', event: Event) {
  const value = (event.target as HTMLSelectElement).value || undefined
  if (key === 'county') update({ county: value, shelter: undefined })
  else update({ [key]: value })
}

function onSort(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  update({ sort: value === 'shortest' ? 'shortest' : undefined })
}
</script>

<template>
  <div>
    <PageHead title="找動物">
      全臺{{ shelters.length ? ` ${shelters.length} 間` : '' }}公立收容所目前仍開放認養的{{
        animals.length ? ` ${formatCount(animals.length)} 隻` : ''
      }}動物，狗、貓與其他動物在同一個清單裡，用下面的條件收斂。
    </PageHead>

    <p v-if="loading" class="state">載入中…（全國動物資料約 272 KB）</p>
    <p v-else-if="error" class="state">資料載入失敗（{{ error }}）。</p>

    <template v-else>
      <!-- Region above the line, the animal itself below it (DESIGN.md §6). -->
      <div class="findbox">
        <div class="find-row upper">
          <div class="field">
            <label for="f-county">縣市</label>
            <div class="select">
              <select id="f-county" :value="filters.county ?? ''" @change="onSelect('county', $event)">
                <option value="">全部（{{ formatCount(countyTotal) }} 隻）</option>
                <option v-for="option in countyOptions" :key="option.name" :value="option.name">
                  {{ option.name }}（{{ formatCount(option.count) }}）
                </option>
              </select>
              <LucideIcon name="chevron-down" :size="16" />
            </div>
          </div>
          <div class="field">
            <label for="f-shelter">收容所</label>
            <div class="select">
              <select id="f-shelter" :value="filters.shelter ?? ''" @change="onSelect('shelter', $event)">
                <option value="">全部（{{ shelterOptions.length }} 間）</option>
                <option v-for="option in shelterOptions" :key="option.id" :value="option.id">
                  {{ option.name }}（{{ formatCount(option.count) }}）
                </option>
              </select>
              <LucideIcon name="chevron-down" :size="16" />
            </div>
          </div>
        </div>

        <div class="find-row lower">
          <div class="field" role="group" aria-labelledby="l-kind">
            <span id="l-kind" class="label">動物類型</span>
            <div class="pills">
              <button
                type="button"
                class="pill-btn"
                :aria-pressed="!filters.kind"
                @click="update({ kind: undefined, variety: undefined })"
              >
                全部 {{ formatCount(kindTotal) }}
              </button>
              <button
                v-for="kind in KINDS"
                :key="kind"
                type="button"
                class="pill-btn"
                :aria-pressed="filters.kind === kind"
                @click="update({ kind, variety: undefined })"
              >
                {{ kind }} {{ formatCount(kindCounts.get(kind) ?? 0) }}
              </button>
            </div>
          </div>

          <div class="field">
            <label for="f-variety">品種</label>
            <div class="select">
              <select id="f-variety" :value="filters.variety ?? ''" @change="onSelect('variety', $event)">
                <option value="">全部（{{ varietyOptions.length }} 種）</option>
                <option v-for="[name, count] in varietyOptions" :key="name" :value="name">
                  {{ name }}（{{ formatCount(count) }}）
                </option>
              </select>
              <LucideIcon name="chevron-down" :size="16" />
            </div>
          </div>

          <div class="field" role="group" aria-labelledby="l-sex">
            <span id="l-sex" class="label">性別</span>
            <div class="pills">
              <button type="button" class="pill-btn" :aria-pressed="!filters.sex" @click="update({ sex: undefined })">
                不限
              </button>
              <button
                v-for="(label, code) in SEX_LABEL"
                :key="code"
                type="button"
                class="pill-btn"
                :aria-pressed="filters.sex === code"
                @click="update({ sex: code })"
              >
                {{ label }} {{ formatCount(sexCounts.get(code) ?? 0) }}
              </button>
            </div>
          </div>

          <div class="field" role="group" aria-labelledby="l-body">
            <span id="l-body" class="label">體型</span>
            <div class="pills">
              <button
                type="button"
                class="pill-btn"
                :aria-pressed="!filters.body"
                @click="update({ body: undefined })"
              >
                不限
              </button>
              <button
                v-for="(label, code) in BODY_LABEL"
                :key="code"
                type="button"
                class="pill-btn"
                :aria-pressed="filters.body === code"
                @click="update({ body: code })"
              >
                {{ label }} {{ formatCount(bodyCounts.get(code) ?? 0) }}
              </button>
            </div>
          </div>

          <div class="field" role="group" aria-labelledby="l-days">
            <span id="l-days" class="label">已在所</span>
            <div class="pills">
              <button
                type="button"
                class="pill-btn"
                :aria-pressed="!filters.days && !filters.daysFrom"
                @click="update({ days: undefined, daysFrom: undefined })"
              >
                不限
              </button>
              <button
                v-for="(band, index) in DAY_BANDS"
                :key="band.key"
                type="button"
                class="pill-btn"
                :aria-pressed="bandOn(band.key)"
                @click="update({ days: band.key, daysFrom: undefined })"
              >
                {{ band.label }} {{ formatCount(bandCounts[index]) }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div id="results" class="resultbar">
        <span class="count" aria-live="polite">符合條件 <b>{{ formatCount(results.length) }}</b> 隻</span>
        <span class="sortwrap">
          <LucideIcon name="arrow-up-down" :size="15" />
          <label for="f-sort">排序</label>
          <span class="select sort">
            <select id="f-sort" :value="filters.sort ?? 'longest'" @change="onSort">
              <option v-for="option in SORTS" :key="option.id" :value="option.id">
                {{ option.label }}
              </option>
            </select>
            <LucideIcon name="chevron-down" :size="16" />
          </span>
        </span>
      </div>

      <div v-if="applied.length" class="applied">
        <span v-for="tag in applied" :key="tag.label" class="tag">
          {{ tag.label }}
          <button type="button" :aria-label="`移除條件：${tag.label}`" @click="update(tag.clear)">
            <LucideIcon name="x" :size="14" />
          </button>
        </span>
        <button type="button" class="clear" @click="clearAll">清除全部</button>
      </div>

      <p v-if="results.length === 0" class="state">沒有符合條件的動物。</p>

      <template v-else>
        <div class="grid">
          <AnimalCard
            v-for="animal in visible"
            :key="animal.id"
            :animal="animal"
            :days="daysOf(animal)"
            :percentile="percentileOf(animal)"
            :longest="animal.id === longestId"
            :place="placeOf(animal)"
            @open="open"
          />
        </div>

        <nav v-if="pageCount > 1" class="pagination" aria-label="分頁">
          <button type="button" class="page-nav" :disabled="page <= 1" @click="goTo(page - 1)">
            <LucideIcon name="chevron-left" :size="16" /> 上一頁
          </button>
          <template v-for="(item, index) in pageItems" :key="`${item}-${index}`">
            <span v-if="item === 'gap'" class="page-gap" aria-hidden="true">…</span>
            <RouterLink
              v-else
              :to="pageLink(item)"
              class="page-num"
              :aria-current="item === page ? 'page' : undefined"
              @click="scrollToResults"
            >
              {{ item }}
            </RouterLink>
          </template>
          <button type="button" class="page-nav" :disabled="page >= pageCount" @click="goTo(page + 1)">
            下一頁 <LucideIcon name="chevron-right" :size="16" />
          </button>
        </nav>
        <p class="page-meta">
          顯示第 {{ formatCount(firstIndex) }}–{{ formatCount(lastIndex) }} 隻，共
          {{ formatCount(results.length) }} 隻 · 每頁 {{ PER_PAGE }} 隻
        </p>
      </template>

      <!-- Kept from the previous page on purpose (DESIGN.md §12.3): the draft
           has no boundary card here, but every page carries one. -->
      <section class="boundary">
        <div class="boundary-head">
          <span class="pill">這些卡片不能拿來說什麼</span>
          <span class="kicker">DATA BOUNDARY</span>
        </div>
        <div class="boundary-cols">
          <div>
            <h3>刊登照片不代表動物現況</h3>
            <p>
              照片多為入所建檔時拍攝，全國有 {{ noPhotoShare }}% 的資料沒有照片。實際的健康與個性必須以現場互動評估為準。
            </p>
          </div>
          <div>
            <h3>「已在所天數」不是難認養程度</h3>
            <p>
              這份資料只包含尚未離所的動物，待得越久的越可能出現在其中。天數極長者常是長期醫療照護的個體，不能反推牠比較不受歡迎。
            </p>
          </div>
          <div>
            <h3>本站不辦理認養</h3>
            <p>
              這裡只呈現農業部開放資料的每日快照，不做媒合也不代辦手續。有意認養請先致電該收容所確認動物仍在所，依其規定辦理。
            </p>
          </div>
        </div>
      </section>
    </template>

    <AnimalDialog
      v-if="openAnimal"
      :animal="openAnimal"
      :snapshot-date="snapshotDate"
      :shelter="shelterById.get(openAnimal.shelter)"
      @close="close"
    />
  </div>
</template>

<style scoped>
.state {
  padding: 3rem 0;
  color: var(--ink-muted);
}

/* ── Filter panel ── */
.findbox {
  margin-top: 1.75rem;
  padding: 1.25rem 1.5rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
}

.find-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
}

.find-row.upper {
  padding-bottom: 1.1rem;
  border-bottom: 1px solid var(--hairline);
}

.find-row.lower {
  padding-top: 1.1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}

.field > label,
.field > .label {
  color: var(--ink-muted);
  font-size: 0.8rem;
}

/* A native select dressed as the draft's field: the list stays the platform's
   own, which keeps it usable by keyboard and on phones. */
.select {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 13rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--plane);
  color: var(--ink);
}

.select:hover {
  border-color: var(--ramp-3);
}

.select:focus-within {
  outline: 2px solid var(--ramp-4);
  outline-offset: 1px;
}

.select select {
  width: 100%;
  padding: 0.5rem 2.4rem 0.5rem 0.8rem;
  border: 0;
  outline: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 0.92rem;
  font-variant-numeric: tabular-nums;
  appearance: none;
  cursor: pointer;
}

.select svg {
  position: absolute;
  right: 0.8rem;
  color: var(--ink-muted);
  pointer-events: none;
}

.pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.pill-btn {
  padding: 0.35rem 0.9rem;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: transparent;
  color: var(--ink-secondary);
  font: inherit;
  font-size: 0.88rem;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  transition:
    background 160ms ease,
    color 160ms ease,
    border-color 160ms ease;
}

.pill-btn:hover {
  border-color: var(--ramp-3);
  color: var(--ink);
}

.pill-btn[aria-pressed='true'] {
  border-color: var(--ramp-4);
  background: var(--ramp-4);
  color: var(--on-accent);
}

/* ── Result bar ── */
.resultbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1.75rem;
  scroll-margin-top: 80px;
}

.resultbar .count {
  color: var(--ink-secondary);
  font-size: 0.95rem;
  font-variant-numeric: tabular-nums;
}

.resultbar .count b {
  color: var(--accent-text);
}

.sortwrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--ink-muted);
  font-size: 0.88rem;
}

.select.sort {
  min-width: 12rem;
}

/* ── Applied filters ── */
.applied {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.9rem;
}

.applied .tag {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.22rem 0.5rem 0.22rem 0.75rem;
  border-radius: 999px;
  background: var(--surface-sunk);
  color: var(--ink-secondary);
  font-size: 0.84rem;
  font-variant-numeric: tabular-nums;
}

.applied .tag button {
  display: flex;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-muted);
  cursor: pointer;
}

.applied .tag button:hover {
  color: var(--ink);
}

.applied .clear {
  margin-left: 0.25rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--accent-text);
  font: inherit;
  font-size: 0.84rem;
  cursor: pointer;
}

/* ── Grid and pager ── */
.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 2rem 1.5rem;
  margin-top: 1.5rem;
}

.pagination {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  margin-top: 2.5rem;
}

.page-num,
.page-nav {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  min-width: 40px;
  height: 40px;
  padding: 0 0.75rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink);
  font: inherit;
  font-size: 0.92rem;
  font-variant-numeric: tabular-nums;
  text-decoration: none;
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    color 160ms ease;
}

.page-num:hover,
.page-nav:hover {
  border-color: var(--ramp-3);
  background: var(--surface);
}

.page-num[aria-current='page'] {
  border-color: var(--ramp-4);
  background: var(--ramp-4);
  color: var(--on-accent);
  font-weight: 500;
}

.page-nav:disabled {
  opacity: 0.35;
  pointer-events: none;
}

.page-gap {
  padding: 0 0.25rem;
  color: var(--ink-muted);
}

.page-meta {
  margin: 0.9rem 0 0;
  color: var(--ink-muted);
  font-size: 0.85rem;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

/* ── Boundary card ── */
.boundary {
  margin-top: 3rem;
  padding: 1.6rem;
  border-radius: var(--radius);
  background: var(--surface-sunk);
}

.boundary-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.1rem;
}

.pill {
  padding: 0.12rem 0.75rem;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: var(--surface);
  font-size: 0.84rem;
}

.kicker {
  color: var(--ink-muted);
  font-size: 0.72rem;
  letter-spacing: 0.14em;
}

.boundary-cols {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
}

.boundary-cols h3 {
  margin-bottom: 0.35rem;
  font-size: 0.98rem;
}

.boundary-cols p {
  margin: 0;
  color: var(--ink-secondary);
  font-size: 0.86rem;
}

@media (max-width: 1000px) {
  .boundary-cols {
    grid-template-columns: 1fr;
    gap: 1.25rem;
  }
}

@media (max-width: 820px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .field {
    width: 100%;
  }

  .select {
    width: 100%;
    min-width: 0;
  }

  .sortwrap {
    width: 100%;
  }

  .select.sort {
    flex: 1;
    min-width: 0;
  }
}

@media (max-width: 480px) {
  .page-num,
  .page-nav {
    min-width: 36px;
    height: 36px;
    padding: 0 0.5rem;
    font-size: 0.88rem;
  }
}
</style>
