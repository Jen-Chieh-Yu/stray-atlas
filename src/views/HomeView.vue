<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AnimalCard from '@/components/AnimalCard.vue'
import AnimalDialog from '@/components/AnimalDialog.vue'
import HeroCarousel from '@/components/HeroCarousel.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import { useRoster } from '@/composables/useRoster'
import { closeAnimalDialog } from '@/lib/dialogRoute'
import { vReveal } from '@/lib/reveal'
import {
  AGE_LABEL,
  BODY_LABEL,
  DAY_BANDS,
  animalsLink,
  formatCount,
  inBand,
  median,
  tally,
} from '@/lib/animals'
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
  knownDays,
  percentileOf,
  byLongest,
} = useRoster()

const longest = computed(() => byLongest.value.slice(0, 10))

/** Newest intake first, by 建檔日 — the date the record entered the system. */
function newest(kind: Kind): Animal[] {
  return animals.value
    .filter((animal) => animal.kind === kind && daysOf(animal) !== null)
    .sort((a, b) => (daysOf(a) ?? 0) - (daysOf(b) ?? 0))
    .slice(0, 4)
}

const kindCount = computed(() => new Map(tally(animals.value, (animal) => animal.kind)))

const newestBlocks = computed(() => [
  {
    kind: '狗' as const,
    icon: 'dog' as const,
    title: '狗狗',
    list: newest('狗'),
    note: '依建檔日期由新到舊。建檔日是資料進到系統的時間，不等於被撿到的日子。',
  },
  {
    kind: '貓' as const,
    icon: 'cat' as const,
    title: '貓咪',
    list: newest('貓'),
    note: '依建檔日期由新到舊。想看等最久的，用「已在所天數」排序。',
  },
])

/* ── Filter box ────────────────────────────────────────────────────────── */

const SPECIES = [
  { kind: '狗' as const, icon: 'dog' as const, label: '尋找狗狗' },
  { kind: '貓' as const, icon: 'cat' as const, label: '尋找貓咪' },
]

const species = ref<'狗' | '貓'>('狗')
const search = ref('')

/** Shortcuts under the search field follow the tab, since the links carry it. */
const quickChips = computed(() => {
  const kind = species.value
  const list = animals.value.filter((animal) => animal.kind === kind)
  const chips = tally(list, countyOf)
    .filter(([county]) => county)
    .slice(0, 4)
    .map(([county, count]) => ({ label: county, count, to: animalsLink({ kind, county }) }))
  chips.push(
    {
      label: '幼體',
      count: list.filter((animal) => animal.age === 'CHILD').length,
      to: animalsLink({ kind, age: 'CHILD' }),
    },
    {
      label: '小型',
      count: list.filter((animal) => animal.body === 'SMALL').length,
      to: animalsLink({ kind, body: 'SMALL' }),
    },
    {
      label: '已在所 2 年以上',
      count: list.filter((animal) => (daysOf(animal) ?? -1) > 730).length,
      to: animalsLink({ kind, daysFrom: '2-5y' }),
    },
  )
  return chips.filter((chip) => chip.count > 0)
})

function submitSearch() {
  void router.push(animalsLink({ kind: species.value, q: search.value.trim() }))
}

/* ── Browse bands ──────────────────────────────────────────────────────── */

function varietyCard(kind: '狗' | '貓', limit: number) {
  const list = animals.value.filter((animal) => animal.kind === kind)
  const varieties = tally(list, (animal) => animal.variety || '未填品種')
  return {
    kinds: varieties.length,
    total: list.length,
    top: varieties.slice(0, limit).map(([name, count]) => ({
      name,
      count,
      to: animalsLink({ kind, variety: name }),
    })),
  }
}

const kindCards = computed(() => [
  { kind: '狗' as const, icon: 'dog' as const, title: '狗狗', data: varietyCard('狗', 10), more: '查看更多犬種' },
  { kind: '貓' as const, icon: 'cat' as const, title: '貓咪', data: varietyCard('貓', 8), more: '查看更多貓種' },
])

const mixedShare = computed(() => {
  const total = animals.value.length
  if (total === 0) return 0
  return Math.round(
    (animals.value.filter((animal) => animal.group === 'mixed').length / total) * 100,
  )
})

/** 其他 is a handful of species; group the variety names into plain words. */
const OTHER_GROUPS = ['兔', '刺蝟', '鸚鵡', '象龜', '絨鼠']
const others = computed(() => {
  const list = animals.value.filter((animal) => animal.kind === '其他')
  const names: string[] = []
  for (const animal of list) {
    const name = OTHER_GROUPS.find((group) => animal.variety.includes(group)) ?? animal.variety
    if (name && !names.includes(name)) names.push(name)
  }
  return { count: list.length, names }
})

const counties = computed(() =>
  tally(animals.value, countyOf)
    .filter(([county]) => county)
    .map(([county, count]) => ({ label: county, count, to: animalsLink({ county }) })),
)

const bodyChips = computed(() =>
  Object.entries(BODY_LABEL).map(([code, label]) => ({
    label,
    count: animals.value.filter((animal) => animal.body === code).length,
    to: animalsLink({ body: code }),
  })),
)

const ageChips = computed(() =>
  Object.entries(AGE_LABEL).map(([code, label]) => ({
    label,
    count: animals.value.filter((animal) => animal.age === code).length,
    to: animalsLink({ age: code }),
  })),
)

const bandChips = computed(() =>
  DAY_BANDS.map((band) => ({
    label: band.label,
    count: animals.value.filter((animal) => inBand(daysOf(animal), band.min, band.max)).length,
    to: animalsLink({ days: band.key }),
  })),
)

const overallMedian = computed(() => median(knownDays.value))
const countyCount = computed(() => new Set(shelters.value.map((shelter) => shelter.county)).size)

/* ── Longest strip: arrows ─────────────────────────────────────────────── */

const strip = ref<HTMLElement | null>(null)
const stripWrap = ref<HTMLElement | null>(null)
const atStart = ref(true)
const atEnd = ref(false)

function syncStrip() {
  const el = strip.value
  if (!el) return
  // The arrows sit on the photo's horizontal midline, which moves with the
  // card width, so it is measured rather than hard-coded.
  const avatar = el.querySelector('.avatar')
  if (avatar && stripWrap.value) {
    stripWrap.value.style.setProperty(
      '--avatar-half',
      `${avatar.getBoundingClientRect().height / 2}px`,
    )
  }
  atStart.value = el.scrollLeft <= 1
  atEnd.value = el.scrollLeft >= el.scrollWidth - el.clientWidth - 1
}

function scrollStrip(direction: 1 | -1) {
  const el = strip.value
  const card = el?.firstElementChild
  if (!el || !card) return
  const gap = parseFloat(getComputedStyle(el).columnGap) || 0
  el.scrollBy({ left: direction * (card.getBoundingClientRect().width + gap), behavior: 'smooth' })
}

let observer: ResizeObserver | null = null
watch(strip, (el) => {
  observer?.disconnect()
  observer = null
  if (!el) return
  observer = new ResizeObserver(syncStrip)
  observer.observe(el)
  void nextTick(syncStrip)
})

onBeforeUnmount(() => observer?.disconnect())

/* ── Detail dialog ─────────────────────────────────────────────────────── */

/** Same contract as the grid pages: the open animal is ?animal=<id>, so Back
 *  closes the dialog and the link can be shared. */
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

/** Rewritten from the Taipei animal protection office's published steps. */
const FLOW = [
  { title: '找到動物，記下編號', text: '收容編號是收容所辨識這隻動物的唯一依據。', site: true },
  { title: '電話聯繫收容所', text: '確認動物仍在所，並預約到現場看動物的時間。', site: false },
  {
    title: '完成飼主責任教育',
    text: '線上課程至少 1 小時，內容為飼主責任、動物福利與飼養管理。',
    site: false,
  },
  {
    title: '現場諮詢與填申請書',
    text: '備妥身分證明文件；部分縣市會安排家訪或互動評估。',
    site: false,
  },
  {
    title: '健康檢查與晶片',
    text: '獸醫檢查並說明健康狀況；犬隻植入晶片、辦理寵物登記與狂犬病疫苗。',
    site: false,
  },
  { title: '帶牠回家', text: '犬隻須以牽繩或提籠固定，貓咪須使用硬式提籠。', site: false },
]
</script>

<template>
  <div class="home">
    <!-- Hero: illustrative photo carousel with the title plate overlapping its
         lower edge (2026-09-17; replaces the plain ground of 2026-09-15). -->
    <div class="hero">
      <div class="herobanner">
        <HeroCarousel />
        <div class="hero-plate">
          <h1>牠們一直都在等待被看見</h1>
          <p class="lede">
            全臺{{ shelters.length ? ` ${shelters.length} 間` : '' }}公立收容所目前仍開放認養的動物。
          </p>
        </div>
      </div>

      <div class="wrap">
        <form class="filterbox" :data-species="species" role="search" @submit.prevent="submitSearch">
          <div class="fb-tabs" role="tablist" aria-label="動物類型">
            <span class="fb-thumb" aria-hidden="true" />
            <button
              v-for="option in SPECIES"
              :key="option.kind"
              type="button"
              role="tab"
              class="fb-tab"
              :aria-selected="species === option.kind"
              @click="species = option.kind"
            >
              <LucideIcon :name="option.icon" :size="20" />
              {{ option.label }}
              <span v-if="!loading && !error" class="n">
                {{ formatCount(kindCount.get(option.kind) ?? 0) }} 隻
              </span>
            </button>
          </div>

          <div class="fb-row">
            <label class="fb-search">
              <LucideIcon name="search" :size="18" />
              <input
                v-model="search"
                type="search"
                placeholder="以縣市、收容所、品種搜尋"
                aria-label="搜尋"
              />
            </label>
            <button class="fb-go" type="submit">搜尋</button>
          </div>

          <div v-if="!loading && !error" class="fb-chips">
            <RouterLink v-for="chip in quickChips" :key="chip.label" :to="chip.to" class="fb-chip">
              {{ chip.label }} {{ formatCount(chip.count) }}
            </RouterLink>
          </div>

          <RouterLink :to="animalsLink({ kind: species })" class="fb-more">
            <LucideIcon name="plus" :size="16" />
            增加篩選條件（收容所、品種、性別、體型、已在所天數）
          </RouterLink>
        </form>
      </div>
    </div>

    <LoadingSkeleton
      v-if="loading"
      class="wrap"
      variant="cards"
      :count="4"
      hint="全國動物資料約 272 KB"
    />
    <p v-else-if="error" class="wrap state">資料載入失敗（{{ error }}）。</p>

    <template v-else>
      <!-- Three numbers -->
      <section v-reveal class="wrap">
        <div class="stats">
          <div class="stat">
            <b>{{ formatCount(animals.length) }}</b><span>隻動物目前仍在所</span>
          </div>
          <div class="stat">
            <b>{{ shelters.length }}</b><span>間公立收容所，涵蓋 {{ countyCount }} 縣市</span>
          </div>
          <div class="stat">
            <b>{{ overallMedian === null ? '—' : formatCount(overallMedian) }}</b>
            <span>天，已在所天數的中位數</span>
          </div>
        </div>
      </section>

      <!-- Longest stays, dogs and cats together -->
      <section v-reveal class="wrap">
        <div class="sec-head">
          <h2><LucideIcon name="clock" :size="22" /> 等最久的</h2>
          <RouterLink :to="animalsLink({ sort: 'longest' })">依已在所天數排序 →</RouterLink>
        </div>

        <div ref="stripWrap" class="longest-wrap">
          <button
            type="button"
            class="lnav prev"
            aria-label="看前面幾隻"
            :disabled="atStart"
            @click="scrollStrip(-1)"
          >
            <LucideIcon name="chevron-left" :size="20" />
          </button>
          <div ref="strip" class="longest" @scroll.passive="syncStrip">
            <div v-for="(animal, index) in longest" :key="animal.id" class="lcard">
              <AnimalCard
                :animal="animal"
                :days="daysOf(animal)"
                :percentile="percentileOf(animal)"
                :longest="index === 0"
                :place="placeOf(animal)"
                @open="open"
              />
            </div>
          </div>
          <button
            type="button"
            class="lnav next"
            aria-label="看後面幾隻"
            :disabled="atEnd"
            @click="scrollStrip(1)"
          >
            <LucideIcon name="chevron-right" :size="20" />
          </button>
        </div>
        <div class="more-row">
          <RouterLink :to="animalsLink({ sort: 'longest' })" class="more-btn">
            查看更多等最久的動物 <LucideIcon name="arrow-right" :size="18" />
          </RouterLink>
        </div>
      </section>

      <!-- Newest dogs, newest cats -->
      <section v-for="block in newestBlocks" :key="block.kind" v-reveal class="wrap">
        <div class="sec-head">
          <h2><LucideIcon :name="block.icon" :size="22" /> {{ block.title }}</h2>
          <RouterLink :to="animalsLink({ kind: block.kind })">
            全部 {{ formatCount(kindCount.get(block.kind) ?? 0) }} 隻 →
          </RouterLink>
        </div>
        <p class="sec-note">{{ block.note }}</p>
        <div class="grid">
          <AnimalCard
            v-for="animal in block.list"
            :key="animal.id"
            :animal="animal"
            :days="daysOf(animal)"
            :percentile="percentileOf(animal)"
            :place="placeOf(animal)"
            @open="open"
          />
        </div>
        <div class="more-row">
          <RouterLink :to="animalsLink({ kind: block.kind, sort: 'shortest' })" class="more-btn">
            查看更多{{ block.title }} <LucideIcon name="arrow-right" :size="18" />
          </RouterLink>
        </div>
      </section>

      <!-- Adoption steps -->
      <section v-reveal class="wrap">
        <div class="sec-head"><h2>認養流程</h2></div>
        <p class="sec-note">
          本站不辦理認養，也不代收申請。認養一律由該動物所在的收容所受理，這裡只負責把你需要的資訊整理齊全。
        </p>

        <div class="flowbox">
          <div class="lane-labels" aria-hidden="true">
            <span class="lane site">在 STRAYATLAS</span>
            <span class="lane">在收容所受理</span>
          </div>
          <ol class="chart">
            <template v-for="(step, index) in FLOW" :key="step.title">
              <li class="fnode" :class="{ site: step.site }">
                <span class="n">STEP {{ String(index + 1).padStart(2, '0') }}</span>
                <h3>{{ step.title }}</h3>
                <p>{{ step.text }}</p>
              </li>
              <li v-if="index < FLOW.length - 1" class="farrow" aria-hidden="true">
                <LucideIcon name="arrow-right" :size="18" />
              </li>
            </template>
          </ol>
          <p class="flow-foot">
            以臺北市動物保護處公告之認養步驟為例。各縣市在教育時數、家訪安排與規費上略有不同，實際流程以該收容所公告為準。
          </p>
        </div>
      </section>

      <!-- Browse by kind -->
      <div v-reveal class="kindband">
        <div class="wrap">
          <div class="kindband-head">
            <h2>
              <LucideIcon name="dog" :size="22" /> 從種類搜尋 <LucideIcon name="cat" :size="22" />
            </h2>
            <p>
              全臺在所動物有 {{ mixedShare }}% 是米克斯。純種犬貓數量少，但每一種都能單獨篩出來。
            </p>
          </div>

          <div class="kinds">
            <div v-for="card in kindCards" :key="card.kind" class="kind-card">
              <h3 class="kind-head">
                <LucideIcon :name="card.icon" :size="20" /> {{ card.title }}
                <span class="n">{{ card.data.kinds }} 種 · {{ formatCount(card.data.total) }} 隻</span>
              </h3>
              <div class="kind-chips">
                <RouterLink
                  v-for="item in card.data.top"
                  :key="item.name"
                  :to="item.to"
                  class="kind-chip"
                >
                  {{ item.name }} <span class="count">{{ formatCount(item.count) }}</span>
                </RouterLink>
              </div>
              <RouterLink :to="animalsLink({ kind: card.kind })" class="kind-more">
                {{ card.more }} <LucideIcon name="arrow-right" :size="16" />
              </RouterLink>
            </div>
          </div>

          <p v-if="others.count > 0" class="kindband-foot">
            另有 {{ others.count }} 隻其他動物（{{ others.names.join('、') }}）在所，<RouterLink
              :to="animalsLink({ kind: '其他' })"
              >在這裡查看</RouterLink
            >。
          </p>
        </div>
      </div>

      <!-- Browse by condition -->
      <div v-reveal class="kindband">
        <div class="wrap">
          <div class="kindband-head">
            <h2><LucideIcon name="sliders-horizontal" :size="22" /> 依條件瀏覽</h2>
            <p>
              不確定要找什麼的時候，從你在意的那一項開始收斂：地點、體型年齡，或牠已經等了多久。
            </p>
          </div>

          <div class="browse">
            <div class="kind-card">
              <h3 class="kind-head">
                依縣市 <span class="n">{{ counties.length }} 縣市</span>
              </h3>
              <div class="kind-chips">
                <RouterLink
                  v-for="item in counties.slice(0, 8)"
                  :key="item.label"
                  :to="item.to"
                  class="kind-chip"
                >
                  {{ item.label }} <span class="count">{{ formatCount(item.count) }}</span>
                </RouterLink>
              </div>
              <RouterLink to="/map" class="kind-more">
                查看全部 {{ counties.length }} 縣市 <LucideIcon name="arrow-right" :size="16" />
              </RouterLink>
            </div>

            <div class="kind-card">
              <h3 class="kind-head">
                依體型與年齡 <span class="n">{{ formatCount(animals.length) }} 隻</span>
              </h3>
              <span class="kind-sub">體型</span>
              <div class="kind-chips">
                <RouterLink v-for="item in bodyChips" :key="item.label" :to="item.to" class="kind-chip">
                  {{ item.label }} <span class="count">{{ formatCount(item.count) }}</span>
                </RouterLink>
              </div>
              <span class="kind-sub">年齡</span>
              <div class="kind-chips">
                <RouterLink v-for="item in ageChips" :key="item.label" :to="item.to" class="kind-chip">
                  {{ item.label }} <span class="count">{{ formatCount(item.count) }}</span>
                </RouterLink>
              </div>
            </div>

            <div class="kind-card">
              <h3 class="kind-head">
                依已在所天數
                <span class="n">
                  中位數 {{ overallMedian === null ? '—' : formatCount(overallMedian) }} 天
                </span>
              </h3>
              <div class="kind-chips">
                <RouterLink v-for="item in bandChips" :key="item.label" :to="item.to" class="kind-chip">
                  {{ item.label }} <span class="count">{{ formatCount(item.count) }}</span>
                </RouterLink>
              </div>
            </div>
          </div>
        </div>
      </div>
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
/* Home runs full-bleed (route meta), so every block brings its own .wrap. */
section {
  padding-top: 4.5rem;
}

.state {
  padding-top: 3rem;
  padding-bottom: 3rem;
  color: var(--ink-muted);
}

.sec-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;

  & h2 {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    font-size: 1.4rem;
  }

  & a {
    color: var(--accent-text);
    font-size: 0.9rem;
    white-space: nowrap;
    text-decoration: none;
  }
}

.sec-note {
  max-width: 46rem;
  margin: 0.35rem 0 0;
  color: var(--ink-secondary);
  font-size: 0.9rem;
}

/* ── Hero ── */
.hero {
  padding-bottom: 1.5rem;
}

.herobanner {
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* The plate overlaps the photo's lower edge, where the ground usually is,
   so it never covers an animal's face. */
.hero-plate {
  position: relative;
  z-index: 1;
  max-width: 660px;
  margin: -3.25rem 1.5rem 0;
  padding: 1.75rem 2.25rem;
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: 0 6px 18px color-mix(in srgb, var(--ink) 12%, transparent);
  text-align: center;
}

.hero h1 {
  max-width: 15em;
  margin: 0 auto;
  font-size: clamp(1.6rem, 3.6vw, 2.5rem);
  text-wrap: balance;
}

.hero .lede {
  max-width: 32em;
  margin: 0.85rem auto 0;
  color: var(--ink-secondary);
  font-size: 0.98rem;
  text-wrap: pretty;
}

/* ── Filter box ── */
.filterbox {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  max-width: 940px;
  margin: 2.5rem auto 0;
  padding: 1rem 1.25rem 1.25rem;
  border-radius: var(--radius);
  background: var(--ramp-4);
}

.fb-tabs {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 4px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--on-accent) 16%, transparent);
}

.fb-thumb {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  border-radius: 999px;
  background: var(--surface);
  transition: transform 280ms cubic-bezier(0.4, 0, 0.2, 1);
}

.filterbox[data-species='貓'] .fb-thumb {
  transform: translateX(100%);
}

.fb-tab {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--on-accent);
  font: inherit;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition: color 280ms ease;

  &[aria-selected='true'] {
    color: var(--ink);
  }

  & .n {
    font-size: 0.85rem;
    opacity: 0.8;
    font-variant-numeric: tabular-nums;
  }

  & svg {
    flex-shrink: 0;
  }
}

.fb-row {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 0.75rem;
}

.fb-search {
  flex: 1 1 320px;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-height: 48px;
  padding: 0 0.85rem;
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--ink-muted);

  &:focus-within {
    outline: 2px solid var(--ink);
    outline-offset: 2px;
  }

  & input {
    flex: 1;
    min-width: 0;
    border: 0;
    outline: 0;
    background: transparent;
    color: var(--ink);
    font: inherit;
    font-size: 0.95rem;

    &::placeholder {
      color: var(--ink-muted);
    }
  }
}

.fb-go {
  min-height: 48px;
  padding: 0 1.4rem;
  border: 0;
  border-radius: var(--radius-sm);
  background: var(--ink);
  color: var(--plane);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.fb-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.fb-chip {
  padding: 0.28rem 0.8rem;
  border: 1px solid color-mix(in srgb, var(--on-accent) 32%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--on-accent) 16%, transparent);
  color: var(--on-accent);
  font-size: 0.86rem;
  font-variant-numeric: tabular-nums;
  text-decoration: none;
  transition: background 160ms ease;

  &:hover {
    background: color-mix(in srgb, var(--on-accent) 28%, transparent);
  }
}

.fb-more {
  align-self: center;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 1.6rem;
  border-radius: 999px;
  background: var(--surface);
  color: var(--ink);
  font-size: 0.92rem;
  text-decoration: none;

  & svg {
    flex-shrink: 0;
  }
}

/* ── Stats ── */
.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}

.stat {
  padding: 1.15rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
  text-align: center;

  & b {
    display: block;
    color: var(--accent-text);
    font-size: 1.85rem;
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
  }

  & span {
    color: var(--ink-secondary);
    font-size: 0.86rem;
  }
}

/* ── Card rows ── */
.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 2rem 1.5rem;
  margin-top: 1.5rem;
}

.longest-wrap {
  position: relative;
  margin-top: 1.5rem;
}

.longest {
  display: flex;
  gap: 1.5rem;
  overflow-x: auto;
  scroll-behavior: smooth;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.lcard {
  flex: 0 0 calc((100% - 4.5rem) / 4);
  scroll-snap-align: start;
}

/* Centred on the photo's left and right edges, on its horizontal midline. */
.lnav {
  position: absolute;
  top: var(--avatar-half, 132px);
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  padding: 0;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: var(--surface);
  color: var(--ink);
  cursor: pointer;
  transition:
    opacity 160ms ease,
    border-color 160ms ease;

  &:hover {
    border-color: var(--ramp-3);
  }

  &.prev {
    left: 0;
    transform: translate(-50%, -50%);
  }

  &.next {
    right: 0;
    transform: translate(50%, -50%);
  }

  &:disabled {
    opacity: 0.3;
    pointer-events: none;
  }
}

.more-row {
  display: flex;
  justify-content: center;
  margin-top: 2rem;
}

.more-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 2rem;
  border: 1px solid var(--ramp-4);
  border-radius: 999px;
  color: var(--ramp-4);
  font-weight: 500;
  text-decoration: none;
  transition:
    background 160ms ease,
    color 160ms ease;

  &:hover {
    background: var(--ramp-4);
    color: var(--on-accent);
  }
}

.more-btn svg,
.kind-more svg {
  transition: transform 180ms ease;
}

.more-btn:hover svg,
.kind-more:hover svg {
  transform: translateX(3px);
}

/* ── Adoption steps ── */
.flowbox {
  margin-top: 1.5rem;
  padding: 1.75rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
}

.lane-labels {
  display: grid;
  grid-template-columns: 1fr 5fr;
  gap: 0.75rem;
  margin-bottom: 0.9rem;
}

.lane {
  padding-bottom: 0.4rem;
  border-bottom: 2px solid var(--hairline);
  color: var(--ink-muted);
  font-size: 0.76rem;
  letter-spacing: 0.1em;

  &.site {
    border-bottom-color: var(--ramp-4);
    color: var(--accent-text);
  }
}

.chart {
  display: flex;
  align-items: stretch;
  gap: 0.4rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.fnode {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.85rem 0.8rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--plane);

  &.site {
    border-color: var(--ramp-4);
    background: var(--surface-sunk);
  }

  & .n {
    color: var(--ink-muted);
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    font-variant-numeric: tabular-nums;
  }

  & h3 {
    font-size: 0.92rem;
    line-height: 1.4;
  }

  & p {
    margin: 0;
    color: var(--ink-secondary);
    font-size: 0.8rem;
    line-height: 1.55;
  }
}

.farrow {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  color: var(--ink-muted);
}

.flow-foot {
  margin: 1rem 0 0;
  color: var(--ink-muted);
  font-size: 0.84rem;
}

/* ── Orange bands ── */
.kindband {
  margin-top: 4.5rem;
  padding: 4.5rem 0;
  background: var(--ramp-4);

  & + .kindband {
    margin-top: 0;
    padding-top: 0;

    & > .wrap {
      padding-top: 4.5rem;
      border-top: 1px solid color-mix(in srgb, var(--on-accent) 22%, transparent);
    }
  }
}

.kindband-head {
  text-align: center;

  & h2 {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    color: var(--on-accent);
    font-size: 1.4rem;
  }

  & p {
    max-width: 40rem;
    margin: 0.6rem auto 0;
    color: color-mix(in srgb, var(--on-accent) 85%, transparent);
    font-size: 0.9rem;
  }
}

.kinds {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
  margin-top: 2rem;
}

.browse {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.25rem;
  margin-top: 2rem;
}

.kind-card {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  padding: 1.5rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
}

.kind-head {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  color: var(--accent-text);
  font-size: 1.05rem;
  font-weight: 700;

  & .n {
    margin-left: auto;
    color: var(--ink-muted);
    font-size: 0.85rem;
    font-weight: 400;
    font-variant-numeric: tabular-nums;
  }
}

.kind-sub {
  margin-bottom: -0.5rem;
  color: var(--ink-muted);
  font-size: 0.8rem;
}

.kind-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.kind-chip {
  padding: 0.38rem 0.85rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  color: var(--ink);
  font-size: 0.88rem;
  font-variant-numeric: tabular-nums;
  text-decoration: none;
  transition:
    border-color 160ms ease,
    background 160ms ease;

  &:hover {
    border-color: var(--ramp-3);
    background: var(--surface-sunk);
  }

  & .count {
    color: var(--ink-muted);
  }
}

.kind-more {
  align-self: center;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin-top: auto;
  padding: 0.45rem 1.4rem;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  color: var(--ink);
  font-size: 0.9rem;
  text-decoration: none;
  transition: border-color 160ms ease;

  &:hover {
    border-color: var(--ramp-3);
  }
}

.kindband-foot {
  margin: 1.5rem 0 0;
  color: color-mix(in srgb, var(--on-accent) 80%, transparent);
  font-size: 0.85rem;
  text-align: center;

  & a {
    color: var(--on-accent);
  }
}

/* ── Responsive ── */
@media (max-width: 1080px) {
  .chart {
    flex-direction: column;
  }

  .farrow {
    justify-content: center;
    padding: 0.1rem 0;
    transform: rotate(90deg);
  }

  .lane-labels {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1000px) {
  .browse {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 820px) {
  .lcard {
    flex-basis: calc((100% - 1.5rem) / 2);
  }

  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stats,
  .kinds {
    grid-template-columns: 1fr;
  }

  .hero-plate {
    padding: 1.25rem;
  }
}

/* Phones: the carousel is squarer and its credit sits at the bottom, so the
   plate moves below the photo instead of overlapping it. */
@media (max-width: 700px) {
  .hero-plate {
    margin-top: 1rem;
    box-shadow: none;
  }
}

@media (max-width: 480px) {
  /* Two labels, an icon and a count do not fit half of a phone width; the
     count is repeated in the section headings further down. */
  .fb-tab .n {
    display: none;
  }

  .browse {
    grid-template-columns: 1fr;
  }

  .fb-go {
    width: 100%;
  }

  .flowbox {
    padding: 1.1rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .fb-thumb {
    transition: none;
  }

  .longest {
    scroll-behavior: auto;
  }
}
</style>
