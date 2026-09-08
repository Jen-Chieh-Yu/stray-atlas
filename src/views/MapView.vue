<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import CountyChoropleth from '@/components/CountyChoropleth.vue'
import { fetchShelterPoints, useAtlasData } from '@/composables/useAtlasData'
import type { CountyStats, KindFilter, Metric, ShelterPoint } from '@/types'

const { stats, shapes, loading, error, reload } = useAtlasData()
const router = useRouter()

const hovered = ref<string | null>(null)
const selected = ref<string | null>(null)

const points = ref<ShelterPoint[]>([])
const showPoints = ref(true)
const manualCount = computed(() => points.value.filter((p) => p.manual).length)

onMounted(async () => {
  try {
    points.value = (await fetchShelterPoints()).points
  } catch {
    // The choropleth is the page; markers are an overlay. A failed fetch
    // hides the layer rather than taking the map down with it.
    points.value = []
  }
})

function goToShelterPage(id: string) {
  void router.push({ name: 'shelter', params: { id } })
}

/* --------------------------------------------------------------- the rail --
 * One panel over the map's left edge, in one of four states. A map has one
 * place for "what am I looking at", and splitting it across a column beside
 * the map and a panel on top of it would mean two.
 */
type RailView = 'closed' | 'list' | 'county' | 'shelter'
const rail = ref<RailView>('closed')
const activeShelter = ref<ShelterPoint | null>(null)
const ascending = ref(false)

const scopedShelters = computed(() => {
  const scope = selected.value
    ? points.value.filter((p) => p.county === selected.value)
    : points.value
  const sorted = [...scope].sort((a, b) => b.count - a.count)
  return ascending.value ? sorted.reverse() : sorted
})

const maxShelterCount = computed(() => Math.max(1, ...scopedShelters.value.map((p) => p.count)))

function openList() {
  selected.value = null
  activeShelter.value = null
  rail.value = rail.value === 'list' ? 'closed' : 'list'
}

/** A click on the map, resolved against what the panel is showing.
 *
 *  Clicking the county whose panel is already open closes it. Clicking any
 *  other county - including the one a currently open shelter card happens to
 *  belong to - opens that county. The map cannot make this call itself,
 *  because it only knows which county is highlighted, not which of the four
 *  panel states put it there. */
function onCountyClick(name: string | null) {
  if (!name || (rail.value === 'county' && selected.value === name)) {
    closeRail()
    return
  }
  openCounty(name)
}

function openCounty(name: string | null) {
  selected.value = name
  activeShelter.value = null
  rail.value = name ? 'county' : 'closed'
}

function openShelterCard(shelter: ShelterPoint) {
  activeShelter.value = shelter
  rail.value = 'shelter'
}

function openShelterById(id: string) {
  const point = points.value.find((p) => p.id === id)
  if (!point) return
  // A pin belongs to a county, so its back arrow should lead there.
  selected.value = point.county
  openShelterCard(point)
}

function railBack() {
  activeShelter.value = null
  rail.value = selected.value ? 'county' : 'list'
}

function closeRail() {
  selected.value = null
  activeShelter.value = null
  rail.value = 'closed'
}

/** The panel follows the lock, not the cursor: one that opened on hover would
 *  flicker across the whole map on the way to the county. */
const locked = computed(
  () => stats.value?.counties.find((county) => county.name === selected.value) ?? null,
)

const metric = ref<Metric>('count')
const kind = ref<KindFilter>('all')

const METRICS: { id: Metric; label: string }[] = [
  { id: 'count', label: '在所數' },
  { id: 'median', label: '滯留中位數' },
]
const KINDS: { id: KindFilter; label: string }[] = [
  { id: 'all', label: '全部' },
  { id: '狗', label: '狗' },
  { id: '貓', label: '貓' },
]

function summaryOf(county: CountyStats) {
  return kind.value === 'all' ? county.all : county[kind.value]
}

function valueOf(county: CountyStats): number | null {
  const summary = summaryOf(county)
  if (metric.value === 'count') return summary.count
  // A median over a handful of animals is noise, not a signal.
  return summary.count >= 20 ? summary.median_days : null
}

const rows = computed(() => {
  if (!stats.value) return []
  return stats.value.counties
    .map((county) => ({ county, value: valueOf(county) }))
    .sort((a, b) => (b.value ?? -1) - (a.value ?? -1))
})

const values = computed(() => new Map(rows.value.map((row) => [row.county.name, row.value])))
const counts = computed(
  () => new Map((stats.value?.counties ?? []).map((county) => [county.name, county.all.count])),
)
/** Five cut points, six classes, by quantile.
 *  Equal-interval would put eighteen counties in the lightest class, because
 *  新北市 holds a third of every animal in the country. */
const breaks = computed(() => {
  const sorted = rows.value
    .map((row) => row.value)
    .filter((value): value is number => value !== null)
    .sort((a, b) => a - b)
  if (sorted.length < 6) return []
  return [1, 2, 3, 4, 5].map((i) => sorted[Math.floor((sorted.length * i) / 6)])
})

const legendBands = computed(() => {
  if (!breaks.value.length) return []
  const unit = metric.value === 'count' ? '' : ' 天'
  const cuts = breaks.value
  return cuts
    .map((cut, index) => ({
      step: index + 1,
      label:
        index === 0
          ? `< ${cut.toLocaleString('zh-TW')}${unit}`
          : `${cuts[index - 1].toLocaleString('zh-TW')}–${cut.toLocaleString('zh-TW')}${unit}`,
    }))
    .concat([{ step: 6, label: `≥ ${cuts[cuts.length - 1].toLocaleString('zh-TW')}${unit}` }])
})

function share(part: number, whole: number): string {
  return whole === 0 ? '0%' : `${((part / whole) * 100).toFixed(1)}%`
}

const shelterCount = computed(() =>
  (stats.value?.counties ?? []).reduce((total, county) => total + county.shelters, 0),
)

function years(days: number | null): string {
  return days === null ? '' : `約 ${(days / 365).toFixed(1)} 年`
}

/** Three bands rather than a bare percentage. 1.1% and 95.1% are the real
 *  extremes across counties, and the number alone does not tell a reader that
 *  the low end means "this county records street names only". */
function coverageNote(value: number): string {
  if (value >= 0.7) return '登錄大致完整'
  if (value >= 0.3) return '登錄不一致'
  return '登錄極不完整'
}
</script>

<template>
  <div>
    <p v-if="loading" class="state">載入中…</p>

    <p v-else-if="error" class="state">
      資料載入失敗（{{ error }}）。
      <button type="button" @click="reload">重試</button>
    </p>

    <template v-else-if="stats && shapes">
      <div class="controls">
        <fieldset>
          <legend>顯示指標</legend>
          <button
            v-for="option in METRICS"
            :key="option.id"
            type="button"
            :class="{ chip: true, on: metric === option.id }"
            :aria-pressed="metric === option.id"
            @click="metric = option.id"
          >
            {{ option.label }}
          </button>
        </fieldset>

        <fieldset>
          <legend>動物類型</legend>
          <button
            v-for="option in KINDS"
            :key="option.id"
            type="button"
            :class="{ chip: true, on: kind === option.id }"
            :aria-pressed="kind === option.id"
            @click="kind = option.id"
          >
            {{ option.label }}
          </button>
        </fieldset>

        <fieldset v-if="points.length">
          <legend>圖層</legend>
          <button
            type="button"
            :class="{ chip: true, on: showPoints }"
            :aria-pressed="showPoints"
            @click="showPoints = !showPoints"
          >
            收容所圖釘
          </button>
        </fieldset>
      </div>

      <div class="kpis">
        <div>
          <p class="kpi-label">全國在所總數</p>
          <p class="kpi-value">{{ stats.total.count.toLocaleString('zh-TW') }} <span>隻</span></p>
        </div>
        <div>
          <p class="kpi-label">全臺滯留中位數</p>
          <p class="kpi-value">
            {{ stats.total.median_days?.toLocaleString('zh-TW') ?? '—' }} <span>天</span>
            <span class="kpi-sub">{{ years(stats.total.median_days) }}</span>
          </p>
        </div>
        <div>
          <p class="kpi-label">公立收容所涵蓋</p>
          <p class="kpi-value">{{ shelterCount }} <span>處設施</span></p>
        </div>
        <div class="minor">
          <p class="kpi-label">全臺平均滯留</p>
          <p class="kpi-value">
            {{ stats.total.mean_days?.toLocaleString('zh-TW') ?? '—' }} <span>天</span>
            <span class="kpi-sub">{{ years(stats.total.mean_days) }}</span>
          </p>
        </div>
        <div class="minor">
          <p class="kpi-label">全臺最長滯留</p>
          <p class="kpi-value accent">
            {{ stats.total.max_days?.toLocaleString('zh-TW') ?? '—' }} <span>天</span>
            <span class="kpi-sub">{{ years(stats.total.max_days) }}</span>
          </p>
        </div>
        <p class="kpi-note">
          中位數是這裡該讀的數字。平均比中位數高出一倍以上，是因為這份資料只含尚未離所的動物，
          待越久的越可能留在其中；最長滯留是單一個體，不是趨勢。
        </p>
      </div>

      <div class="layout">
        <section class="card map-card">
          <div class="card-head">
            <h2><span class="dot" aria-hidden="true" />臺灣縣市分佈地圖</h2>
            <span class="hint">點選縣市或圖釘</span>
          </div>

          <div class="map-shell">
            <div class="map-frame" :class="{ shifted: rail !== 'closed' }">
            <CountyChoropleth
            :shapes="shapes"
            :values="values"
            :breaks="breaks"
            :counts="counts"
            :selected="selected"
            :points="points"
            :show-points="showPoints && points.length > 0"
            @hover="hovered = $event"
            @select="onCountyClick($event)"
            @open-shelter="openShelterById"
            />
            </div>

            <!-- One rail, four states. Google Maps' left panel: what you
                 clicked opens where you are looking. -->
            <button
              v-if="rail === 'closed'"
              type="button"
              class="rail-open"
              @click="openList"
            >
              全臺收容所在所數
            </button>

            <transition name="slide">
              <aside v-if="rail !== 'closed'" class="rail" aria-live="polite">
                <div class="rail-head">
                  <button
                    v-if="rail === 'shelter'"
                    type="button"
                    class="rail-icon"
                    aria-label="返回"
                    @click="railBack"
                  >
                    ‹
                  </button>
                  <div class="rail-title">
                    <template v-if="rail === 'shelter' && activeShelter">
                      <h2 class="detail-name">{{ activeShelter.name }}</h2>
                      <p class="detail-sub">
                        {{ activeShelter.county }}{{ activeShelter.district }}
                      </p>
                    </template>
                    <template v-else-if="rail === 'county' && locked">
                      <h2 class="detail-name">{{ locked.name }}</h2>
                      <p class="detail-sub">{{ locked.shelters }} 間公立收容所</p>
                    </template>
                    <template v-else>
                      <h2 class="detail-name">全臺收容所在所數</h2>
                      <p class="detail-sub">{{ scopedShelters.length }} 處</p>
                    </template>
                  </div>
                  <button type="button" class="rail-icon" aria-label="關閉" @click="closeRail">
                    ✕
                  </button>
                </div>

                <!-- county summary -->
                <template v-if="rail === 'county' && locked">
                  <div class="stats">
                    <div>
                      <p class="stat-label">在所總數</p>
                      <p class="stat-value">
                        {{ locked.all.count.toLocaleString('zh-TW') }} <span>隻</span>
                      </p>
                    </div>
                    <div>
                      <p class="stat-label">滯留中位數</p>
                      <p class="stat-value accent">
                        {{ locked.all.median_days?.toLocaleString('zh-TW') ?? '—' }} <span>天</span>
                      </p>
                      <p class="stat-sub">{{ years(locked.all.median_days) }}</p>
                    </div>
                  </div>
                  <div class="spread">
                    <div>
                      <p class="stat-label">平均滯留</p>
                      <p class="spread-value">
                        {{ locked.all.mean_days?.toLocaleString('zh-TW') ?? '—' }} 天
                      </p>
                    </div>
                    <div>
                      <p class="stat-label">最長滯留</p>
                      <p class="spread-value">
                        {{ locked.all.max_days?.toLocaleString('zh-TW') ?? '—' }} 天
                      </p>
                    </div>
                  </div>
                  <p class="species">
                    狗：{{ locked.狗.count.toLocaleString('zh-TW') }}
                    <span>{{ share(locked.狗.count, locked.all.count) }}</span>
                    ・貓：{{ locked.貓.count.toLocaleString('zh-TW') }}
                    <span>{{ share(locked.貓.count, locked.all.count) }}</span>
                  </p>
                  <div class="coverage">
                    <span>尋獲地行政區級別比例</span>
                    <span class="coverage-badge">
                      {{ (locked.district_coverage * 100).toFixed(1) }}%（{{
                        coverageNote(locked.district_coverage)
                      }}）
                    </span>
                  </div>
                </template>

                <!-- one shelter -->
                <template v-else-if="rail === 'shelter' && activeShelter">
                  <div class="stats">
                    <div>
                      <p class="stat-label">在所數</p>
                      <p class="stat-value">
                        {{ activeShelter.count.toLocaleString('zh-TW') }} <span>隻</span>
                      </p>
                    </div>
                    <div>
                      <p class="stat-label">滯留中位數</p>
                      <p class="stat-value accent">
                        {{ activeShelter.median_days?.toLocaleString('zh-TW') ?? '—' }}
                        <span>天</span>
                      </p>
                      <p class="stat-sub">{{ years(activeShelter.median_days) }}</p>
                    </div>
                  </div>
                  <div class="spread">
                    <div>
                      <p class="stat-label">平均滯留</p>
                      <p class="spread-value">
                        {{ activeShelter.mean_days?.toLocaleString('zh-TW') ?? '—' }} 天
                      </p>
                    </div>
                    <div>
                      <p class="stat-label">最長滯留</p>
                      <p class="spread-value">
                        {{ activeShelter.max_days?.toLocaleString('zh-TW') ?? '—' }} 天
                      </p>
                    </div>
                  </div>
                  <p class="species">
                    狗：{{ activeShelter.dogs.toLocaleString('zh-TW') }}
                    <span>{{ share(activeShelter.dogs, activeShelter.count) }}</span>
                    ・貓：{{ activeShelter.cats.toLocaleString('zh-TW') }}
                    <span>{{ share(activeShelter.cats, activeShelter.count) }}</span>
                  </p>
                  <p v-for="address in activeShelter.addresses" :key="address" class="rail-line">
                    {{ address }}
                  </p>
                  <p v-if="activeShelter.tel" class="rail-line">
                    <a :href="`tel:${activeShelter.tel}`">{{ activeShelter.tel }}</a>
                  </p>
                  <button
                    type="button"
                    class="chip on rail-cta"
                    @click="goToShelterPage(activeShelter.id)"
                  >
                    查看這間收容所的動物
                  </button>
                </template>

                <!-- the ranked list, national or scoped to the county -->
                <template v-if="rail !== 'shelter'">
                  <div class="rail-tools">
                    <span class="rail-tools-label">
                      {{ rail === 'county' ? '所內收容所' : '依在所數' }}
                    </span>
                    <button
                      type="button"
                      class="chip small"
                      :aria-pressed="ascending"
                      @click="ascending = !ascending"
                    >
                      {{ ascending ? '由少到多 ↑' : '由多到少 ↓' }}
                    </button>
                  </div>

                  <ol class="shelters">
                    <li
                      v-for="shelter in scopedShelters"
                      :key="shelter.id"
                      class="shelter-row"
                    >
                      <button
                        type="button"
                        class="shelter-hit"
                        @click="openShelterCard(shelter)"
                      >
                        <span class="shelter-name">{{ shelter.name }}</span>
                        <span class="shelter-count">
                          {{ shelter.count.toLocaleString('zh-TW') }}
                        </span>
                        <span class="shelter-meta">
                          {{ shelter.county }}{{ shelter.district }}・中位數
                          {{ shelter.median_days?.toLocaleString('zh-TW') ?? '—' }} 天
                        </span>
                        <span
                          class="shelter-bar"
                          :style="{ width: `${(shelter.count / maxShelterCount) * 100}%` }"
                        />
                      </button>
                    </li>
                  </ol>
                </template>
              </aside>
            </transition>
          </div>

          <p v-if="showPoints && points.length" class="pin-note">
            圖釘標示 {{ points.length }} 處公立收容所，數字為在所隻數，位置為該所所在<strong>行政區</strong>的形心而非門牌；其中 {{ manualCount }} 處的行政區由地址人工判定。點擊圖釘進入該所的動物列表；滾輪縮放、拖曳平移；點選縣市開啟左側面板，連點兩下才會把鏡頭框過去。
          </p>

          <div class="legend">
            <div class="legend-head">
              <span class="legend-title">
                分位數色階級距（{{ metric === 'count' ? '在所數' : '滯留中位數' }}）
              </span>
              <span class="legend-unit">單位：{{ metric === 'count' ? '隻' : '天' }}</span>
            </div>
            <ul>
              <li v-for="band in legendBands" :key="band.step">
                <span class="swatch" :style="{ background: `var(--ramp-${band.step})` }" />
                {{ band.label }}
              </li>
              <li v-if="metric === 'median'">
                <span class="swatch" :style="{ background: 'var(--no-data)' }" />
                樣本不足 20 隻
              </li>
            </ul>
            <p class="legend-note">分位數分級染色，非等距——新北市一縣即佔全國三分之一。</p>
          </div>
        </section>

      </div>

      <section class="card caveats">
        <h2><span class="mark" aria-hidden="true">ⓘ</span> 這張圖不能拿來說什麼（數據判讀邊界）</h2>
        <p class="caveats-intro">
          本平臺資料完全取自農業部公立動物收容系統的即時快照。在把地理分布當成政策討論或倡議依據之前，必須先理解以下三項登錄結構上的限制：
        </p>

        <ol class="notes">
          <li class="note-card">
            <p class="note-no">01</p>
            <h3>縣市＝收容所所在地，不等於動物尋獲地</h3>
            <p>
              尋獲地欄位只有 2.4% 自己寫出縣市，而其中有 6% 與收容縣市不同，部分登錄者甚至直接寫「外縣市」。
              地圖上的顏色反映的是該縣市硬體設施收了多少動物，不是那裡有多少流浪動物。
            </p>
          </li>
          <li class="note-card">
            <p class="note-no">02</p>
            <h3>滯留天數只計算「目前仍在所」的動物</h3>
            <p>
              已經認養、死亡或回置的個體完全不在這份資料裡。待越久的動物越可能留在快照中，因此中位數與平均值都必然被長期滯留者拉高——全國中位數 348 天，平均卻是 858 天，兩者差距本身就是這個偏誤的證據。不能讀成「一隻動物平均多久會被認養」。
            </p>
          </li>
          <li class="note-card">
            <p class="note-no">03</p>
            <h3>在所總量（存量）不等於流動率（流量）</h3>
            <p>
              高在所數可能來自收容空間充裕、零撲殺後的長期安置；低在所數也可能是硬體已滿而嚴格控管入所。存量是入所與離所速率的差，無法單憑色階推論地方主管機關的作為。
            </p>
          </li>
        </ol>

        <div class="caveats-foot">
          <span>資料快照基準日：{{ stats.snapshot_date }}·農業部公立動物收容開放資料集</span>
          <span>StrayAtlas 開放分析原則</span>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.state {
  padding: 3rem 0;
  color: var(--ink-secondary);
}

.controls {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 1.75rem;
  margin-bottom: 1.25rem;
}

fieldset {
  border: 0;
  margin: 0;
  padding: 0;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

legend {
  float: left;
  margin-right: 0.65rem;
  font-size: 0.85rem;
  color: var(--ink-muted);
}

/* Three tiles rather than three sentences: these are the numbers a reader
   wants before they touch a control, and a hero row states them once so the
   map does not have to be interrogated for them. */
.kpis {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 1px;
  background: var(--hairline);
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 1.25rem;
}

.kpis > div {
  grid-column: span 2;
  background: var(--surface);
  padding: 0.9rem 1.25rem;
}

.kpis > div.minor {
  grid-column: span 3;
}

.kpi.minor .kpi-value,
.kpis > div.minor .kpi-value {
  font-size: 1.15rem;
}

.kpi-label {
  margin: 0 0 0.15rem;
  font-size: 0.8rem;
  color: var(--ink-muted);
}

.kpi-value {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.kpi-value span {
  font-size: 0.85rem;
  font-weight: 400;
  color: var(--ink-secondary);
}

.kpi-sub {
  margin-left: 0.35rem;
  color: var(--ink-muted) !important;
}

.kpi-value.accent {
  color: var(--accent-text);
}

.kpi-note {
  grid-column: 1 / -1;
  background: var(--surface);
  margin: 0;
  padding: 0.75rem 1.25rem;
  font-size: 0.8rem;
  line-height: 1.7;
  color: var(--ink-muted);
}

/* Wide enough for all five, and one unbroken row reads faster than two:
   the eye crosses it once instead of resetting. Below this the primary
   three keep the top line and the two context figures drop beneath. */
@media (min-width: 1180px) {
  .kpis {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .kpis > div,
  .kpis > div.minor {
    grid-column: span 1;
  }
}

@media (max-width: 760px) {
  .kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .kpis > div,
  .kpis > div.minor {
    grid-column: span 1;
  }

  /* Five tiles over two columns leaves the last one alone; let it run
     the full width rather than sitting beside an empty cell. */
  .kpis > div:last-of-type {
    grid-column: span 2;
  }
}

.pin-note {
  margin: 0.7rem 0 0;
  font-size: 0.78rem;
  line-height: 1.8;
  color: var(--ink-muted);
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.9rem;
}

.card-head h2 {
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--ramp-4);
  display: inline-block;
}

.hint {
  font-size: 0.78rem;
  color: var(--ink-muted);
  white-space: nowrap;
}

/* One column. Everything the old right-hand column carried now lives in the
   rail over the map, so the map takes the whole width and the page has one
   subject rather than two competing for the row. */
.layout {
  display: grid;
  gap: 1.25rem;
}

.map-shell {
  position: relative;
}

/* The map is centred while the rail is closed and steps aside when it opens.
   Padding on an inner frame, not on the shell: the rail is absolutely
   positioned against the shell's padding box, so padding there would carry the
   rail along with the map and defeat the whole point.

   The drawing is letterboxed inside a full-width element, so on a wide screen
   this eats the dead space and the map does not shrink — it only moves. */
.map-frame {
  padding-left: 0;
  transition: padding-left 220ms cubic-bezier(0.22, 0.61, 0.36, 1);
}

.map-frame.shifted {
  padding-left: min(21rem, 92%);
}

/* Full width would make a 560×588 viewBox over 1,200px tall on a desktop. The
   cap letterboxes it instead. */
.map-shell :deep(svg.map) {
  max-height: 74vh;
}

/* Slides in over the map's left edge. Absolute rather than in the flow, so
   opening it does not reflow the map underneath and move the county the
   reader just clicked. */
.rail {
  position: absolute;
  left: 0;
  top: 0;
  width: min(21rem, 92%);
  max-height: 100%;
  overflow-y: auto;
  padding: 0.9rem 1rem 1.1rem;
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  box-shadow: 0 10px 30px rgb(0 0 0 / 12%);
  z-index: 2;
}

.rail-open {
  position: absolute;
  left: 0;
  top: 0;
  z-index: 2;
  font: inherit;
  font-size: 0.85rem;
  padding: 0.45rem 0.9rem;
  border-radius: 999px;
  border: 1px solid var(--hairline);
  background: var(--surface);
  color: var(--ink-secondary);
  cursor: pointer;
  box-shadow: 0 4px 14px rgb(0 0 0 / 8%);
}

.rail-open:hover {
  border-color: var(--ramp-3);
  color: var(--ink);
}

.slide-enter-active,
.slide-leave-active {
  transition:
    transform 220ms cubic-bezier(0.22, 0.61, 0.36, 1),
    opacity 180ms ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(-102%);
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .map-frame {
    transition: none;
  }

  .slide-enter-active,
  .slide-leave-active {
    transition: opacity 120ms ease;
  }

  .slide-enter-from,
  .slide-leave-to {
    transform: none;
  }
}

.rail-head {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.85rem;
}

.rail-title {
  flex: 1;
  min-width: 0;
}

.rail-icon {
  font: inherit;
  font-size: 0.95rem;
  line-height: 1;
  padding: 0.3rem 0.5rem;
  border-radius: 8px;
  border: 1px solid var(--hairline);
  background: var(--surface);
  color: var(--ink-muted);
  cursor: pointer;
}

.rail-icon:hover {
  border-color: var(--ramp-3);
  color: var(--ink);
}

/* The shared .stats grid is three columns for the old side card; the rail
   carries two and would otherwise leave each one a third of a narrow panel. */
.rail .stats,
.rail .spread {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.rail .stat-value,
.rail .spread-value {
  white-space: nowrap;
}

.rail .species {
  margin: 0.7rem 0 0;
  font-size: 0.82rem;
  color: var(--ink-secondary);
}

.rail-line {
  margin: 0.4rem 0 0;
  font-size: 0.8rem;
  color: var(--ink-muted);
  word-break: break-all;
}

.rail-cta {
  margin-top: 0.9rem;
  width: 100%;
}

.rail-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  margin: 1rem 0 0.2rem;
  padding-top: 0.8rem;
  border-top: 1px solid var(--hairline);
}

.rail-tools-label {
  font-size: 0.78rem;
  color: var(--ink-muted);
}

.shelters {
  list-style: none;
  margin: 0;
  padding: 0;
}

.shelter-row + .shelter-row {
  border-top: 1px solid var(--hairline);
}

.shelter-hit {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-rows: auto auto auto;
  gap: 0.1rem 0.6rem;
  width: 100%;
  padding: 0.5rem 0;
  border: 0;
  background: none;
  font: inherit;
  text-align: left;
  cursor: pointer;
  color: inherit;
}

.shelter-hit:hover .shelter-name {
  color: var(--accent-text);
}

.shelter-name {
  font-size: 0.88rem;
  font-weight: 600;
  grid-column: 1;
}

.shelter-count {
  grid-column: 2;
  grid-row: 1;
  font-size: 0.88rem;
  font-variant-numeric: tabular-nums;
  color: var(--ink-secondary);
  white-space: nowrap;
}

.shelter-meta {
  grid-column: 1 / -1;
  font-size: 0.74rem;
  color: var(--ink-muted);
}

/* A bar, not a number repeated: the count is already in the right column, and
   the bar is there to make the shape of the ranking readable at a glance. */
.shelter-bar {
  grid-column: 1 / -1;
  height: 4px;
  border-radius: 999px;
  background: var(--ramp-3);
  margin-top: 0.25rem;
  min-width: 2px;
}

.shelter-row.on .shelter-bar {
  background: var(--ramp-5);
}

.map-card {
  /* No longer sticky: at full width the map is most of the viewport already,
     and pinning something that tall just covers whatever is scrolled past. */
  position: relative;
}

.detail {
  /* Reserved so hovering from one county to another does not resize the card
     and shove the list below it up and down. */
  min-height: 24rem;
}

.detail.empty {
  color: var(--ink-muted);
  display: flex;
  align-items: center;
}

.detail-name {
  font-size: 1.4rem;
}

.detail-sub {
  margin: 0.1rem 0 0;
  color: var(--ink-muted);
  font-size: 0.85rem;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  padding: 0.9rem 0;
  border-top: 1px solid var(--hairline);
  border-bottom: 1px solid var(--hairline);
}

.stat-label {
  margin: 0 0 0.2rem;
  font-size: 0.78rem;
  color: var(--ink-muted);
}

.stat-value {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.stat-value.accent {
  color: var(--accent-text);
}

.stat-value span {
  font-size: 0.82rem;
  font-weight: 400;
  color: var(--ink-secondary);
}

.stat-sub {
  margin: 0.1rem 0 0;
  font-size: 0.78rem;
  color: var(--ink-muted);
}

.species {
  margin: 0 0 0.15rem;
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
}

.species span {
  color: var(--ink-muted);
  margin-left: 0.3rem;
}

.spread {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  padding: 0.8rem 0 0;
}

.spread-value {
  margin: 0;
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
}

.spread-sub {
  font-size: 0.76rem;
  color: var(--ink-muted);
  margin-left: 0.25rem;
}

.spread-note {
  margin: 0.6rem 0 0;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid var(--hairline);
  font-size: 0.76rem;
  line-height: 1.65;
  color: var(--ink-muted);
}

.coverage {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.8rem 0 0;
  font-size: 0.85rem;
  color: var(--ink-secondary);
}

.coverage-badge {
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  background: var(--surface-sunk);
  font-size: 0.78rem;
  color: var(--ink-secondary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.detail-note {
  margin: 0.7rem 0 0;
  font-size: 0.78rem;
  line-height: 1.65;
  color: var(--ink-muted);
}

.mark {
  color: var(--accent-text);
  margin-right: 0.25rem;
}

.hint-empty {
  margin: 0;
  font-size: 0.92rem;
}

.panel-title {
  font-size: 1rem;
}

.panel-sub {
  margin: 0.15rem 0 0;
  font-size: 0.78rem;
  color: var(--ink-muted);
}

.panel-note {
  color: var(--ink-muted);
  font-weight: 400;
}

.legend {
  margin-top: 0.75rem;
  border-top: 1px solid var(--hairline);
  padding-top: 0.85rem;
}

.legend-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
}

.legend-title,
.legend-unit {
  font-size: 0.8rem;
  color: var(--ink-muted);
}

.legend ul {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 1rem;
  font-size: 0.82rem;
  color: var(--ink-secondary);
  font-variant-numeric: tabular-nums;
}

.legend li {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.legend-note {
  margin: 0.6rem 0 0;
  font-size: 0.76rem;
  color: var(--ink-muted);
}

.swatch {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  display: inline-block;
}

.caveats {
  margin-top: 1.5rem;
}

.caveats h2 {
  font-size: 1.05rem;
  display: flex;
  align-items: center;
}

.caveats-intro {
  margin: 0.7rem 0 1.1rem;
  color: var(--ink-secondary);
  font-size: 0.9rem;
  max-width: 60rem;
}

.notes {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.75rem;
}

.note-card {
  background: var(--surface-sunk);
  border-radius: var(--radius-sm);
  padding: 0.9rem 1.1rem 1rem;
}

.note-no {
  margin: 0 0 0.2rem;
  font-size: 0.75rem;
  color: var(--accent-text);
  font-variant-numeric: tabular-nums;
}

.note-card h3 {
  font-size: 0.9rem;
  margin-bottom: 0.35rem;
}

.note-card p {
  margin: 0;
  font-size: 0.83rem;
  line-height: 1.75;
  color: var(--ink-secondary);
}

.caveats-foot {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 1.1rem;
  padding-top: 0.9rem;
  border-top: 1px solid var(--hairline);
  font-size: 0.76rem;
  color: var(--ink-muted);
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }

  /* Stacked, the rail sits under the map rather than beside it, so there is
     nothing to step aside from. */
  .map-frame.shifted {
    padding-left: 0;
  }

  /* Over a narrow map the rail would cover the county it describes. */
  .rail {
    position: static;
    width: auto;
    max-height: none;
    margin-top: 0.9rem;
    box-shadow: none;
  }

  .rail-open {
    position: static;
    margin-bottom: 0.7rem;
  }

  /* Stacked, a sticky map would cover most of the viewport while the reader
     is trying to scroll the list past it. */
  .map-card {
    position: static;
  }

  .detail {
    min-height: 0;
  }

  .stats,
  .spread {
    grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
  }

}
</style>
