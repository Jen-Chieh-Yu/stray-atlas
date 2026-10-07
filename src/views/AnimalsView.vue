<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AnimalCard from '@/components/AnimalCard.vue'
import AnimalDialog from '@/components/AnimalDialog.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import MissingAnimalDialog from '@/components/MissingAnimalDialog.vue'
import PageHead from '@/components/PageHead.vue'
import { fetchHome } from '@/composables/useAtlasData'
import { useRoster } from '@/composables/useRoster'
import { closeAnimalDialog } from '@/lib/dialogRoute'
import { vReveal } from '@/lib/reveal'
import {
  BODY_LABEL,
  DAY_BANDS,
  SEX_LABEL,
  SORTS,
  AGE_LABEL,
  OFFICIAL_ADOPTION_URL,
  formatCount,
  inBand,
  isIdQuery,
  isNewerId,
  matchesId,
  parseAnimalQuery,
  rosterHint,
  searchLink,
  tally,
  KIND_PARAM,
  LOST_PET_LINKS,
} from '@/lib/animals'
import type { AnimalQuery, DayBandKey } from '@/lib/animals'
import type { Animal, Kind } from '@/types'

const route = useRoute()
const router = useRouter()

const { animals, shelters, snapshotDate, loading, error, shelterById, placeOf, countyOf, daysOf } =
  useRoster()

/** What the loading line says this page is waiting for. home.json is a few
 *  kilobytes and usually lands well before the roster; until it does, or if
 *  it fails, the line names the data without figures. */
const loadingHint = ref(rosterHint())
fetchHome()
  .then((home) => {
    loadingHint.value = rosterHint(home.roster)
  })
  .catch(() => undefined)

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
  for (const key of [
    'county',
    'shelter',
    'variety',
    'sex',
    'body',
    'age',
    'days',
    'daysFrom',
    'q',
  ] as const) {
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

/** A number is matched whole against 收容編號 and 流水號 (lib/animals.ts).
 *  Anything else: every word must hit the county, the shelter or the variety
 *  — the three things the search boxes promise. */
function matchesText(animal: Animal, text: string | undefined): boolean {
  if (!text) return true
  if (isIdQuery(text)) return matchesId(animal, text)
  const haystack = `${countyOf(animal)} ${placeOf(animal)} ${animal.variety}`
  return text.split(/\s+/).every((word) => haystack.includes(word))
}

const idSearch = computed(() => {
  const q = filters.value.q
  return q && isIdQuery(q) ? q : null
})

/** Hits for the number alone, before any other filter: zero means the number
 *  is not in the roster at all, which gets its own explanation below. */
const idHits = computed(() => {
  const q = idSearch.value
  return q ? animals.value.filter((animal) => matchesId(animal, q)) : []
})

/* ── Search box ────────────────────────────────────────────────────────────
 * Applied on Enter, not per keystroke: recounting every facet on each letter
 * would make the numbers beside the chips flicker. */

const searchText = ref('')

watch(
  () => filters.value.q,
  (q) => (searchText.value = q ?? ''),
  { immediate: true },
)

function submitSearch() {
  void router.replace(
    searchLink(searchText.value, { ...filters.value, q: undefined }, animals.value),
  )
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
  return DAY_BANDS.map(
    (band) => list.filter((animal) => inBand(daysOf(animal), band.min, band.max)).length,
  )
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
  if (query.q) {
    tags.push({
      label: `${isIdQuery(query.q) ? '編號' : '搜尋'}「${query.q}」`,
      clear: { q: undefined },
    })
  }
  if (query.county)
    tags.push({ label: query.county, clear: { county: undefined, shelter: undefined } })
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
    tags.push({
      label: `已在所 ${formatCount(Math.ceil((band.min - 1) / 365))} 年以上`,
      clear: { daysFrom: undefined },
    })
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

const firstIndex = computed(() =>
  results.value.length === 0 ? 0 : (page.value - 1) * PER_PAGE + 1,
)
const lastIndex = computed(() => Math.min(page.value * PER_PAGE, results.value.length))

/** Up to a few hundred pages, so: both ends, a window round the current page,
 *  and a gap for the rest. */
const pageItems = computed<(number | 'gap')[]>(() => {
  const total = pageCount.value
  const current = page.value
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)
  const shown = new Set([1, total, current - 1, current, current + 1])
  if (current <= 4) [2, 3, 4, 5].forEach((n) => shown.add(n))
  if (current >= total - 3)
    [total - 4, total - 3, total - 2, total - 1].forEach((n) => shown.add(n))
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

/* ── 在找走失的寵物 ─────────────────────────────────────────────────────────
 * The note at the foot of the page, reached from the line under the title,
 * from a number that found nothing, and from the 不在目前名單 dialog on any
 * page (/animals#lost). The router leaves #lost to this page (router/index.ts)
 * because the note sits below the roster, which may still be loading. */

function scrollToLost() {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  document.getElementById('lost')?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth' })
}

watch(
  () => [route.hash, loading.value] as const,
  async ([hash, waiting]) => {
    if (hash !== '#lost' || waiting) return
    await nextTick()
    scrollToLost()
  },
  { immediate: true, flush: 'post' },
)

/* ── Detail dialog ─────────────────────────────────────────────────────── */

const openAnimal = computed<Animal | null>(() => {
  const id = route.query.animal
  if (typeof id !== 'string') return null
  return animals.value.find((animal) => animal.id === id) ?? null
})

/** A link to an animal no longer in the roster, once the roster is here. */
const missingId = computed(() => {
  const id = route.query.animal
  if (typeof id !== 'string' || animals.value.length === 0 || openAnimal.value) return null
  return id
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

    <!-- For someone looking for their own pet: this list leaves out the
         animals they are most likely to find (DESIGN.md §6). -->
    <p class="lost-hint">
      <LucideIcon name="circle-help" :size="16" />
      <span
        ><b>在找走失的寵物？</b
        >剛進收容所的動物要先公告招領，通常還不在這份名單上，在這裡找不到不代表牠不在收容所。<a
          href="#lost"
          @click.prevent="scrollToLost"
          >怎麼找 ↓</a
        ></span
      >
    </p>

    <LoadingSkeleton v-if="loading" variant="cards" :count="4" :hint="loadingHint" />
    <p v-else-if="error" class="state">資料載入失敗（{{ error }}）。</p>

    <template v-else>
      <!-- Region above the line, the animal itself below it (DESIGN.md §6). -->
      <div v-reveal class="findbox">
        <div class="find-row upper">
          <!-- Searches place and breed, and finds one animal by its number;
               it sits with the region controls because it spans both rows. -->
          <form class="field" role="search" @submit.prevent="submitSearch">
            <label for="f-search">搜尋</label>
            <div class="textbox">
              <LucideIcon name="search" :size="16" />
              <input
                id="f-search"
                v-model="searchText"
                type="search"
                placeholder="縣市、收容所、品種或收容編號"
                enterkeyhint="search"
                autocomplete="off"
              />
            </div>
          </form>
          <div class="field">
            <label for="f-county">縣市</label>
            <div class="select">
              <select
                id="f-county"
                :value="filters.county ?? ''"
                @change="onSelect('county', $event)"
              >
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
              <select
                id="f-shelter"
                :value="filters.shelter ?? ''"
                @change="onSelect('shelter', $event)"
              >
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
              <select
                id="f-variety"
                :value="filters.variety ?? ''"
                @change="onSelect('variety', $event)"
              >
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
              <button
                type="button"
                class="pill-btn"
                :aria-pressed="!filters.sex"
                @click="update({ sex: undefined })"
              >
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
        <span class="count" aria-live="polite"
          >符合條件 <b>{{ formatCount(results.length) }}</b> 隻</span
        >
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

      <p v-if="idSearch && idHits.length > 1" class="idnote">
        這個編號在資料裡對到
        {{ idHits.length }} 隻動物。同一個編號登錄給不同動物，是收容所登錄資料的問題。
      </p>

      <div v-if="idSearch && idHits.length === 0" class="idmiss">
        <span class="icon"><LucideIcon name="search-x" :size="18" /></span>
        <div>
          <p>
            <b>目前開放認養的名單裡沒有編號「{{ idSearch }}」。</b>
          </p>
          <p class="more">
            請確認編號是否正確。若編號無誤，牠可能已被認養、轉到其他收容所或暫停開放認養；本站無法分辨是哪一種。想確認請致電收容所，或到
            <a :href="OFFICIAL_ADOPTION_URL" target="_blank" rel="noreferrer"
              >農業部動物認領養公告頁（pet.gov.tw）</a
            >
            查詢。
          </p>
          <p class="more">
            在找走失的寵物？剛進收容所的動物通常還不在名單上，<a
              href="#lost"
              @click.prevent="scrollToLost"
              >看怎麼找 ↓</a
            >
          </p>
        </div>
      </div>
      <p v-else-if="results.length === 0" class="state">沒有符合條件的動物。</p>

      <template v-else>
        <div class="grid">
          <AnimalCard
            v-for="animal in visible"
            :key="animal.id"
            v-reveal
            :animal="animal"
            :days="daysOf(animal)"
            :place="placeOf(animal)"
            :snapshot-date="snapshotDate"
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
          <button
            type="button"
            class="page-nav"
            :disabled="page >= pageCount"
            @click="goTo(page + 1)"
          >
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
      <section v-reveal class="boundary">
        <div class="boundary-head">
          <span class="pill">這些卡片不能拿來說什麼</span>
          <span class="kicker">DATA BOUNDARY</span>
        </div>
        <div class="boundary-cols">
          <div>
            <h3>刊登照片不代表動物現況</h3>
            <p>
              照片多為入所建檔時拍攝，全國有 {{ noPhotoShare }}%
              的資料沒有照片。實際的健康與個性必須以現場互動評估為準。
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
              這裡只呈現農業部開放資料的快照，不做媒合也不代辦手續。有意認養請先致電該收容所確認動物仍在所，依其規定辦理。
            </p>
          </div>
        </div>
      </section>
    </template>

    <!-- Outside the loading switch, so 怎麼找 works while the roster loads. -->
    <section id="lost" class="lost" aria-labelledby="lost-title">
      <div class="lost-head">
        <h2 id="lost-title">在找走失的寵物</h2>
        <span class="kicker">LOST PETS</span>
      </div>
      <p>
        本站只列<b>目前開放認養</b>的動物。剛被帶進收容所的動物會先公告招領、等飼主來認，這段期間通常不在這份名單上；收容所標為暫時不適合認養的動物也不在。所以<b>在這裡找不到，不代表牠不在收容所</b>，請照下面的方式找：
      </p>
      <ol class="lost-steps">
        <li>
          <b>每天看全國收容公告</b>
          新入所的動物會先刊在全國動物收容管理系統的<a
            :href="LOST_PET_LINKS.announcements"
            target="_blank"
            rel="noreferrer"
            >收容公告</a
          >，可依收容所縣市與收容所篩選。
        </li>
        <li>
          <b>直接打電話問收容所</b>
          從走失地點附近的收容所問起，電話在<RouterLink to="/shelters">收容所列表</RouterLink
          >。拾獲的動物不一定送到同縣市的收容所。
        </li>
        <li>
          <b>申報寵物遺失</b>
          做過寵物登記、植入晶片的，可以到寵物登記管理資訊網<a
            :href="LOST_PET_LINKS.report"
            target="_blank"
            rel="noreferrer"
            >申報遺失</a
          >（需要飼主證號與晶片號碼），申報後會刊登並全國協尋。
        </li>
        <li>
          <b>看縣市自己的公告頁</b>
          部分縣市另有招領公告，例如<template
            v-for="(item, index) in LOST_PET_LINKS.counties"
            :key="item.county"
            >{{ index ? '、' : ''
            }}<a :href="item.url" target="_blank" rel="noreferrer">{{ item.county }}</a></template
          >。
        </li>
      </ol>
      <p class="fine">
        本站資料取自農業部開放資料，每天更新一次，不是即時資料；最新狀況以收容所與上述官方網站為準。
      </p>
    </section>

    <AnimalDialog
      v-if="openAnimal"
      :animal="openAnimal"
      :snapshot-date="snapshotDate"
      :shelter="shelterById.get(openAnimal.shelter)"
      :roster="animals"
      @close="close"
      @open="open"
    />
    <MissingAnimalDialog
      v-else-if="missingId"
      :id="missingId"
      :newer="isNewerId(missingId, animals)"
      @close="close"
      @browse="close"
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

  &.upper {
    padding-bottom: 1.1rem;
    border-bottom: 1px solid var(--hairline);
  }

  &.lower {
    padding-top: 1.1rem;
  }
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;

  & > label,
  & > .label {
    color: var(--ink-muted);
    font-size: 0.8rem;
  }
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

  &:hover {
    border-color: var(--ramp-3);
  }

  &:focus-within {
    outline: 2px solid var(--ramp-4);
    outline-offset: 1px;
  }

  & select {
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

  & svg {
    position: absolute;
    right: 0.8rem;
    color: var(--ink-muted);
    pointer-events: none;
  }
}

/* The search field, dressed like the selects beside it. */
.textbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 19rem;
  padding: 0 0.8rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--plane);
  color: var(--ink-muted);

  &:hover {
    border-color: var(--ramp-3);
  }

  &:focus-within {
    outline: 2px solid var(--ramp-4);
    outline-offset: 1px;
  }

  & input {
    flex: 1;
    min-width: 0;
    padding: 0.5rem 0;
    border: 0;
    outline: 0;
    background: transparent;
    color: var(--ink);
    font: inherit;
    font-size: 0.92rem;
    font-variant-numeric: tabular-nums;

    &::placeholder {
      color: var(--ink-muted);
    }
  }
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

  &:hover {
    border-color: var(--ramp-3);
    color: var(--ink);
  }

  &[aria-pressed='true'] {
    border-color: var(--ramp-4);
    background: var(--ramp-4);
    color: var(--on-accent);
  }
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

  & .count {
    color: var(--ink-secondary);
    font-size: 0.95rem;
    font-variant-numeric: tabular-nums;

    & b {
      color: var(--accent-text);
    }
  }
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

  & .tag {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.22rem 0.5rem 0.22rem 0.75rem;
    border-radius: 999px;
    background: var(--surface-sunk);
    color: var(--ink-secondary);
    font-size: 0.84rem;
    font-variant-numeric: tabular-nums;

    & button {
      display: flex;
      padding: 0;
      border: 0;
      background: transparent;
      color: var(--ink-muted);
      cursor: pointer;

      &:hover {
        color: var(--ink);
      }
    }
  }

  & .clear {
    margin-left: 0.25rem;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--accent-text);
    font: inherit;
    font-size: 0.84rem;
    cursor: pointer;
  }
}

/* ── Search by number ── */
.idnote {
  margin: 0.9rem 0 0;
  padding: 0.7rem 0.95rem;
  border-radius: var(--radius-sm);
  background: var(--surface-sunk);
  color: var(--ink-secondary);
  font-size: 0.88rem;
}

.idmiss {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  margin-top: 1.2rem;
  padding: 1.1rem 1.25rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);

  & .icon {
    display: grid;
    place-items: center;
    flex-shrink: 0;
    width: 2rem;
    height: 2rem;
    border-radius: var(--radius-sm);
    background: var(--surface-sunk);
    color: var(--ink-secondary);
  }

  & p {
    margin: 0;
    color: var(--ink-secondary);
    font-size: 0.92rem;
  }

  & .more {
    margin-top: 0.35rem;
    font-size: 0.86rem;
  }

  & b {
    color: var(--ink);
  }

  & a {
    color: var(--accent-text);
  }
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

/* ── 在找走失的寵物 ── */
.lost-hint {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  margin: 1rem 0 0;
  padding: 0.65rem 0.9rem;
  border: 1px solid var(--hairline);
  border-left: 4px solid var(--ramp-3);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--ink-secondary);
  font-size: 0.88rem;
  line-height: 1.65;

  & svg {
    flex-shrink: 0;
    margin-top: 0.2rem;
    color: var(--ramp-4);
  }

  & b {
    color: var(--ink);
  }

  & a {
    color: var(--accent-text);
    white-space: nowrap;
  }
}

.lost {
  margin-top: 1.5rem;
  padding: 1.4rem 1.6rem 1.5rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
  scroll-margin-top: 5rem;

  & > p {
    margin: 0 0 1rem;
    color: var(--ink-secondary);
    font-size: 0.9rem;
    line-height: 1.75;
  }

  & b {
    color: var(--ink);
  }

  & a {
    color: var(--accent-text);
  }

  & .fine {
    margin: 1rem 0 0;
    color: var(--ink-muted);
    font-size: 0.78rem;
  }
}

.lost-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.6rem;
  margin-bottom: 0.5rem;

  & h2 {
    margin: 0;
    font-size: 1.15rem;
  }
}

.lost-steps {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem 1.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
  counter-reset: step;

  & li {
    position: relative;
    padding-left: 2.1rem;
    color: var(--ink-secondary);
    font-size: 0.86rem;
    line-height: 1.65;
    counter-increment: step;
  }

  & li::before {
    content: counter(step);
    position: absolute;
    top: 0.1rem;
    left: 0;
    display: grid;
    place-items: center;
    width: 1.4rem;
    height: 1.4rem;
    border-radius: 999px;
    background: var(--ramp-4);
    color: var(--on-accent);
    font-size: 0.75rem;
    font-weight: 700;
  }

  & b {
    display: block;
    font-size: 0.92rem;
  }
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

  & h3 {
    margin-bottom: 0.35rem;
    font-size: 0.98rem;
  }

  & p {
    margin: 0;
    color: var(--ink-secondary);
    font-size: 0.86rem;
  }
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

  .lost-steps {
    grid-template-columns: 1fr;
  }

  .field {
    width: 100%;
  }

  .select,
  .textbox {
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
