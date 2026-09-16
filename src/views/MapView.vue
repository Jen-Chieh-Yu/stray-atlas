<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import CountyChoropleth from '@/components/CountyChoropleth.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import PageHead from '@/components/PageHead.vue'
import { fetchShelterPoints, useAtlasData } from '@/composables/useAtlasData'
import { animalsLink, formatCount } from '@/lib/animals'
import { addressesOf, phoneOf } from '@/lib/shelters'
import type { CountyStats, KindFilter, Metric, ShelterPoint, Summary } from '@/types'

const { stats, shapes, loading, error, reload } = useAtlasData()
const route = useRoute()
const router = useRouter()

const points = ref<ShelterPoint[]>([])

onMounted(async () => {
  try {
    points.value = (await fetchShelterPoints()).points
  } catch {
    // The choropleth is the page; markers are an overlay. A failed fetch
    // hides the layer rather than taking the map down with it.
    points.value = []
  }
})

/* ── State lives in the URL, as on the animals and shelters pages ─────────
 *
 *  metric=median, kind=dog|cat, pins=1, county=<name>, shelter=<id>. A link
 *  to 新北市 with pins on opens exactly that view. Unknown values are
 *  ignored against the data rather than trusted.
 */
const KIND_QUERY: Record<string, KindFilter> = { dog: '狗', cat: '貓' }
const KIND_PARAM: Partial<Record<KindFilter, string>> = { 狗: 'dog', 貓: 'cat' }

function one(value: unknown): string | null {
  const first = Array.isArray(value) ? value[0] : value
  return typeof first === 'string' && first !== '' ? first : null
}

const metric = computed<Metric>(() => (route.query.metric === 'median' ? 'median' : 'count'))
const kind = computed<KindFilter>(() => KIND_QUERY[one(route.query.kind) ?? ''] ?? 'all')
const showPins = computed(() => route.query.pins === '1')

const activeShelter = computed(
  () => points.value.find((point) => point.id === one(route.query.shelter)) ?? null,
)

/** A shelter belongs to a county, so an open shelter also marks its county;
 *  the shelter panel's ✕ then leads back there. */
const selected = computed<string | null>(() => {
  if (activeShelter.value) return activeShelter.value.county
  const name = one(route.query.county)
  return stats.value?.counties.some((county) => county.name === name) ? name : null
})

const locked = computed(
  () => stats.value?.counties.find((county) => county.name === selected.value) ?? null,
)

type Patch = Partial<{
  metric: Metric
  kind: KindFilter
  pins: boolean
  county: string | null
  shelter: string | null
}>

function update(patch: Patch) {
  const next = {
    metric: metric.value,
    kind: kind.value,
    pins: showPins.value,
    county: selected.value,
    shelter: activeShelter.value?.id ?? null,
    ...patch,
  }
  const query: Record<string, string> = {}
  if (next.metric === 'median') query.metric = 'median'
  const kindParam = KIND_PARAM[next.kind]
  if (kindParam) query.kind = kindParam
  if (next.pins) query.pins = '1'
  if (next.shelter) query.shelter = next.shelter
  else if (next.county) query.county = next.county
  void router.replace({ query })
}

/* ── Panel: three states, always on screen ────────────────────────────────
 *
 *  全臺 → 縣市 → 收容所. A click on the county that is already open goes back
 *  to 全臺. The map cannot make that call itself: it only knows which county
 *  is marked, and an open shelter marks its county too.
 */
type Mode = 'total' | 'county' | 'shelter'
const mode = computed<Mode>(() =>
  activeShelter.value ? 'shelter' : locked.value ? 'county' : 'total',
)

function onCountyClick(name: string | null) {
  if (!name || (mode.value === 'county' && selected.value === name)) {
    update({ county: null, shelter: null })
    return
  }
  update({ county: name, shelter: null })
}

function openShelter(id: string) {
  if (activeShelter.value?.id === id) {
    update({ shelter: null })
    return
  }
  const point = points.value.find((p) => p.id === id)
  if (point) update({ county: point.county, shelter: id })
}

/** The shelter card's ✕ steps back to its county; the county card's ✕ goes
 *  back to 全臺. */
function closePanel() {
  if (activeShelter.value) update({ shelter: null })
  else update({ county: null })
}

/* ── Colour classes ────────────────────────────────────────────────────────
 *
 *  Fixed thresholds, not quantiles. With quantiles every switch between 狗
 *  and 貓 redraws the classes, so the two maps cannot be compared; with fixed
 *  ones the same colour means the same number on every view.
 */
const CLASSES: Record<Metric, { cuts: number[]; labels: string[] }> = {
  count: {
    cuts: [49, 99, 199, 499, 999],
    labels: ['1–49', '50–99', '100–199', '200–499', '500–999', '1,000 以上'],
  },
  median: {
    cuts: [89, 179, 364, 729, 1459],
    labels: ['90 天內', '90–179 天', '180–364 天', '1–2 年', '2–4 年', '4 年以上'],
  },
}

/** A median over a handful of animals is noise, not a signal. */
const MIN_FOR_MEDIAN = 20

function summaryOf(county: CountyStats): Summary {
  return kind.value === 'all' ? county.all : county[kind.value]
}

function valueOf(county: CountyStats): number | null {
  const summary = summaryOf(county)
  // Zero animals is drawn as "none here", not as the lightest class.
  if (summary.count === 0) return null
  if (metric.value === 'count') return summary.count
  return summary.count >= MIN_FOR_MEDIAN ? summary.median_days : null
}

const values = computed(
  () => new Map((stats.value?.counties ?? []).map((county) => [county.name, valueOf(county)])),
)
const breaks = computed(() => CLASSES[metric.value].cuts)
const legend = computed(() => CLASSES[metric.value].labels)

/* ── Panel content ─────────────────────────────────────────────────────── */

const METRICS: { id: Metric; label: string }[] = [
  { id: 'count', label: '在所數' },
  { id: 'median', label: '滯留中位數' },
]

const kinds = computed(() => {
  const byKind = (name: '狗' | '貓') =>
    (stats.value?.counties ?? []).reduce((sum, county) => sum + county[name].count, 0)
  return [
    { id: 'all' as KindFilter, label: '全部', count: stats.value?.total.count ?? 0 },
    { id: '狗' as KindFilter, label: '狗', count: byKind('狗') },
    { id: '貓' as KindFilter, label: '貓', count: byKind('貓') },
  ]
})

const shelterCount = computed(() =>
  (stats.value?.counties ?? []).reduce((total, county) => total + county.shelters, 0),
)

function days(value: number | null): string {
  return value === null ? '—' : `${formatCount(value)} 天`
}

const nums = computed(() => {
  const shelter = activeShelter.value
  if (shelter) {
    return [
      { value: formatCount(shelter.count), label: '隻在所動物' },
      { value: days(shelter.median_days), label: '在所天數中位數' },
      { value: days(shelter.mean_days), label: '平均在所天數' },
      { value: days(shelter.max_days), label: '等最久的一隻' },
    ]
  }
  const county = locked.value
  const summary = county ? county.all : stats.value?.total
  if (!summary) return []
  return [
    { value: formatCount(summary.count), label: '隻在所動物' },
    { value: formatCount(county ? county.shelters : shelterCount.value), label: '間收容所' },
    { value: days(summary.median_days), label: '在所天數中位數' },
    { value: days(summary.max_days), label: '等最久的一隻' },
  ]
})

const split = computed(() => {
  const shelter = activeShelter.value
  if (shelter) return { dogs: shelter.dogs, cats: shelter.cats }
  const county = locked.value
  if (county) return { dogs: county.狗.count, cats: county.貓.count }
  return { dogs: kinds.value[1].count, cats: kinds.value[2].count }
})

function widthOf(part: number): string {
  const whole = split.value.dogs + split.value.cats
  return whole === 0 ? '0%' : `${(part / whole) * 100}%`
}

/** 全臺: the six counties first on the current metric and kind. */
const topCounties = computed(() => {
  const unit = metric.value === 'count' ? '隻' : '天'
  return (stats.value?.counties ?? [])
    .map((county) => ({ name: county.name, value: valueOf(county) }))
    .filter((row): row is { name: string; value: number } => row.value !== null)
    .sort((a, b) => b.value - a.value)
    .slice(0, 6)
    .map((row) => ({ name: row.name, text: `${formatCount(row.value)} ${unit}` }))
})

/** 縣市: its shelters, most animals first. */
const countyShelters = computed(() =>
  points.value
    .filter((point) => point.county === selected.value)
    .sort((a, b) => b.count - a.count),
)

const shelterAddresses = computed(() =>
  activeShelter.value ? addressesOf(activeShelter.value) : [],
)
const shelterPhone = computed(() => (activeShelter.value ? phoneOf(activeShelter.value) : null))

const manualCount = computed(() => points.value.filter((point) => point.manual).length)

const hint = computed(() => {
  if (mode.value === 'shelter') {
    return '圖釘的位置是行政區形心，不是門牌；出發前請照上面的地址與電話再確認一次。'
  }
  if (mode.value === 'county') return '點一間收容所看它的資料與動物清單。'
  return '點一個縣市看它的收容所；再點一次可以回到全臺。'
})
</script>

<template>
  <div>
    <PageHead title="縣市地圖">
      動物集中在哪些縣市、哪些縣市的動物待得特別久，一張圖看完，再一路點到單一收容所。
      先讀一件事：這張圖畫的是<strong>收容所的所在地</strong>，不是動物被撿到的地方——底下有說明。
    </PageHead>

    <p v-if="loading" class="state">載入中…</p>

    <p v-else-if="error" class="state">
      資料載入失敗（{{ error }}）。
      <button type="button" class="retry" @click="reload">重試</button>
    </p>

    <template v-else-if="stats && shapes">
      <div class="findbox">
        <div class="field">
          <span id="m-metric" class="label">顯示指標</span>
          <div class="pills" role="group" aria-labelledby="m-metric">
            <button
              v-for="option in METRICS"
              :key="option.id"
              type="button"
              class="pill-btn"
              :aria-pressed="metric === option.id"
              @click="update({ metric: option.id })"
            >
              {{ option.label }}
            </button>
          </div>
        </div>

        <div class="field">
          <span id="m-kind" class="label">動物類型</span>
          <div class="pills" role="group" aria-labelledby="m-kind">
            <button
              v-for="option in kinds"
              :key="option.id"
              type="button"
              class="pill-btn"
              :aria-pressed="kind === option.id"
              @click="update({ kind: option.id })"
            >
              {{ option.label }} {{ formatCount(option.count) }}
            </button>
          </div>
        </div>

        <div v-if="points.length" class="field">
          <span id="m-layer" class="label">圖層</span>
          <div class="pills" role="group" aria-labelledby="m-layer">
            <button
              type="button"
              class="pill-btn"
              :aria-pressed="showPins"
              @click="update({ pins: !showPins })"
            >
              收容所圖釘 {{ points.length }}
            </button>
          </div>
        </div>
      </div>

      <div class="mapcard">
        <!-- The panel stays on screen: 全臺 is its resting state, not a
             closed one. -->
        <aside class="rail" aria-live="polite">
          <div class="rail-head">
            <div class="rail-title">
              <span class="rail-kicker">
                {{
                  activeShelter
                    ? `${activeShelter.county} · 收容所`
                    : mode === 'county'
                      ? '縣市'
                      : '全臺'
                }}
              </span>
              <h2>
                {{ activeShelter ? activeShelter.name : locked ? locked.name : '全臺公立收容所' }}
              </h2>
            </div>
            <button
              v-if="mode !== 'total'"
              type="button"
              class="rail-close"
              :aria-label="mode === 'shelter' ? '回到縣市' : '回到全臺'"
              @click="closePanel"
            >
              <LucideIcon name="x" :size="18" />
            </button>
          </div>

          <div class="rail-nums">
            <div v-for="num in nums" :key="num.label" class="rnum">
              <b>{{ num.value }}</b>
              <span>{{ num.label }}</span>
            </div>
          </div>

          <div>
            <div class="rail-split" aria-hidden="true">
              <i class="dog" :style="{ width: widthOf(split.dogs) }" />
              <i class="cat" :style="{ width: widthOf(split.cats) }" />
            </div>
            <div class="rail-splitlab">
              <span class="k dog">狗 <em>{{ formatCount(split.dogs) }}</em></span>
              <span class="k cat">貓 <em>{{ formatCount(split.cats) }}</em></span>
            </div>
          </div>

          <template v-if="activeShelter">
            <div class="rail-meta">
              <div>
                <span class="lbl">地址</span>
                <span v-for="address in shelterAddresses" :key="address.text" class="line">
                  {{ address.text }}
                </span>
              </div>
              <div>
                <span class="lbl">電話</span>
                <a v-if="shelterPhone?.href" class="line" :href="shelterPhone.href">
                  {{ shelterPhone.text }}
                </a>
                <span v-else class="line">原始資料未提供完整電話</span>
              </div>
            </div>
            <div class="rail-actions">
              <RouterLink
                :to="{ name: 'shelter', params: { id: activeShelter.id } }"
                class="detail-btn"
              >
                收容所介紹
                <LucideIcon name="arrow-right" :size="16" />
              </RouterLink>
              <RouterLink :to="animalsLink({ shelter: activeShelter.id })" class="animals-link">
                看這裡的 {{ formatCount(activeShelter.count) }} 隻動物 →
              </RouterLink>
            </div>
          </template>

          <div v-else-if="mode === 'county'" class="rail-list">
            <span class="cap">這個縣市的收容所</span>
            <button
              v-for="shelter in countyShelters"
              :key="shelter.id"
              type="button"
              class="rail-item"
              @click="openShelter(shelter.id)"
            >
              <span class="nm">{{ shelter.name }}</span>
              <span class="n">{{ formatCount(shelter.count) }} 隻</span>
            </button>
          </div>

          <div v-else class="rail-list">
            <span class="cap">
              {{ metric === 'count' ? '在所數最多的六個縣市' : '滯留中位數最長的六個縣市' }}
            </span>
            <button
              v-for="row in topCounties"
              :key="row.name"
              type="button"
              class="rail-item"
              @click="onCountyClick(row.name)"
            >
              <span class="nm">{{ row.name }}</span>
              <span class="n">{{ row.text }}</span>
            </button>
          </div>

          <p class="rail-hint">{{ hint }}</p>
        </aside>

        <div class="mapwrap">
          <span class="maphint">點選縣市或圖釘</span>
          <CountyChoropleth
            :shapes="shapes"
            :values="values"
            :breaks="breaks"
            :selected="selected"
            :picked-shelter="activeShelter?.id ?? null"
            :points="points"
            :show-points="showPins && points.length > 0"
            @select="onCountyClick($event)"
            @open-shelter="openShelter"
          />
        </div>

        <!-- Under the map, not over it: laid on the map it would cover the
             高雄–屏東 coast. -->
        <div class="maplegend">
          <div class="lg-main">
            <span class="cap">{{ metric === 'count' ? '在所動物數（隻）' : '在所天數中位數' }}</span>
            <div class="lg-row">
              <span v-for="(label, index) in legend" :key="label" class="lg-step">
                <i :style="{ background: `var(--ramp-${index + 1})` }" />
                <em>{{ label }}</em>
              </span>
            </div>
            <span class="lg-nd">
              <i />
              {{
                metric === 'count'
                  ? '0 隻／沒有公立收容所'
                  : `在所不足 ${MIN_FOR_MEDIAN} 隻／沒有公立收容所`
              }}
            </span>
          </div>
          <p class="lg-note">
            離島插圖只畫收容所所在的島群（澎湖本島、大小金門、南竿北竿），各有各的比例尺，面積不可與本島相比。滾輪或右下角按鈕縮放，放大後可拖曳；連點兩下縣市會把鏡頭框過去。
          </p>
        </div>
      </div>

      <section class="boundary">
        <div class="boundary-head">
          <span class="kicker">這張圖不能拿來說什麼</span>
        </div>
        <ul>
          <li>
            <strong>這是收容所的地圖，不是流浪動物的地圖。</strong>顏色來自「動物現在在哪一間收容所」，不是牠被撿到的地方。尋獲地欄位只有
            2.4% 自己寫出縣市，其中又有 6% 與收容縣市不同，有些登錄者直接寫「外縣市」。
          </li>
          <li>顏色同時混著「動物量」和「幾間收容所」兩件事。跨縣市比較之前，先看面板裡的收容所數。</li>
          <li>
            只算得出<strong>目前仍在所</strong>的動物，所以看不出一間收容所的認養速度。待得越久的動物越可能留在快照裡：全臺滯留中位數
            {{ days(stats.total.median_days) }}，平均卻是
            {{ days(stats.total.mean_days) }}，這個差距本身就是偏誤的證據。
          </li>
          <li>
            在所數是存量，不是流量。在所數高可能是空間充裕、長期安置；在所數低也可能是已經滿載而嚴格控管入所，不能單憑顏色推論地方主管機關的作為。
          </li>
          <li>
            圖釘的位置是<strong>行政區形心，不是門牌</strong>{{
              manualCount ? `，其中 ${manualCount} 處的行政區由地址人工判定` : ''
            }}。出發前請照面板上的地址與電話再確認一次。
          </li>
          <li>
            切換狗／貓時色階門檻不變，兩張圖可以直接互比。在「在所數」下整片變灰的縣市是真的 0
            隻；在「滯留中位數」下則是在所不足 {{ MIN_FOR_MEDIAN }} 隻，中位數沒有參考價值。
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

.retry {
  margin-left: 0.5rem;
  padding: 0.2rem 0.8rem;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: var(--surface);
  color: var(--ink);
  font: inherit;
  cursor: pointer;
}

/* ── Controls ── */
.findbox {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem 2rem;
  margin-top: 1.75rem;
  padding: 1.25rem 1.5rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}

.field > .label {
  color: var(--ink-muted);
  font-size: 0.8rem;
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

/* ── Map card: panel | map, legend band below ── */
.mapcard {
  display: grid;
  grid-template-columns: 292px minmax(0, 1fr);
  overflow: hidden;
  margin-top: 1.25rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
}

/* contain: size keeps the panel from setting the row height: the map does,
   and a long county list scrolls inside the panel instead of stretching
   the card. */
.rail {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  min-width: 0;
  contain: size;
  overflow-y: auto;
  padding: 1.25rem;
  border-right: 1px solid var(--hairline);
  background: var(--plane);
}

.rail-head {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.rail-title {
  flex: 1;
  min-width: 0;
}

.rail-kicker {
  display: block;
  color: var(--ink-muted);
  font-size: 0.72rem;
  letter-spacing: 0.14em;
}

.rail-head h2 {
  font-size: 1.05rem;
}

.rail-close {
  display: grid;
  place-items: center;
  padding: 0.15rem;
  border: 0;
  background: transparent;
  color: var(--ink-muted);
  cursor: pointer;
}

.rail-close:hover {
  color: var(--ink);
}

.rail-nums {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.6rem;
}

.rnum {
  padding: 0.6rem 0.7rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--surface);
}

.rnum b {
  display: block;
  color: var(--accent-text);
  font-size: 1.15rem;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}

.rnum span {
  color: var(--ink-muted);
  font-size: 0.76rem;
}

.rail-split {
  display: flex;
  overflow: hidden;
  height: 8px;
  border-radius: 999px;
  background: var(--no-data);
}

.rail-split i {
  display: block;
  height: 100%;
}

.rail-split .dog,
.rail-splitlab .dog::before {
  background: var(--series-a);
}

.rail-split .cat,
.rail-splitlab .cat::before {
  background: var(--series-b);
}

.rail-splitlab {
  display: flex;
  justify-content: space-between;
  margin-top: 0.3rem;
  color: var(--ink-secondary);
  font-size: 0.78rem;
}

.rail-splitlab em {
  font-style: normal;
  font-variant-numeric: tabular-nums;
}

.rail-splitlab .k {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.rail-splitlab .k::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.rail-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  color: var(--ink-secondary);
  font-size: 0.84rem;
}

.rail-meta .lbl,
.rail-meta .line {
  display: block;
}

.rail-meta .lbl {
  color: var(--ink-muted);
  font-size: 0.74rem;
}

.rail-meta a.line {
  color: var(--ink);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  text-decoration: none;
}

.rail-meta a.line:hover {
  color: var(--accent-text);
}

.rail-actions {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
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

.rail-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.rail-list .cap {
  color: var(--ink-muted);
  font-size: 0.76rem;
  letter-spacing: 0.08em;
}

.rail-item {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  padding: 0.5rem 0.6rem;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink);
  font: inherit;
  font-size: 0.88rem;
  line-height: 1.45;
  text-align: left;
  cursor: pointer;
}

.rail-item:hover {
  border-color: var(--hairline);
  background: var(--surface);
}

.rail-item .nm {
  flex: 1;
  min-width: 0;
}

.rail-item .n {
  color: var(--ink-muted);
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.rail-hint {
  margin: 0;
  color: var(--ink-muted);
  font-size: 0.8rem;
  line-height: 1.6;
}

.mapwrap {
  position: relative;
  min-width: 0;
  padding: 0.75rem;
}

.maphint {
  position: absolute;
  top: 1rem;
  right: 1rem;
  color: var(--ink-muted);
  font-size: 0.78rem;
}

/* ── Legend band ── */
.maplegend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1.5rem;
  grid-column: 1 / -1;
  padding: 0.9rem 1.25rem;
  border-top: 1px solid var(--hairline);
  background: var(--plane);
}

.lg-main {
  display: flex;
  flex: 1 1 100%;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem 0.9rem;
  min-width: 0;
}

.maplegend .cap {
  color: var(--ink-secondary);
  font-size: 0.78rem;
}

.lg-row {
  display: flex;
  flex: 1 1 300px;
  gap: 0.15rem;
  min-width: 0;
  max-width: 30rem;
}

.lg-step {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  min-width: 0;
}

.lg-step i {
  display: block;
  width: 100%;
  height: 10px;
}

.lg-step:first-child i {
  border-radius: 3px 0 0 3px;
}

.lg-step:last-child i {
  border-radius: 0 3px 3px 0;
}

.lg-step em {
  color: var(--ink-muted);
  font-size: 0.68rem;
  font-style: normal;
  line-height: 1.3;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.lg-nd {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--ink-muted);
  font-size: 0.72rem;
}

.lg-nd i {
  width: 14px;
  height: 10px;
  border-radius: 2px;
  background: var(--no-data);
}

.lg-note {
  max-width: 46rem;
  margin: 0;
  color: var(--ink-muted);
  font-size: 0.78rem;
  line-height: 1.6;
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
  font-variant-numeric: tabular-nums;
}

.boundary strong {
  color: var(--ink);
}

@media (max-width: 900px) {
  /* minmax(0, 1fr), not 1fr: the SVG's min-content width comes from its
     viewBox ratio and would push the card past the screen. */
  .mapcard {
    grid-template-columns: minmax(0, 1fr);
  }

  /* On one column the map and its legend come first: with the panel above
     them, a tap on the map would change text already scrolled past. */
  .mapwrap,
  .maplegend {
    order: -1;
  }

  .maplegend {
    border-bottom: 1px solid var(--hairline);
  }

  .rail {
    contain: none;
    border-right: 0;
  }
}

@media (max-width: 520px) {
  .findbox {
    padding: 1.1rem;
  }

  .field {
    width: 100%;
  }

  .maphint {
    display: none;
  }

  .lg-step em {
    font-size: 0.62rem;
  }
}
</style>
