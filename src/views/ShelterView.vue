<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AnimalCard from '@/components/AnimalCard.vue'
import AnimalDialog from '@/components/AnimalDialog.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import ShelterSpark from '@/components/ShelterSpark.vue'
import { useRoster } from '@/composables/useRoster'
import { animalsLink, formatCount, median } from '@/lib/animals'
import { closeAnimalDialog } from '@/lib/dialogRoute'
import { addressesOf, mapEmbedUrl, mapOpenUrl, phoneOf } from '@/lib/shelters'
import type { Animal, Kind } from '@/types'

/* The shelter introduction page (.notes/drafts/shelter-detail.html): its
 * longest stays first, then how to reach it, then its numbers. The full list
 * of its animals lives on the animals page, one link away. */

const route = useRoute()
const router = useRouter()

const {
  animals,
  shelters,
  snapshotDate,
  buckets,
  loading,
  error,
  daysOf,
  knownDays,
  percentileOf,
  longestId,
  placeOf,
} = useRoster()

const shelter = computed(() => shelters.value.find((item) => item.id === route.params.id) ?? null)

const mine = computed(() =>
  animals.value
    .filter((animal) => animal.shelter === shelter.value?.id)
    .sort((a, b) => (daysOf(b) ?? -1) - (daysOf(a) ?? -1)),
)

const longest = computed(() => mine.value.slice(0, 4))
const overTwoYears = computed(() => mine.value.filter((animal) => (daysOf(animal) ?? -1) > 730).length)

const rank = computed(() => {
  const own = shelter.value?.all.count ?? 0
  return shelters.value.filter((item) => item.all.count > own).length + 1
})

const nationalMedian = computed(() => median(knownDays.value))

const addresses = computed(() => (shelter.value ? addressesOf(shelter.value) : []))
const phone = computed(() => (shelter.value ? phoneOf(shelter.value) : null))
const primary = computed(() => addresses.value[0] ?? null)
const embed = computed(() => (primary.value ? mapEmbedUrl(primary.value) : null))

function share(count: number): string {
  const total = shelter.value?.all.count ?? 0
  return total ? `${Math.round((count / total) * 100)}%` : '—'
}

/* ── Stay distribution: all, dogs or cats ──────────────────────────────── */

type Scope = 'all' | Kind
const SCOPES: { id: Scope; label: string }[] = [
  { id: 'all', label: '全部' },
  { id: '狗', label: '狗' },
  { id: '貓', label: '貓' },
]
const scope = ref<Scope>('all')
const histogram = computed(() => shelter.value?.[scope.value].histogram ?? [])
const labels = computed(() => buckets.value.map((bucket) => bucket.label))

/* ── Detail dialog, same contract as the other card pages ──────────────── */

const openAnimal = computed<Animal | null>(() => {
  const id = route.query.animal
  if (typeof id !== 'string') return null
  return mine.value.find((animal) => animal.id === id) ?? null
})

function open(animal: Animal) {
  void router.push({ query: { ...route.query, animal: animal.id } })
}

function close() {
  closeAnimalDialog(router, route)
}
</script>

<template>
  <div>
    <RouterLink to="/shelters" class="crumb">
      <LucideIcon name="chevron-left" :size="16" /> 收容所列表
    </RouterLink>

    <p v-if="loading" class="state">載入中…</p>
    <p v-else-if="error" class="state">收容所資料載入失敗（{{ error }}）。</p>
    <p v-else-if="!shelter" class="state">
      找不到這間收容所，它可能已不在最新的資料裡。<RouterLink to="/shelters">回收容所列表</RouterLink>
    </p>

    <template v-else>
      <header class="head">
        <h1>{{ shelter.name }}</h1>
        <p>
          目前有 {{ formatCount(shelter.all.count) }} 隻動物仍在所，是全臺在所數第 {{ rank }}
          多的公立收容所。出發前請先來電，確認想看的動物還在。
          <span class="stamp">資料快照 {{ snapshotDate }}</span>
        </p>
      </header>

      <!-- Animals first: they are why most visitors came. Each block below
           carries an icon head and a rule above it, so the page reads as
           three parts rather than one long scroll. -->
      <section class="sect" aria-labelledby="s-animals">
        <div class="sect-head">
          <span class="sect-icon" aria-hidden="true"><LucideIcon name="hourglass" :size="20" /></span>
          <div class="sect-title">
            <h2 id="s-animals">這裡等最久的</h2>
            <p>這間收容所已在所天數最長的 {{ longest.length }} 隻。完整名單與篩選在「找動物」。</p>
          </div>
          <RouterLink :to="animalsLink({ shelter: shelter.id })" class="sect-link">
            依已在所天數排序 →
          </RouterLink>
        </div>
        <div class="grid">
          <AnimalCard
            v-for="animal in longest"
            :key="animal.id"
            :animal="animal"
            :days="daysOf(animal)"
            :percentile="percentileOf(animal)"
            :longest="animal.id === longestId"
            :place="placeOf(animal)"
            @open="open"
          />
        </div>
        <div class="cta-row">
          <RouterLink :to="animalsLink({ shelter: shelter.id })" class="cta primary">
            看這裡的全部 {{ formatCount(shelter.all.count) }} 隻動物
            <LucideIcon name="arrow-right" :size="16" />
          </RouterLink>
          <RouterLink v-if="shelter.狗.count" :to="animalsLink({ shelter: shelter.id, kind: '狗' })" class="cta">
            <LucideIcon name="dog" :size="16" /> 只看狗 {{ formatCount(shelter.狗.count) }}
          </RouterLink>
          <RouterLink v-if="shelter.貓.count" :to="animalsLink({ shelter: shelter.id, kind: '貓' })" class="cta">
            <LucideIcon name="cat" :size="16" /> 只看貓 {{ formatCount(shelter.貓.count) }}
          </RouterLink>
          <RouterLink
            v-if="overTwoYears"
            :to="animalsLink({ shelter: shelter.id, daysFrom: '2-5y' })"
            class="cta"
          >
            已在所 2 年以上 {{ formatCount(overTwoYears) }}
          </RouterLink>
        </div>
      </section>

      <section class="sect" aria-labelledby="s-contact">
        <div class="sect-head">
          <span class="sect-icon" aria-hidden="true"><LucideIcon name="map-pinned" :size="20" /></span>
          <div class="sect-title">
            <h2 id="s-contact">聯絡與位置</h2>
            <p>地址與電話來自原始資料；地圖由 Google 依地址定位，入口請以現場指標為準。</p>
          </div>
        </div>

        <div class="intro">
          <section class="panel contact" aria-label="聯絡方式">
            <div class="crow">
              <LucideIcon name="map-pin" :size="18" />
              <div>
                <span class="k">
                  地址<template v-if="addresses.length > 1">（來源資料登錄了 {{ addresses.length }} 個地點，全部列出）</template>
                </span>
                <span v-for="address in addresses" :key="address.text" class="v" :title="`原始資料：${address.raw}`">
                  {{ address.text }}
                </span>
              </div>
            </div>
            <div class="crow">
              <LucideIcon name="phone" :size="18" />
              <div>
                <span class="k">電話</span>
                <a v-if="phone?.href" class="tel" :href="phone.href">{{ phone.text }}</a>
                <span v-else class="v missing">電話欄位不完整（原始資料：{{ shelter.tel }}）</span>
                <span v-if="phone?.href" class="sub">手機點一下即可撥號</span>
              </div>
            </div>
            <div class="callout">
              <b>本站不辦理認養。</b>資料每天更新一次，名單上的動物可能已經被認養；開放時間、預約方式與認養規定，請以收容所現場公告為準。
            </div>
          </section>

          <section v-if="primary" class="panel mapcard">
            <div v-if="embed" class="mapframe">
              <iframe
                :title="`${shelter.name}位置地圖`"
                :src="embed"
                loading="lazy"
                referrerpolicy="no-referrer-when-downgrade"
                allowfullscreen
              />
            </div>
            <div v-else class="mapframe empty">
              <LucideIcon name="map-pin" :size="28" />
              <span>點下方連結，在 Google 地圖查看這間收容所的位置。</span>
            </div>
            <div class="mapbar">
              <span>
                地圖依{{ primary.coords ? '原始資料的座標' : '地址文字' }}由 Google 定位，入口位置請以現場指標為準。
              </span>
              <span class="maplinks">
                <a :href="mapOpenUrl(primary)" target="_blank" rel="noreferrer">
                  在 Google 地圖開啟 <LucideIcon name="external-link" :size="14" />
                </a>
                <a
                  v-for="(address, index) in addresses.slice(1)"
                  :key="address.text"
                  :href="mapOpenUrl(address)"
                  target="_blank"
                  rel="noreferrer"
                >
                  第 {{ index + 2 }} 個地點 <LucideIcon name="external-link" :size="14" />
                </a>
              </span>
            </div>
          </section>
        </div>
      </section>

      <!-- Numbers and the distribution share one block: the card on the left
           gives the totals, the chart on the right shows how they spread. -->
      <section class="sect" aria-labelledby="s-status">
        <div class="sect-head">
          <span class="sect-icon" aria-hidden="true"><LucideIcon name="chart-column" :size="20" /></span>
          <div class="sect-title">
            <h2 id="s-status">收容動物現況</h2>
            <p>全部只計算目前仍在所的動物；滯留中位數旁附上全臺的數字作對照。</p>
          </div>
        </div>

        <div class="status">
          <dl class="panel stats">
            <div class="stat lead">
              <dt>在所總數</dt>
              <dd>
                <b>{{ formatCount(shelter.all.count) }}<small>隻</small></b>
                <em>全臺第 {{ rank }} 多</em>
              </dd>
            </div>
            <div class="stat">
              <dt>狗</dt>
              <dd>
                <b>{{ formatCount(shelter.狗.count) }}<small>隻</small></b>
                <em>佔 {{ share(shelter.狗.count) }}</em>
              </dd>
            </div>
            <div class="stat">
              <dt>貓</dt>
              <dd>
                <b>{{ formatCount(shelter.貓.count) }}<small>隻</small></b>
                <em>佔 {{ share(shelter.貓.count) }}</em>
              </dd>
            </div>
            <div class="stat accent">
              <dt>滯留中位數</dt>
              <dd>
                <b>{{ shelter.all.median_days === null ? '—' : formatCount(shelter.all.median_days) }}<small>天</small></b>
                <em v-if="nationalMedian !== null">全臺為 {{ formatCount(nationalMedian) }} 天</em>
              </dd>
            </div>
            <div class="stat">
              <dt>最長滯留</dt>
              <dd>
                <b>{{ shelter.all.max_days === null ? '—' : formatCount(shelter.all.max_days) }}<small>天</small></b>
                <em v-if="shelter.all.max_days">約 {{ (shelter.all.max_days / 365).toFixed(1) }} 年</em>
              </dd>
            </div>
          </dl>

          <div class="panel dist">
            <div class="dist-head">
              <div>
                <h3 id="s-dist">在所時間分布</h3>
                <p>七個區間各有幾隻，可以切換只看狗或只看貓。</p>
              </div>
              <div class="pills" role="group" aria-label="動物類型">
                <button
                  v-for="option in SCOPES"
                  :key="option.id"
                  type="button"
                  class="pill-btn"
                  :aria-pressed="scope === option.id"
                  :disabled="option.id !== 'all' && shelter[option.id].count === 0"
                  @click="scope = option.id"
                >
                  {{ option.label }}
                </button>
              </div>
            </div>
            <ShelterSpark :histogram="histogram" :labels="labels" large />
            <p class="dist-note">
              只算得出目前仍在所的動物，已被認養或離所的不在資料裡，所以這張圖看不出這間收容所的認養速度。
            </p>
          </div>
        </div>
      </section>

      <section class="boundary">
        <div class="boundary-head">
          <span class="kicker">這一頁不能拿來說什麼</span>
          <span class="pill">資料快照 {{ snapshotDate }}</span>
        </div>
        <ul>
          <li>在所動物多不代表這間收容所做得比較差。收容量、腹地與所轄範圍差距很大，這一頁不做收容所之間的評比。</li>
          <li>「滯留中位數」與分布只包含<strong>目前仍在所</strong>的動物，看不出認養速度。</li>
          <li>地址與電話直接來自原始資料；地圖位置由 Google 依地址文字解析，不是本站量測的座標。</li>
        </ul>
      </section>
    </template>

    <AnimalDialog
      v-if="openAnimal && shelter"
      :animal="openAnimal"
      :snapshot-date="snapshotDate"
      :shelter="shelter"
      @close="close"
    />
  </div>
</template>

<style scoped>
.state {
  padding: 3rem 0;
  color: var(--ink-muted);
}

.crumb {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  width: fit-content;
  margin-bottom: 1rem;
  color: var(--ink-secondary);
  font-size: 0.88rem;
  text-decoration: none;
}

.crumb:hover {
  color: var(--ink);
}

/* ── Head ── */
.head h1 {
  font-size: clamp(1.6rem, 3.4vw, 2.2rem);
}

.head p {
  margin: 0.6rem 0 0;
  color: var(--ink-secondary);
}

.stamp {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.05rem 0.6rem;
  border-radius: 999px;
  background: var(--surface-sunk);
  color: var(--ink-muted);
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* ── Section heads and rules ── */
.sect {
  padding-top: 2.25rem;
}

.sect + .sect {
  margin-top: 2.75rem;
  border-top: 1px solid var(--hairline);
}

.sect-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.4rem 1rem;
}

.sect-icon {
  display: grid;
  flex-shrink: 0;
  place-items: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: var(--radius-sm);
  background: var(--surface-sunk);
  color: var(--accent-text);
}

.sect-title {
  flex: 1 1 18rem;
  min-width: 0;
}

.sect-title h2 {
  font-size: 1.35rem;
}

.sect-title p {
  max-width: 46rem;
  margin: 0.25rem 0 0;
  color: var(--ink-secondary);
  font-size: 0.9rem;
}

.sect-link {
  align-self: center;
  margin-left: auto;
}

a.sect-link {
  color: var(--accent-text);
  font-size: 0.9rem;
  white-space: nowrap;
  text-decoration: none;
}

a.sect-link:hover {
  text-decoration: underline;
}

.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 2rem 1.5rem;
  margin-top: 1.5rem;
}

.cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 1.25rem;
}

.cta {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.6rem 1.2rem;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: var(--surface);
  color: var(--ink);
  font-size: 0.9rem;
  font-variant-numeric: tabular-nums;
  text-decoration: none;
}

.cta:hover {
  border-color: var(--ramp-3);
}

.cta.primary {
  border-color: var(--ramp-4);
  background: var(--ramp-4);
  color: var(--on-accent);
  font-weight: 500;
}

/* ── Contact and map ── */
.intro {
  display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
  align-items: stretch;
  gap: 1.25rem;
  margin-top: 1.25rem;
}

.panel {
  padding: 1.4rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
}

.contact {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.crow {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
}

.crow > svg {
  flex-shrink: 0;
  margin-top: 0.25rem;
  color: var(--accent-text);
}

.crow .k {
  display: block;
  color: var(--ink-muted);
  font-size: 0.78rem;
}

.crow .v {
  display: block;
  font-size: 0.98rem;
}

.crow .v + .v {
  margin-top: 0.35rem;
}

.crow .missing {
  color: var(--ink-muted);
}

.crow .sub {
  display: block;
  margin-top: 0.15rem;
  color: var(--ink-muted);
  font-size: 0.8rem;
}

.tel {
  color: var(--ink);
  font-size: 1.15rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-decoration: none;
}

.tel:hover {
  color: var(--accent-text);
}

.callout {
  margin-top: auto;
  padding: 0.9rem 1rem;
  border-radius: var(--radius-sm);
  background: var(--surface-sunk);
  color: var(--ink-secondary);
  font-size: 0.86rem;
}

.callout b {
  color: var(--ink);
}

.mapcard {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.mapframe {
  position: relative;
  flex: 1;
  min-height: 340px;
  background: var(--surface-sunk);
}

.mapframe iframe {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 340px;
  border: 0;
}

.mapframe.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  padding: 1.5rem;
  color: var(--ink-muted);
  font-size: 0.86rem;
  text-align: center;
}

.mapbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem 1rem;
  padding: 0.8rem 1.1rem;
  border-top: 1px solid var(--hairline);
  color: var(--ink-muted);
  font-size: 0.82rem;
}

.maplinks {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1rem;
}

.maplinks a {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--accent-text);
  font-weight: 500;
  white-space: nowrap;
  text-decoration: none;
}

/* ── Status: numbers card + distribution ── */
.status {
  display: grid;
  grid-template-columns: minmax(0, 4fr) minmax(0, 8fr);
  align-items: stretch;
  gap: 1.25rem;
  margin-top: 1.25rem;
}

.stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  gap: 1.1rem 1rem;
  margin: 0;
}

.stat.lead {
  grid-column: 1 / -1;
  padding-bottom: 1.1rem;
  border-bottom: 1px solid var(--hairline);
}

.stat dt {
  color: var(--ink-muted);
  font-size: 0.78rem;
}

.stat dd {
  margin: 0;
}

.stat b {
  display: block;
  font-size: 1.5rem;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}

.stat.lead b {
  font-size: 2.2rem;
  line-height: 1.2;
}

.stat b small {
  margin-left: 0.15rem;
  color: var(--ink-secondary);
  font-size: 0.8rem;
  font-weight: 400;
}

.stat em {
  display: block;
  color: var(--ink-secondary);
  font-size: 0.78rem;
  font-style: normal;
  font-variant-numeric: tabular-nums;
}

.stat.accent b {
  color: var(--accent-text);
}

.dist {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dist-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.6rem 1rem;
}

.dist-head h3 {
  font-size: 1.02rem;
}

.dist-head p {
  margin: 0.15rem 0 0;
  color: var(--ink-muted);
  font-size: 0.84rem;
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
  cursor: pointer;
}

.pill-btn:hover:not(:disabled) {
  border-color: var(--ramp-3);
  color: var(--ink);
}

.pill-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.pill-btn[aria-pressed='true'] {
  border-color: var(--ramp-4);
  background: var(--ramp-4);
  color: var(--on-accent);
}

.dist-note {
  margin: auto 0 0;
  color: var(--ink-muted);
  font-size: 0.84rem;
}

/* ── Boundary card ── */
.boundary {
  margin-top: 3.5rem;
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

.pill {
  padding: 0.12rem 0.75rem;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: var(--surface);
  font-size: 0.84rem;
  font-variant-numeric: tabular-nums;
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

@media (max-width: 1000px) {
  .intro {
    grid-template-columns: 1fr;
  }

  .status {
    grid-template-columns: 1fr;
  }

  /* One row of five while the card has the full width. */
  .stats {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .stat.lead {
    grid-column: auto;
    padding-bottom: 0;
    border-bottom: 0;
  }

  .stat.lead b {
    font-size: 1.5rem;
    line-height: 1.3;
  }
}

@media (max-width: 820px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stat.lead {
    grid-column: 1 / -1;
    padding-bottom: 1.1rem;
    border-bottom: 1px solid var(--hairline);
  }

  .stat.lead b {
    font-size: 2rem;
    line-height: 1.2;
  }

  .mapframe,
  .mapframe iframe {
    min-height: 260px;
  }
}
</style>
