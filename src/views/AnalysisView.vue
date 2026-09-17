<script setup lang="ts">
/** Duration analysis: histogram + KDE, an ECDF comparing 狗 with 貓, the
 *  quantile table and the county list.
 *
 *  The page is built around one caveat rather than decorated with it. Every
 *  animal here is still in a shelter, so the numbers describe who is currently
 *  inside, not how long a stay lasts — and the second chart exists so the
 *  quotable figures come from a curve with no bandwidth in it.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DistributionChart from '@/components/DistributionChart.vue'
import EcdfChart from '@/components/EcdfChart.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import PageHead from '@/components/PageHead.vue'
import { fetchDistribution, fetchFoundplace, useAtlasData } from '@/composables/useAtlasData'
import { formatCount } from '@/lib/animals'
import type {
  DistributionPayload,
  FoundplacePayload,
  Scale,
  Scope,
  Smoothing,
} from '@/types'

const route = useRoute()
const router = useRouter()
const { stats } = useAtlasData()

const data = ref<DistributionPayload | null>(null)
const foundplace = ref<FoundplacePayload | null>(null)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    data.value = await fetchDistribution()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  }
  try {
    foundplace.value = await fetchFoundplace()
  } catch {
    // Only one sentence in the county note reads this; without it the
    // sentence is left out rather than the page failing.
    foundplace.value = null
  }
})

/* ── Settings live in the URL, as on the other pages ──────────────────────
 *
 *  kind=dog|cat, axis=linear, smooth=fine|smooth. The defaults (全部, 對數,
 *  標準) are left out of the URL.
 */
const SCOPES: { id: Scope; label: string }[] = [
  { id: 'all', label: '全部' },
  { id: 'dog', label: '狗' },
  { id: 'cat', label: '貓' },
]
const SCALES: { id: Scale; label: string }[] = [
  { id: 'log', label: '對數' },
  { id: 'linear', label: '線性' },
]
const SMOOTHINGS: { id: Smoothing; label: string }[] = [
  { id: 'fine', label: '較細' },
  { id: 'standard', label: '標準' },
  { id: 'smooth', label: '較平滑' },
]

const scope = computed<Scope>(() =>
  route.query.kind === 'dog' || route.query.kind === 'cat' ? route.query.kind : 'all',
)
const scale = computed<Scale>(() => (route.query.axis === 'linear' ? 'linear' : 'log'))
const smoothing = computed<Smoothing>(() =>
  route.query.smooth === 'fine' || route.query.smooth === 'smooth'
    ? route.query.smooth
    : 'standard',
)

function update(patch: Partial<{ scope: Scope; scale: Scale; smoothing: Smoothing }>) {
  const next = { scope: scope.value, scale: scale.value, smoothing: smoothing.value, ...patch }
  const query: Record<string, string> = {}
  if (next.scope !== 'all') query.kind = next.scope
  if (next.scale !== 'log') query.axis = next.scale
  if (next.smoothing !== 'standard') query.smooth = next.smoothing
  void router.replace({ query })
}

const labelOf = <T extends string>(options: { id: T; label: string }[], id: T) =>
  options.find((option) => option.id === id)?.label ?? ''

const current = computed(() => data.value?.scopes[scope.value] ?? null)
const block = computed(() => (current.value ? current.value[scale.value] : null))

/** Stated beside the controls: the bandwidth is the one setting whose effect
 *  on the curve is invisible until it is named. */
const bandwidth = computed(() => {
  const value = block.value?.kde[smoothing.value].bandwidth ?? 0
  return scale.value === 'log' ? `${value.toFixed(3)} log₁₀ 天` : `${formatCount(Math.round(value))} 天`
})

const ecdfSeries = computed(() => {
  if (!data.value) return []
  return [
    { key: 'dog', label: '狗', colour: 'var(--series-a)', points: data.value.scopes.dog.ecdf },
    { key: 'cat', label: '貓', colour: 'var(--series-b)', points: data.value.scopes.cat.ecdf },
  ]
})

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

/** The whole-number percentage used in running text. */
function pctRound(value: number): string {
  return `${Math.round(value * 100)}%`
}

function ratio(a: number, b: number): string {
  return b === 0 ? '—' : (a / b).toFixed(1)
}

/* ── County list ───────────────────────────────────────────────────────────
 *
 *  Every row carries both numbers: sorting by one and printing only that one
 *  hides the fact that the two disagree — 桃園市 is fourth by headcount and
 *  first by median. The accent marks a median at least twice the national
 *  one, a stated rule rather than a judgement about the county.
 */
const national = computed(() => stats.value?.total.median_days ?? null)
const hotLine = computed(() => (national.value === null ? null : national.value * 2))

const countyRows = computed(() =>
  [...(stats.value?.counties ?? [])]
    .sort((a, b) => b.all.count - a.all.count)
    .map((county) => ({
      name: county.name,
      shelters: county.shelters,
      count: county.all.count,
      median: county.all.median_days,
      hot:
        hotLine.value !== null &&
        county.all.median_days !== null &&
        county.all.median_days >= hotLine.value,
    })),
)

const hotCount = computed(() => countyRows.value.filter((row) => row.hot).length)
const shelterRange = computed(() => {
  const counts = countyRows.value.map((row) => row.shelters)
  return counts.length ? [Math.min(...counts), Math.max(...counts)] : [0, 0]
})
</script>

<template>
  <div class="page">
    <PageHead title="資料分析">
      地圖答不了的那個問題：在所天數的分布長什麼樣。這頁只有在下面那張警語卡先被讀過之後才是誠實的，所以它放在圖表上面，不是放在註腳。
    </PageHead>

    <!-- Not a footnote. Each column names its statistical term in English as
         well: a reader who knows the term can stop at the heading, and one who
         does not gets the words they would need to look it up. -->
    <section class="warncard" aria-labelledby="warn-title">
      <div class="warn-top">
        <span id="warn-title" class="pill">
          <LucideIcon name="triangle-alert" :size="15" />方法學指引與資料邊界
        </span>
        <span class="kicker">DATA BOUNDARY &amp; BIAS</span>
      </div>
      <div class="warn-cols">
        <div class="warn-col">
          <span class="no">01</span>
          <h2>右設限<em>Right-Censoring</em></h2>
          <p>
            這份資料只看得到<strong>目前仍在所</strong>的動物。每一筆的在所天數都還在往上加，沒有一筆是完整的停留長度。已經被認養、被領回、或因其他原因離開的動物，全部不在這份快照裡。
          </p>
          <span class="status">所有觀測值都只是下界</span>
        </div>
        <div class="warn-col">
          <span class="no">02</span>
          <h2>長度偏差抽樣<em>Length-Biased Sampling</em></h2>
          <p>
            在某一天對收容所拍一張快照，待得越久的動物被拍到的機率天生就越高。很快就離所的動物幾乎不會出現在任何一張快照裡，所以牠們在這份資料中被系統性地低估。
          </p>
          <span class="status">快照必然高估停留時間</span>
        </div>
        <div class="warn-col">
          <span class="no">03</span>
          <h2>存活分析<em>Survival Analysis</em></h2>
          <p>
            要回答「一隻狗平均多久會被認養」，需要的是 Kaplan–Meier 這一類處理設限資料的方法，以及進出所的時間序列。本站只有單日快照，兩者都沒有。
          </p>
          <span class="status">本站不做認養速度的推論</span>
        </div>
      </div>
    </section>

    <p v-if="error" class="state">分布資料載入失敗：{{ error }}</p>
    <p v-else-if="!data || !current || !block" class="state">載入中…</p>

    <template v-else>
      <section class="acard controls" aria-label="圖表設定">
        <div class="field">
          <span id="a-scope" class="label">對象</span>
          <div class="pills" role="group" aria-labelledby="a-scope">
            <button
              v-for="option in SCOPES"
              :key="option.id"
              type="button"
              class="pill-btn"
              :aria-pressed="scope === option.id"
              @click="update({ scope: option.id })"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
        <div class="field">
          <span id="a-scale" class="label">橫軸</span>
          <div class="pills" role="group" aria-labelledby="a-scale">
            <button
              v-for="option in SCALES"
              :key="option.id"
              type="button"
              class="pill-btn"
              :aria-pressed="scale === option.id"
              @click="update({ scale: option.id })"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
        <div class="field">
          <span id="a-smooth" class="label">平滑程度</span>
          <div class="pills" role="group" aria-labelledby="a-smooth">
            <button
              v-for="option in SMOOTHINGS"
              :key="option.id"
              type="button"
              class="pill-btn"
              :aria-pressed="smoothing === option.id"
              @click="update({ smoothing: option.id })"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
        <!-- What the three groups currently add up to, stated once. -->
        <p class="applied" aria-live="polite">
          已套用：<b>{{ labelOf(SCOPES, scope) }} {{ formatCount(current.count) }} 隻</b>
          · {{ scale === 'log' ? '對數軸' : '線性軸' }} · 平滑度
          {{ labelOf(SMOOTHINGS, smoothing) }}（頻寬 <b>{{ bandwidth }}</b>）
        </p>
      </section>

      <section class="acard" aria-labelledby="a-hist">
        <div class="an-head">
          <h2 id="a-hist">在所天數的分布</h2>
          <span class="sub">
            {{ labelOf(SCOPES, scope) }} {{ formatCount(current.count) }} 隻 ·
            {{ block.bins.length }} 個區間
          </span>
        </div>
        <DistributionChart
          :block="block"
          :scale="scale"
          :smoothing="smoothing"
          :log-ticks="data.log_ticks"
          :median="current.median_days"
        />
        <div class="chart-legend">
          <span class="k bar">長條：各區間的密度</span>
          <span class="k kde">曲線：核密度估計</span>
          <span class="k median">中位數</span>
        </div>
        <div class="note">
          <h3>數據判讀與尺度邊界</h3>
          <p>
            線性軸下這是一條單調遞減的長尾，全部結構都被壓在最前面幾百天；切到對數軸才看得到兩個隆起——一群已在所一年上下，另一群已在所數年。同一組數字，兩種軸說的是不同層次的事，所以兩種都放在這裡讓你切換。
          </p>
          <p>
            曲線的形狀有一半是頻寬的主張。三段平滑度分別是 Silverman 參考值的 0.6／1.0／1.7 倍，當前數值就寫在控制列右端——把選擇公開，讀者才有機會不同意。
          </p>
        </div>
      </section>

      <section class="acard" aria-labelledby="a-ecdf">
        <div class="an-head">
          <h2 id="a-ecdf">累積分布（ECDF）</h2>
          <span class="sub">狗與貓兩條，橫軸跟著上面的設定走</span>
        </div>
        <EcdfChart
          :series="ecdfSeries"
          :max-days="Math.max(data.scopes.dog.max_days, data.scopes.cat.max_days)"
          :ticks="data.log_ticks"
          :scale="scale"
        />
        <div class="chart-legend">
          <span class="k dog">狗</span>
          <span class="k cat">貓</span>
        </div>
        <div class="note">
          <h3>階梯曲線判讀指引</h3>
          <p>
            <strong>要引用的數字請讀這一張，不要讀上面那一張。</strong>ECDF 沒有頻寬、沒有平滑假設，「{{
              pctRound(data.scopes.dog.over_year)
            }} 的狗已在所超過一年」這種句子不該取決於一個讀者可以自己拖動的控制項。
          </p>
          <p>
            畫成階梯而不是折線是有理由的：ECDF 在每一個觀測值上跳躍，在兩隻動物之間畫一條斜線，等於宣稱有一個沒人擁有過的數值存在。
          </p>
        </div>
      </section>

      <section class="acard" aria-labelledby="a-quant">
        <div class="an-head">
          <h2 id="a-quant">分位數</h2>
          <span class="sub">單位：天</span>
        </div>
        <div class="table-scroll">
          <table class="qtable">
            <thead>
              <tr>
                <th scope="col">對象</th>
                <th scope="col">隻數</th>
                <th scope="col">P25</th>
                <th scope="col">中位數</th>
                <th scope="col">P75</th>
                <th scope="col">P90</th>
                <th scope="col">最長</th>
                <th scope="col">超過 1 年</th>
                <th scope="col">超過 4 年</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="option in SCOPES" :key="option.id">
                <th scope="row">{{ option.label }}</th>
                <td>{{ formatCount(data.scopes[option.id].count) }}</td>
                <td>{{ formatCount(data.scopes[option.id].p25_days) }}</td>
                <td>{{ formatCount(data.scopes[option.id].median_days) }}</td>
                <td>{{ formatCount(data.scopes[option.id].p75_days) }}</td>
                <td>{{ formatCount(data.scopes[option.id].p90_days) }}</td>
                <td>{{ formatCount(data.scopes[option.id].max_days) }}</td>
                <td>{{ pct(data.scopes[option.id].over_year) }}</td>
                <td>{{ pct(data.scopes[option.id].over_4_years) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="note">
          <h3>偏態分布判讀重點</h3>
          <p>
            全部動物的平均是 {{ formatCount(data.scopes.all.mean_days) }} 天、中位數是
            {{ formatCount(data.scopes.all.median_days) }} 天，差了
            {{ ratio(data.scopes.all.mean_days, data.scopes.all.median_days) }}
            倍。這種偏態下平均數沒有代表性，所以全站一律用中位數；表裡把每個分位數都列出來，是為了讓圖上的每個判斷都能被單獨查證，不必靠辨色。
          </p>
          <p>
            狗與貓不是同一回事：狗的中位數 {{ formatCount(data.scopes.dog.median_days) }} 天、貓
            {{ formatCount(data.scopes.cat.median_days) }}
            天。把兩者混在一起談「收容動物平均待多久」，等於用狗的數字去描述貓。
          </p>
        </div>
      </section>

      <section v-if="countyRows.length" class="acard" aria-labelledby="a-county">
        <div class="an-head">
          <h2 id="a-county">各縣市</h2>
          <span class="sub">依在所數排序 · 右側同時顯示在所數與中位數</span>
        </div>
        <ol class="ranklist">
          <li v-for="(row, index) in countyRows" :key="row.name" class="rank-row" :class="{ hot: row.hot }">
            <span class="rk">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="nm">{{ row.name }}</span>
            <span class="sh">{{ row.shelters }} 間</span>
            <span class="v1">{{ formatCount(row.count) }} 隻</span>
            <span class="v2">{{ row.median === null ? '—' : `${formatCount(row.median)} 天` }}</span>
          </li>
        </ol>
        <div class="note">
          <h3>縣市排行資料背景與口徑差異</h3>
          <p>
            縣市是用「動物現在在哪一間收容所」推得的，不是動物被撿到的地方<template v-if="foundplace"
              >——全部 {{ formatCount(foundplace.rows) }} 筆裡只有
              {{ formatCount(foundplace.county_source.text) }} 筆（{{
                pct(foundplace.county_source.text / foundplace.rows)
              }}）的尋獲地寫得出縣市名，其中又有
              {{ formatCount(foundplace.county_from_text_differs_from_shelter) }}
              筆與收容所不同縣市</template
            >。所以這張表講的是收容所的負擔分布，不是流浪動物的地理分布。
          </p>
          <p v-if="hotLine !== null">
            強調色的門檻是<strong>中位數達全國兩倍</strong>，也就是 {{ formatCount(hotLine) }}
            天以上，目前有 {{ hotCount }} 個縣市達到。門檻寫出來，讀者可以不同意；沒寫出來的門檻，就變成對那幾個縣市的指控。
          </p>
          <p>
            各縣市的收容所數量差很多（{{ shelterRange[0] }} 到 {{ shelterRange[1] }}
            間不等），在所數同時混著「動物量」和「幾間收容所」兩件事，欄位裡一併列出間數供對照。在所數也是存量不是流量：數字高可能是空間充裕、長期安置，數字低也可能是已經滿載而嚴格控管入所，不足以評價地方主管機關的作為。
          </p>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page > * + * {
  margin-top: 1.25rem;
}

.page > :first-child + * {
  margin-top: 1.75rem;
}

.state {
  color: var(--ink-muted);
}

/* ── Warning card ── */
.warncard {
  padding: 1.6rem;
  border-radius: var(--radius);
  background: var(--surface-sunk);
}

.warn-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.12rem 0.75rem;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: var(--surface);
  font-size: 0.84rem;

  & svg {
    color: var(--accent-text);
  }
}

.kicker {
  color: var(--ink-muted);
  font-size: 0.72rem;
  letter-spacing: 0.14em;
}

.warn-cols {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
}

.warn-col {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;

  & .no {
    color: var(--accent-text);
    font-size: 0.78rem;
    letter-spacing: 0.12em;
    font-variant-numeric: tabular-nums;
  }

  & h2 {
    font-size: 0.98rem;

    & em {
      display: block;
      color: var(--ink-muted);
      font-size: 0.76rem;
      font-style: normal;
      font-weight: 400;
      letter-spacing: 0.02em;
    }
  }

  & p {
    margin: 0;
    color: var(--ink-secondary);
    font-size: 0.86rem;
    line-height: 1.65;
  }

  & strong {
    color: var(--ink);
  }

  /* The three texts differ in length; margin-top: auto lines the footers up. */
  & .status {
    margin-top: auto;
    padding-top: 0.8rem;
    border-top: 1px solid var(--hairline);
    color: var(--ink-muted);
    font-size: 0.78rem;
  }
}

/* ── Cards ── */
.acard {
  padding: 1.5rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
}

.an-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.4rem 1rem;
  margin-bottom: 0.9rem;

  & h2 {
    font-size: 1.15rem;
  }

  & .sub {
    color: var(--ink-muted);
    font-size: 0.84rem;
    font-variant-numeric: tabular-nums;
  }
}

/* ── Controls ── */
.controls {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 1.25rem 1.5rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;

  & > .label {
    color: var(--ink-muted);
    font-size: 0.8rem;
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

.applied {
  margin: 0 0 0 auto;
  color: var(--ink-secondary);
  font-size: 0.84rem;
  line-height: 1.6;
  text-align: right;
  font-variant-numeric: tabular-nums;

  & b {
    color: var(--accent-text);
    font-weight: 500;
  }
}

/* ── Chart legends and notes ── */
.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  margin-top: 0.4rem;
  color: var(--ink-secondary);
  font-size: 0.84rem;

  & .k {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;

    &::before {
      content: '';
      width: 14px;
      height: 3px;
      border-radius: 2px;
    }
  }

  & .bar::before {
    width: 12px;
    height: 10px;
    background: var(--ramp-2);
  }

  & .kde::before {
    background: var(--ramp-5);
  }

  & .median::before {
    height: 0;
    border-top: 1.5px dashed var(--ink);
    border-radius: 0;
  }

  & .dog::before {
    background: var(--series-a);
  }

  & .cat::before {
    background: var(--series-b);
  }
}

/* A caption with its own heading and a sunk ground, not grey small print. */
.note {
  margin-top: 1.1rem;
  padding: 1rem 1.1rem;
  border-radius: var(--radius-sm);
  background: var(--surface-sunk);

  & h3 {
    margin-bottom: 0.4rem;
    font-size: 0.88rem;
  }

  & p {
    max-width: 52rem;
    margin: 0;
    color: var(--ink-secondary);
    font-size: 0.85rem;
    line-height: 1.7;
    font-variant-numeric: tabular-nums;

    & + p {
      margin-top: 0.5rem;
    }
  }

  & strong {
    color: var(--ink);
  }
}

/* ── Quantile table ── */
.table-scroll {
  overflow-x: auto;
}

.qtable {
  width: 100%;
  min-width: 620px;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;

  & th,
  & td {
    padding: 0.6rem 0.5rem;
    font-size: 0.88rem;
    text-align: right;
  }

  & thead th {
    border-bottom: 1px solid var(--hairline);
    color: var(--ink-muted);
    font-size: 0.78rem;
    font-weight: 400;
  }

  & thead th:first-child,
  & tbody th {
    text-align: left;
  }

  & tbody th {
    font-weight: 700;
  }

  & tbody tr + tr > * {
    border-top: 1px solid var(--hairline);
  }
}

/* ── County list ── */
.ranklist {
  margin: 0;
  padding: 0;
  list-style: none;
}

.rank-row {
  display: grid;
  grid-template-columns: 2.2rem minmax(0, 1fr) auto 5.5rem 5.5rem;
  align-items: baseline;
  gap: 0.75rem;
  padding: 0.55rem 0.5rem;
  border-bottom: 1px solid var(--hairline);
  font-variant-numeric: tabular-nums;

  &:last-child {
    border-bottom: 0;
  }

  & .rk,
  & .sh {
    color: var(--ink-muted);
    font-size: 0.78rem;
  }

  & .v1,
  & .v2 {
    font-size: 0.9rem;
    text-align: right;
  }

  & .v2 {
    color: var(--ink-secondary);
  }

  &.hot .v2 {
    color: var(--accent-text);
    font-weight: 700;
  }
}

@media (max-width: 900px) {
  .warn-cols {
    grid-template-columns: minmax(0, 1fr);
    gap: 1.25rem;
  }

  .warn-col .status {
    margin-top: 0;
  }

  .applied {
    width: 100%;
    margin-left: 0;
    text-align: left;
  }

  .rank-row {
    grid-template-columns: 2rem minmax(0, 1fr) 4.6rem 4.6rem;

    & .sh {
      display: none;
    }
  }
}

@media (max-width: 520px) {
  .warncard,
  .acard {
    padding: 1.1rem;
  }

  .field {
    width: 100%;
  }
}
</style>
