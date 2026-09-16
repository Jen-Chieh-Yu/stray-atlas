<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import LucideIcon from '@/components/LucideIcon.vue'
import PageHead from '@/components/PageHead.vue'
import ShelterSpark from '@/components/ShelterSpark.vue'
import { useRoster } from '@/composables/useRoster'
import { animalsLink, formatCount } from '@/lib/animals'
import {
  addressesOf,
  duplicateSpellings,
  hasMachineField,
  northToSouth,
  phoneOf,
} from '@/lib/shelters'
import type { Shelter } from '@/types'

const route = useRoute()
const router = useRouter()

const { shelters, buckets, loading, error } = useRoster()

const labels = computed(() => buckets.value.map((bucket) => bucket.label))

/* ── Filters live in the URL, as on the animals page ────────────────────── */

type Has = 'dog' | 'cat'
type Size = 'big' | 'mid' | 'small'
type Sort = 'all-desc' | 'all-asc' | 'median-desc' | 'max-desc' | 'dog-desc' | 'cat-desc' | 'north'

const SIZES: { id: Size; label: string; test: (count: number) => boolean }[] = [
  { id: 'big', label: '300 隻以上', test: (count) => count >= 300 },
  { id: 'mid', label: '100–299 隻', test: (count) => count >= 100 && count < 300 },
  { id: 'small', label: '100 隻以下', test: (count) => count < 100 },
]

const SORTS: { id: Sort; label: string }[] = [
  { id: 'all-desc', label: '在所動物數（多到少）' },
  { id: 'all-asc', label: '在所動物數（少到多）' },
  { id: 'median-desc', label: '滯留中位數（長到短）' },
  { id: 'max-desc', label: '等最久的一隻（長到短）' },
  { id: 'dog-desc', label: '狗的數量（多到少）' },
  { id: 'cat-desc', label: '貓的數量（多到少）' },
  { id: 'north', label: '縣市（由北到南）' },
]

function one(value: unknown): string | undefined {
  const first = Array.isArray(value) ? value[0] : value
  return typeof first === 'string' && first !== '' ? first : undefined
}

const filters = computed(() => {
  const has = one(route.query.has)
  const size = one(route.query.size)
  const sort = one(route.query.sort)
  return {
    // Card grid or full-width rows. Kept in the URL so the choice survives
    // a trip to a shelter page and back.
    view: one(route.query.view) === 'list' ? ('list' as const) : ('grid' as const),
    county: one(route.query.county),
    q: one(route.query.q)?.trim() || undefined,
    has: has === 'dog' || has === 'cat' ? (has as Has) : undefined,
    size: SIZES.some((item) => item.id === size) ? (size as Size) : undefined,
    sort: SORTS.some((item) => item.id === sort) ? (sort as Sort) : ('all-desc' as Sort),
  }
})

type Filters = typeof filters.value

function update(patch: Partial<Filters>) {
  const next = { ...filters.value, ...patch }
  const query: Record<string, string> = {}
  if (next.county) query.county = next.county
  if (next.q) query.q = next.q
  if (next.has) query.has = next.has
  if (next.size) query.size = next.size
  if (next.sort !== 'all-desc') query.sort = next.sort
  if (next.view === 'list') query.view = 'list'
  void router.replace({ query })
}

function matches(shelter: Shelter, skip: keyof Filters | null): boolean {
  const query = filters.value
  if (skip !== 'county' && query.county && shelter.county !== query.county) return false
  if (skip !== 'q' && query.q && !shelter.name.includes(query.q)) return false
  if (skip !== 'has' && query.has === 'dog' && shelter.狗.count === 0) return false
  if (skip !== 'has' && query.has === 'cat' && shelter.貓.count === 0) return false
  if (skip !== 'size' && query.size) {
    const size = SIZES.find((item) => item.id === query.size)!
    if (!size.test(shelter.all.count)) return false
  }
  return true
}

function by(sort: Sort) {
  const days = (value: number | null) => value ?? -1
  return (a: Shelter, b: Shelter): number => {
    switch (sort) {
      case 'all-asc':
        return a.all.count - b.all.count
      case 'median-desc':
        return days(b.all.median_days) - days(a.all.median_days)
      case 'max-desc':
        return days(b.all.max_days) - days(a.all.max_days)
      case 'dog-desc':
        return b.狗.count - a.狗.count
      case 'cat-desc':
        return b.貓.count - a.貓.count
      case 'north':
        return northToSouth(a) - northToSouth(b) || b.all.count - a.all.count
      default:
        return b.all.count - a.all.count
    }
  }
}

const results = computed(() =>
  shelters.value.filter((shelter) => matches(shelter, null)).sort(by(filters.value.sort)),
)

const resultAnimals = computed(() =>
  results.value.reduce((total, shelter) => total + shelter.all.count, 0),
)

/* ── Options with counts ───────────────────────────────────────────────── */

const counties = computed(() => {
  const counts = new Map<string, number>()
  for (const shelter of shelters.value) {
    if (!matches(shelter, 'county')) continue
    counts.set(shelter.county, (counts.get(shelter.county) ?? 0) + 1)
  }
  const names = [...new Set([...shelters.value].sort(by('north')).map((shelter) => shelter.county))]
  return names.map((name) => ({ name, count: counts.get(name) ?? 0 }))
})

const hasCounts = computed(() => {
  const pool = shelters.value.filter((shelter) => matches(shelter, 'has'))
  return {
    dog: pool.filter((shelter) => shelter.狗.count > 0).length,
    cat: pool.filter((shelter) => shelter.貓.count > 0).length,
  }
})

const sizeCounts = computed(() => {
  const pool = shelters.value.filter((shelter) => matches(shelter, 'size'))
  return SIZES.map((size) => pool.filter((shelter) => size.test(shelter.all.count)).length)
})

const totals = computed(() => ({
  shelters: shelters.value.length,
  counties: new Set(shelters.value.map((shelter) => shelter.county)).size,
  animals: shelters.value.reduce((total, shelter) => total + shelter.all.count, 0),
}))

/* ── The notes at the bottom are counted, not typed ────────────────────── */

const notes = computed(() => {
  const list = shelters.value
  const incompletePhone = list.filter((shelter) => !phoneOf(shelter).href)
  const machine = list.filter(hasMachineField)
  const twoPlaces = list.filter((shelter) => addressesOf(shelter).length > 1)
  const respelled = list.filter((shelter) => duplicateSpellings(shelter) > 0)
  const byAddress = new Map<string, Shelter[]>()
  for (const shelter of list) {
    const key = addressesOf(shelter)[0]?.text ?? ''
    byAddress.set(key, [...(byAddress.get(key) ?? []), shelter])
  }
  const shared = [...byAddress.values()].filter((group) => group.length > 1)
  return { incompletePhone, machine, twoPlaces, respelled, shared }
})

function names(list: Shelter[]): string {
  return list.map((shelter) => shelter.name).join('、')
}
</script>

<template>
  <div>
    <PageHead title="收容所">
      全臺{{ totals.shelters ? ` ${totals.shelters} 間` : '' }}公立收容所{{
        totals.counties ? `，分布在 ${totals.counties} 個縣市` : ''
      }}。每張卡片先回答三件事：現在有多少動物、狗貓各佔多少、這裡的動物已經在所多久。決定要去哪一間之前，先在這裡看清楚。
    </PageHead>

    <p v-if="loading" class="state">載入中…</p>
    <p v-else-if="error" class="state">收容所資料載入失敗（{{ error }}）。</p>

    <template v-else>
      <div class="stats">
        <div class="stat"><b>{{ totals.shelters }}</b><span>間公立收容所</span></div>
        <div class="stat"><b>{{ totals.counties }}</b><span>個縣市有收容所</span></div>
        <div class="stat">
          <b>{{ formatCount(totals.animals) }}</b><span>隻動物目前仍在所</span>
        </div>
      </div>

      <div class="findbox">
        <div class="find-row upper">
          <div class="field">
            <label for="s-county">縣市</label>
            <div class="select">
              <select
                id="s-county"
                :value="filters.county ?? ''"
                @change="update({ county: ($event.target as HTMLSelectElement).value || undefined })"
              >
                <option value="">全部（{{ counties.length }} 個）</option>
                <option v-for="county in counties" :key="county.name" :value="county.name">
                  {{ county.name }}（{{ county.count }} 間）
                </option>
              </select>
              <LucideIcon name="chevron-down" :size="16" />
            </div>
          </div>
          <div class="field">
            <label for="s-q">收容所名稱</label>
            <div class="find-search">
              <LucideIcon name="search" :size="16" />
              <input
                id="s-q"
                type="search"
                placeholder="輸入關鍵字，例如「動物之家」"
                :value="filters.q ?? ''"
                @input="update({ q: ($event.target as HTMLInputElement).value.trim() || undefined })"
              />
            </div>
          </div>
        </div>

        <div class="find-row lower">
          <div class="field" role="group" aria-labelledby="l-has">
            <span id="l-has" class="label">目前收容</span>
            <div class="pills">
              <button type="button" class="pill-btn" :aria-pressed="!filters.has" @click="update({ has: undefined })">
                不限
              </button>
              <button
                type="button"
                class="pill-btn"
                :aria-pressed="filters.has === 'dog'"
                @click="update({ has: 'dog' })"
              >
                有狗可認養 {{ hasCounts.dog }}
              </button>
              <button
                type="button"
                class="pill-btn"
                :aria-pressed="filters.has === 'cat'"
                @click="update({ has: 'cat' })"
              >
                有貓可認養 {{ hasCounts.cat }}
              </button>
            </div>
          </div>
          <div class="field" role="group" aria-labelledby="l-size">
            <span id="l-size" class="label">規模</span>
            <div class="pills">
              <button
                type="button"
                class="pill-btn"
                :aria-pressed="!filters.size"
                @click="update({ size: undefined })"
              >
                不限
              </button>
              <button
                v-for="(size, index) in SIZES"
                :key="size.id"
                type="button"
                class="pill-btn"
                :aria-pressed="filters.size === size.id"
                @click="update({ size: size.id })"
              >
                {{ size.label }} {{ sizeCounts[index] }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="resultbar">
        <span class="count" aria-live="polite">
          共 <b>{{ results.length }}</b> 間收容所<span v-if="results.length" class="sum"
            >，合計 {{ formatCount(resultAnimals) }} 隻動物</span
          >
        </span>
        <span class="tools">
          <span class="viewtoggle" role="group" aria-label="顯示方式">
            <button
              type="button"
              :aria-pressed="filters.view === 'grid'"
              aria-label="以卡片顯示"
              title="以卡片顯示"
              @click="update({ view: 'grid' })"
            >
              <LucideIcon name="layout-grid" :size="18" />
            </button>
            <button
              type="button"
              :aria-pressed="filters.view === 'list'"
              aria-label="以條列顯示"
              title="以條列顯示"
              @click="update({ view: 'list' })"
            >
              <LucideIcon name="list" :size="18" />
            </button>
          </span>
          <span class="sortwrap">
            <LucideIcon name="arrow-up-down" :size="15" />
            <label for="s-sort">排序</label>
            <span class="select sort">
              <select
                id="s-sort"
                :value="filters.sort"
                @change="update({ sort: ($event.target as HTMLSelectElement).value as Sort })"
              >
                <option v-for="option in SORTS" :key="option.id" :value="option.id">
                  {{ option.label }}
                </option>
              </select>
              <LucideIcon name="chevron-down" :size="16" />
            </span>
          </span>
        </span>
      </div>

      <!-- Thirty-seven fit on one page; no pager. -->
      <!-- Rows: the same facts as a card, laid out left to right so a long
           list can be scanned and compared column by column. -->
      <ul v-if="results.length && filters.view === 'list'" class="rows">
        <li v-for="shelter in results" :key="shelter.id" class="srow">
          <div class="r-main">
            <div class="scard-top">
              <span class="county">{{ shelter.county }}</span>
            </div>
            <h2>
              <RouterLink :to="{ name: 'shelter', params: { id: shelter.id } }">{{ shelter.name }}</RouterLink>
            </h2>
            <div class="smeta">
              <span v-for="address in addressesOf(shelter)" :key="address.text">
                <LucideIcon name="map-pin" :size="14" />
                <span class="line" :title="`原始資料：${address.raw}`">{{ address.text }}</span>
              </span>
              <span>
                <LucideIcon name="phone" :size="14" />
                <span v-if="phoneOf(shelter).href" class="line">{{ shelter.tel }}</span>
                <span v-else class="line missing">電話欄位不完整（原始資料：{{ shelter.tel }}）</span>
              </span>
            </div>
          </div>
          <div class="r-counts">
            <div class="scount total"><b>{{ formatCount(shelter.all.count) }}</b><span>在所</span></div>
            <div class="scount"><b>{{ formatCount(shelter.狗.count) }}</b><span>狗</span></div>
            <div class="scount"><b>{{ formatCount(shelter.貓.count) }}</b><span>貓</span></div>
            <div class="scount"><b>{{ formatCount(shelter.其他.count) }}</b><span>其他</span></div>
          </div>
          <div class="r-spark">
            <ShelterSpark :histogram="shelter.all.histogram" :labels="labels" />
            <div class="spark-foot">
              中位數 {{ shelter.all.median_days === null ? '—' : formatCount(shelter.all.median_days) }} 天 ·
              最久 {{ shelter.all.max_days === null ? '—' : formatCount(shelter.all.max_days) }} 天
            </div>
          </div>
          <div class="r-actions">
            <RouterLink :to="{ name: 'shelter', params: { id: shelter.id } }" class="detail-btn">
              收容所介紹 <LucideIcon name="arrow-right" :size="16" />
            </RouterLink>
            <RouterLink :to="animalsLink({ shelter: shelter.id })" class="animals-link">
              看這裡的 {{ formatCount(shelter.all.count) }} 隻動物 →
            </RouterLink>
          </div>
        </li>
      </ul>

      <div v-else-if="results.length" class="shelters">
        <article v-for="shelter in results" :key="shelter.id" class="scard">
          <div class="scard-top">
            <span class="county">{{ shelter.county }}</span>
            <span class="scard-n">在所 {{ formatCount(shelter.all.count) }} 隻</span>
          </div>
          <h2>
            <RouterLink :to="{ name: 'shelter', params: { id: shelter.id } }">{{ shelter.name }}</RouterLink>
          </h2>
          <div class="smeta">
            <span v-for="address in addressesOf(shelter)" :key="address.text">
              <LucideIcon name="map-pin" :size="14" />
              <span class="line" :title="`原始資料：${address.raw}`">{{ address.text }}</span>
            </span>
            <span>
              <LucideIcon name="phone" :size="14" />
              <span v-if="phoneOf(shelter).href" class="line">{{ shelter.tel }}</span>
              <span v-else class="line missing">電話欄位不完整（原始資料：{{ shelter.tel }}）</span>
            </span>
          </div>
          <div class="scounts">
            <div class="scount"><b>{{ formatCount(shelter.狗.count) }}</b><span>狗</span></div>
            <div class="scount"><b>{{ formatCount(shelter.貓.count) }}</b><span>貓</span></div>
            <div class="scount"><b>{{ formatCount(shelter.其他.count) }}</b><span>其他</span></div>
          </div>
          <div class="spark-block">
            <div class="spark-cap">在所時間分布</div>
            <ShelterSpark :histogram="shelter.all.histogram" :labels="labels" />
            <div class="spark-foot">
              中位數 {{ shelter.all.median_days === null ? '—' : formatCount(shelter.all.median_days) }} 天 ·
              最久 {{ shelter.all.max_days === null ? '—' : formatCount(shelter.all.max_days) }} 天
            </div>
          </div>
          <div class="actions">
            <RouterLink :to="{ name: 'shelter', params: { id: shelter.id } }" class="detail-btn">
              收容所介紹 <LucideIcon name="arrow-right" :size="16" />
            </RouterLink>
            <RouterLink :to="animalsLink({ shelter: shelter.id })" class="animals-link">
              看這裡的 {{ formatCount(shelter.all.count) }} 隻動物 →
            </RouterLink>
          </div>
        </article>
      </div>
      <p v-else class="empty-state">沒有符合條件的收容所，試著放寬條件。</p>

      <section class="boundary">
        <div class="boundary-head">
          <span class="kicker">這一頁不能拿來說什麼</span>
        </div>
        <ul>
          <li>
            在所動物多不代表這間收容所做得比較差。收容量、腹地、所轄行政區的捕捉量差距很大，這一頁不做收容所之間的評比，也不排名。
          </li>
          <li>
            「在所時間分布」只算得出<strong>目前還在所內</strong>的動物。已經被認養、被領回或已不在名單上的動物不在這份資料裡，所以看不出一間收容所的認養速度。
          </li>
          <li v-if="notes.incompletePhone.length">
            電話直接來自原始資料，其中 {{ notes.incompletePhone.length }} 間的欄位不完整（{{
              names(notes.incompletePhone)
            }}）。
          </li>
          <li v-if="notes.machine.length">
            {{ notes.machine.length }} 間的地址欄混進了地圖連結或座標（{{ names(notes.machine) }}），本頁不顯示；其中的座標改拿來在收容所介紹頁定位地圖。「龍巖人本旁」「屏東科技大學內」這類地標補述幫得上忙，予以保留。滑鼠停在地址上可以看到原文。
          </li>
          <li v-if="notes.twoPlaces.length">
            {{ names(notes.twoPlaces) }} 在原始資料裡登錄了不同的地點，全部列出而不擇一。
          </li>
          <li v-if="notes.respelled.length">
            {{ names(notes.respelled) }} 是同一個地址被打成不同寫法（例如 <code>~</code> 與
            <code>-</code>、全形與半形），本頁合併為一筆。
          </li>
          <li v-for="group in notes.shared" :key="group[0].id">
            {{ names(group) }} 是不同紀錄共用同一個地址；是否為同一處所需要向主管機關確認，本頁照原始資料分開列出。
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.state {
  padding: 3rem 0;
  color: var(--ink-muted);
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 1.75rem;
}

.stat {
  padding: 1.15rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
  text-align: center;
}

.stat b {
  display: block;
  color: var(--accent-text);
  font-size: 1.85rem;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.stat span {
  color: var(--ink-secondary);
  font-size: 0.86rem;
}

/* ── Filter panel (same shape as the animals page) ── */
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

.select:focus-within,
.find-search:focus-within {
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

.find-search {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 16rem;
  min-height: 40px;
  padding: 0 0.8rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--plane);
  color: var(--ink-muted);
}

.find-search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--ink);
  font: inherit;
  font-size: 0.92rem;
}

.find-search input::placeholder {
  color: var(--ink-muted);
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
  white-space: nowrap;
}

.select.sort {
  min-width: 13.5rem;
}

/* ── View toggle ── */
.tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1rem;
}

.viewtoggle {
  display: inline-flex;
  padding: 3px;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: var(--surface);
}

.viewtoggle button {
  display: inline-grid;
  place-items: center;
  width: 2.25rem;
  height: 2rem;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--ink-secondary);
  font: inherit;
  font-size: 0.85rem;
  cursor: pointer;
}

.viewtoggle button:hover {
  color: var(--ink);
}

.viewtoggle button[aria-pressed='true'] {
  background: var(--ramp-4);
  color: var(--on-accent);
}

/* ── Shelter rows ── */
.rows {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 1.5rem 0 0;
  padding: 0;
  list-style: none;
}

.srow {
  display: grid;
  grid-template-columns: minmax(0, 2.4fr) minmax(0, 1.5fr) minmax(0, 1.5fr) auto;
  align-items: center;
  gap: 1.5rem;
  padding: 1.1rem 1.3rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
  transition: border-color 160ms ease;
}

.srow:hover {
  border-color: var(--ramp-3);
}

.r-main {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
}

.r-main h2 {
  font-size: 1.05rem;
}

.r-main h2 a {
  color: inherit;
  text-decoration: none;
}

.r-main h2 a:hover {
  color: var(--accent-text);
}

.r-counts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.25rem;
  padding: 0 1.25rem;
  border-right: 1px solid var(--hairline);
  border-left: 1px solid var(--hairline);
}

.scount.total b {
  color: var(--accent-text);
}

.r-spark {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
}

.r-actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.45rem;
  min-width: 11rem;
}

/* ── Shelter cards ── */
.shelters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.25rem;
  margin-top: 1.5rem;
}

.scard {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1.25rem 1.3rem 1.4rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
  transition: border-color 160ms ease;
}

.scard:hover {
  border-color: var(--ramp-3);
}

.scard-top {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.county {
  padding: 0.08rem 0.62rem;
  border-radius: 999px;
  background: var(--surface-sunk);
  color: var(--ink-secondary);
  font-size: 0.78rem;
}

.scard-n {
  margin-left: auto;
  color: var(--ink-muted);
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
}

/* Names hold two lines so a row's numbers and charts line up. */
.scard h2 {
  display: -webkit-box;
  min-height: 2.7em;
  overflow: hidden;
  font-size: 1.05rem;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.scard h2 a {
  color: inherit;
  text-decoration: none;
}

.scard h2 a:hover {
  color: var(--accent-text);
}

.smeta {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  color: var(--ink-muted);
  font-size: 0.83rem;
}

.smeta > span {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
}

.smeta svg {
  flex-shrink: 0;
  margin-top: 0.3rem;
}

/* One line each: source addresses vary wildly in length. Hover shows it all. */
.smeta .line {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.smeta .missing {
  opacity: 0.75;
}

.scounts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
  padding: 0.8rem 0;
  border-top: 1px solid var(--hairline);
  border-bottom: 1px solid var(--hairline);
}

.scount {
  text-align: center;
}

.scount b {
  display: block;
  font-size: 1.15rem;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}

.scount span {
  color: var(--ink-muted);
  font-size: 0.78rem;
}

.spark-block {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.spark-cap {
  color: var(--ink-muted);
  font-size: 0.76rem;
  letter-spacing: 0.08em;
}

.spark-foot {
  color: var(--ink-secondary);
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
}

.actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.55rem;
  margin-top: auto;
  padding-top: 0.35rem;
}

.detail-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.45rem 2.4rem 0.45rem 1rem;
  border: 1px solid var(--ink);
  border-radius: 999px;
  color: var(--ink);
  font-size: 0.9rem;
  font-weight: 500;
  text-decoration: none;
  transition:
    background 160ms ease,
    color 160ms ease;
}

.detail-btn svg {
  position: absolute;
  right: 1.05rem;
}

.detail-btn:hover {
  background: var(--ink);
  color: var(--plane);
}

.animals-link {
  color: var(--accent-text);
  font-size: 0.86rem;
  text-align: center;
  text-decoration: none;
  font-variant-numeric: tabular-nums;
}

.animals-link:hover {
  text-decoration: underline;
}

.empty-state {
  margin-top: 1.5rem;
  padding: 3rem 1.5rem;
  border: 1px dashed var(--hairline);
  border-radius: var(--radius);
  color: var(--ink-muted);
  text-align: center;
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
}

.kicker {
  color: var(--ink-muted);
  font-size: 0.72rem;
  letter-spacing: 0.14em;
}

.boundary ul {
  margin: 0.6rem 0 0;
  padding-left: 1.1rem;
}

.boundary li {
  margin-bottom: 0.45rem;
  color: var(--ink-secondary);
  font-size: 0.86rem;
}

.boundary code {
  padding: 0 0.3rem;
  border: 1px solid var(--hairline);
  border-radius: 4px;
  background: var(--surface);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.92em;
}

@media (max-width: 1000px) {
  .shelters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  /* Two lines per row: who and where on top, the numbers underneath. */
  .srow {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
    gap: 1rem 1.25rem;
  }

  .r-main {
    grid-column: 1 / -1;
  }

  .r-counts {
    padding: 0 1.25rem 0 0;
    border-left: 0;
  }
}

@media (max-width: 820px) {
  .field,
  .find-search {
    width: 100%;
  }

  .select,
  .find-search {
    min-width: 0;
  }

  .select {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .srow {
    grid-template-columns: minmax(0, 1fr);
  }

  .r-counts {
    padding: 0.7rem 0;
    border-top: 1px solid var(--hairline);
    border-right: 0;
    border-bottom: 1px solid var(--hairline);
  }

  .r-actions {
    min-width: 0;
  }

  /* minmax(0, …), not 1fr: a one-line address would otherwise size the
     column to its full length and push the page sideways. */
  .stats,
  .shelters {
    grid-template-columns: minmax(0, 1fr);
  }

  .scard h2 {
    min-height: 0;
  }
}

@media (max-width: 520px) {
  .tools {
    width: 100%;
    flex-wrap: nowrap;
  }

  .sortwrap {
    flex: 1;
    min-width: 0;
  }

  .select.sort {
    flex: 1;
    min-width: 0;
  }
}
</style>
