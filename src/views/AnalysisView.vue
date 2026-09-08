<script setup lang="ts">
/** Duration analysis: histogram + KDE, and an ECDF comparing 狗 with 貓.
 *
 *  The page is built around one caveat rather than decorated with it. Every
 *  animal here is still in a shelter, so the numbers describe who is currently
 *  inside, not how long a stay lasts — and the second chart exists so the
 *  quotable figures come from a curve with no bandwidth in it.
 */
import { computed, onMounted, ref } from 'vue'
import { fetchDistribution, useAtlasData } from '@/composables/useAtlasData'
import CountyTable from '@/components/CountyTable.vue'
import DistributionChart from '@/components/DistributionChart.vue'
import EcdfChart from '@/components/EcdfChart.vue'
import type { CountyStats, DistributionPayload, Metric, Scale, Scope, Smoothing } from '@/types'

const data = ref<DistributionPayload | null>(null)
const error = ref<string | null>(null)

const scope = ref<Scope>('all')
const scale = ref<Scale>('log')
const smoothing = ref<Smoothing>('standard')

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

onMounted(async () => {
  try {
    data.value = await fetchDistribution()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  }
})

const current = computed(() => data.value?.scopes[scope.value] ?? null)
const block = computed(() => (current.value ? current.value[scale.value] : null))

/** Stated beside the controls: the bandwidth is the one setting whose effect
 *  on the curve is invisible until it is named. */
const curveBandwidth = computed(() => block.value?.kde[smoothing.value].bandwidth ?? 0)

const scopeColour = computed(() =>
  scope.value === 'cat' ? 'var(--series-b)' : 'var(--series-a)',
)

const ecdfSeries = computed(() => {
  if (!data.value) return []
  return [
    {
      key: 'dog',
      label: '狗',
      colour: 'var(--series-a)',
      points: data.value.scopes.dog.ecdf,
    },
    {
      key: 'cat',
      label: '貓',
      colour: 'var(--series-b)',
      points: data.value.scopes.cat.ecdf,
    },
  ]
})

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function years(days: number): string {
  return `約 ${(days / 365).toFixed(1)} 年`
}

/* ---------------------------------------------------------- county rank --
 * Moved off the map page. There it sat beside the choropleth and said the
 * same thing in a second form, while the map wanted the width; here it is one
 * more way of reading the same distribution, which is what this page is for.
 */
const { stats } = useAtlasData()
const rankMetric = ref<Metric>('count')
const RANK_METRICS: { id: Metric; label: string }[] = [
  { id: 'count', label: '在所數' },
  { id: 'median', label: '滯留中位數' },
]

function rankValue(county: CountyStats): number | null {
  if (rankMetric.value === 'count') return county.all.count
  // A median over a handful of animals is noise, not a signal.
  return county.all.count >= 20 ? county.all.median_days : null
}

/** Every row carries both numbers: sorting by one and printing only that one
 *  hides the fact that the two disagree — 桃園市 is fourth by headcount and
 *  first by median. The accent marks a median at least twice the national one,
 *  which is a stated rule rather than a judgement about the county. */
const rankRows = computed(() => {
  if (!stats.value) return []
  const national = stats.value.total.median_days ?? 0
  return stats.value.counties
    .map((county) => ({
      county,
      value: rankValue(county),
      sub:
        rankMetric.value === 'count'
          ? county.all.median_days === null
            ? '—'
            : `${county.all.median_days.toLocaleString('zh-TW')} 天`
          : `${county.all.count.toLocaleString('zh-TW')} 隻`,
      alert:
        rankMetric.value === 'count' &&
        national > 0 &&
        (county.all.median_days ?? 0) >= national * 2,
    }))
    .sort((a, b) => (b.value ?? -1) - (a.value ?? -1))
})

const rankMax = computed(() => Math.max(...rankRows.value.map((row) => row.value ?? 0), 0))
</script>

<template>
  <section class="page">
    <header class="intro">
      <h2>在所天數分佈</h2>
      <p>
        這一頁只回答一個問題：<strong>此刻還在收容所裡的動物，已經待了多久</strong>。它不是「一隻動物會待多久」的分佈——那需要離所事件，而這份資料看不到。
      </p>
    </header>

    <p v-if="error" class="state">分佈資料載入失敗：{{ error }}</p>
    <p v-else-if="!current || !block" class="state">載入中…</p>

    <template v-else>
      <!-- Three columns, each naming its statistical term in English as well.
           A reader who knows the term can stop after the heading; one who does
           not gets the sentence — and the term is the thing they would need to
           look it up. -->
      <div class="caveat card">
        <div class="caveat-head">
          <span class="caveat-tag"><span aria-hidden="true">⚠</span> 方法學指引與資料邊界</span>
          <span class="caveat-mark">DATA BOUNDARY &amp; BIAS</span>
        </div>
        <h3>為什麼不能把這張圖讀成「停留時間」</h3>
        <p class="caveat-lead">
          這頁呈現的是全臺公立收容所「目前仍在所」動物的截面存量。把這些數字直接讀成「一隻動物平均要待多久才能離開」，會犯下三項統計推論錯誤。
        </p>
        <ol class="caveat-grid">
          <li>
            <span class="caveat-num">01</span>
            <h4>右設限（Right-Censoring）</h4>
            <p>
              每一筆都還在所內，所以天數是「至少待了這麼久」，不是最終停留長度。等於只量到一半就記錄下來。
            </p>
            <p class="caveat-foot">狀態：事件未發生（Censored）</p>
          </li>
          <li>
            <span class="caveat-num">02</span>
            <h4>長度偏誤（Length-Biased Sampling）</h4>
            <p>
              待越久的動物，出現在任何一天快照裡的機率越高。這份樣本天生就過度代表長期滯留者，中位數 {{ current.median_days }} 天高於實際的停留中位數。
            </p>
            <p class="caveat-foot">現象：長期滯留個體被過度代表</p>
          </li>
          <li>
            <span class="caveat-num">03</span>
            <h4>正確工具：存活分析（Survival Analysis）</h4>
            <p>
              需要「離開」這個事件，階段 3 會用連續快照相減把它還原出來；在那之前，這頁只描述族群組成。
            </p>
            <p class="caveat-foot">解方：需要隊列歷程資料（Cohort）</p>
          </li>
        </ol>
      </div>

      <div class="controls">
        <fieldset>
          <legend>對象</legend>
          <button
            v-for="option in SCOPES"
            :key="option.id"
            type="button"
            :class="{ chip: true, on: scope === option.id }"
            :aria-pressed="scope === option.id"
            @click="scope = option.id"
          >
            {{ option.label }}
          </button>
        </fieldset>

        <fieldset>
          <legend>橫軸</legend>
          <button
            v-for="option in SCALES"
            :key="option.id"
            type="button"
            :class="{ chip: true, on: scale === option.id }"
            :aria-pressed="scale === option.id"
            @click="scale = option.id"
          >
            {{ option.label }}
          </button>
        </fieldset>

        <fieldset>
          <legend>平滑程度</legend>
          <button
            v-for="option in SMOOTHINGS"
            :key="option.id"
            type="button"
            :class="{ chip: true, on: smoothing === option.id }"
            :aria-pressed="smoothing === option.id"
            @click="smoothing = option.id"
          >
            {{ option.label }}
          </button>
        </fieldset>

        <!-- What the controls above currently add up to. Three chip groups can
             be read four ways; this states the answer once. -->
        <p class="applied">
          已套用：{{ SCOPES.find((s) => s.id === scope)?.label }}（{{
            current.count.toLocaleString('zh-TW')
          }} 隻）・{{ scale === 'log' ? '對數軸' : '線性軸' }}・頻寬 {{ curveBandwidth }}
        </p>
      </div>

      <section class="card">
        <div class="card-head">
          <div>
            <h3><span class="dot" aria-hidden="true" />長條圖與核密度估計</h3>
            <p class="card-sub">中位數以虛線標示・{{ scale === 'log' ? '對數' : '線性' }}橫軸</p>
          </div>
          <span class="hint">
            中位數 {{ current.median_days.toLocaleString('zh-TW') }} 天（P50）
          </span>
        </div>

        <DistributionChart
          :block="block"
          :scale="scale"
          :smoothing="smoothing"
          :log-ticks="data!.log_ticks"
          :max-days="current.max_days"
          :median="current.median_days"
          :colour="scopeColour"
        />

        <div class="note">
          <h4 class="note-title">數據判讀與尺度邊界</h4>
          <p>
          <template v-if="scale === 'log'">
            對數軸下可以看見兩個隆起：一個在一年以內，一個在數年之後，中間有明顯凹陷。這是「數量級」上的雙峰——換成線性軸，密度是單調遞減的長尾，沒有第二個峰。兩張圖是同一組數字，說的是不同層次的事，所以兩個都放在這裡讓你切換。
          </template>
          <template v-else>
            線性軸上密度單調遞減，全部結構被壓在最前面幾百天。這才是「天數」尺度下的真相；切到對數軸看的是數量級尺度下的結構。
          </template>
          </p>
          <p>
            切換平滑程度會改變結論：頻寬夠窄時每個小起伏都變成一個峰，夠寬時第二個峰整個消失。狗的雙峰撐得過「標準」但撐不過「較平滑」，貓在「較平滑」下則收斂成單峰。一個經得起平滑的結構才值得下結論。
          </p>
        </div>
      </section>

      <section class="card">
        <div class="card-head">
          <div>
            <h3><span class="dot" aria-hidden="true" />累積分佈：狗與貓</h3>
            <p class="card-sub">無頻寬、無平滑假設・階梯式累積經驗分佈</p>
          </div>
          <span class="hint">
            狗 {{ data!.scopes.dog.count.toLocaleString('zh-TW') }}・貓
            {{ data!.scopes.cat.count.toLocaleString('zh-TW') }}
          </span>
        </div>

        <EcdfChart
          :series="ecdfSeries"
          :max-days="Math.max(data!.scopes.dog.max_days, data!.scopes.cat.max_days)"
          :ticks="data!.log_ticks"
        />

        <div class="note">
          <h4 class="note-title">階梯曲線判讀指引</h4>
          <p>
          兩條線分得很開，而且沒有交叉：在任何一個天數以內，貓的累積比例都高於狗。狗的在所中位數是 {{ data!.scopes.dog.median_days.toLocaleString('zh-TW') }} 天，貓是 {{ data!.scopes.cat.median_days.toLocaleString('zh-TW') }} 天；待超過一年的比例，狗 {{ pct(data!.scopes.dog.over_year) }}、貓 {{ pct(data!.scopes.cat.over_year) }}。這些數字直接讀自這條曲線，不經過任何平滑。
          </p>
        </div>
      </section>

      <section class="card">
        <div class="card-head">
          <div>
            <h3><span class="dot" aria-hidden="true" />分位數</h3>
            <p class="card-sub">主要指標分佈統計（天數與長期滯留比例）</p>
          </div>
          <span class="hint">單位：天數／佔該群體比例</span>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">對象</th>
                <th scope="col">隻數</th>
                <th scope="col">P25</th>
                <th scope="col">中位數</th>
                <th scope="col">P75</th>
                <th scope="col">P90</th>
                <th scope="col">超過 1 年</th>
                <th scope="col">超過 4 年</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="option in SCOPES" :key="option.id">
                <th scope="row">{{ option.label }}</th>
                <td>{{ data!.scopes[option.id].count.toLocaleString('zh-TW') }}</td>
                <td>{{ data!.scopes[option.id].p25_days.toLocaleString('zh-TW') }}</td>
                <td class="lead">
                  {{ data!.scopes[option.id].median_days.toLocaleString('zh-TW') }}
                  <span>{{ years(data!.scopes[option.id].median_days) }}</span>
                </td>
                <td>{{ data!.scopes[option.id].p75_days.toLocaleString('zh-TW') }}</td>
                <td>{{ data!.scopes[option.id].p90_days.toLocaleString('zh-TW') }}</td>
                <td>{{ pct(data!.scopes[option.id].over_year) }}</td>
                <td>{{ pct(data!.scopes[option.id].over_4_years) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="note">
          <h4 class="note-title">偏態分布判讀重點</h4>
          <p>
            這份分布是右偏的：極端的長期滯留個體會把平均數拉高，使平均值失去中心代表性，因此表格以中位數為主。表格同時是圖表之外的替代讀法——每個數字都能被複製與查證，不必靠辨色。
          </p>
        </div>
      </section>

      <section v-if="rankRows.length" class="card">
        <div class="card-head">
          <div>
            <h3>
              <span class="dot" aria-hidden="true" />各縣市{{
                rankMetric === 'count' ? '在所數' : '滯留中位數'
              }}排行
            </h3>
            <p class="rank-sub">公立動物收容設施之即時盤點存量排序</p>
          </div>
          <fieldset>
            <button
              v-for="option in RANK_METRICS"
              :key="option.id"
              type="button"
              :class="{ chip: true, small: true, on: rankMetric === option.id }"
              :aria-pressed="rankMetric === option.id"
              @click="rankMetric = option.id"
            >
              {{ option.label }}
            </button>
          </fieldset>
        </div>
        <CountyTable
          :rows="rankRows"
          :metric="rankMetric"
          :max="rankMax"
          :selected="null"
          ranked
        />
        <div class="note">
          <h4 class="note-title">縣市排行資料背景與口徑差異</h4>
          <p>
            縣市指的是收容動物的收容所所在地，不是動物被尋獲的地點——只有 2.4% 的紀錄自己寫出縣市，其中還有十二筆與收容它的收容所不同縣市。
          </p>
          <p>
            在所數是存量不是流量：高在所數可能來自收容空間充裕，低在所數也可能是硬體已滿而嚴格控管入所，兩者無法由長度區分。右側的中位數以強調色標出高於全國中位數兩倍者，代表該縣市在所動物有一半已待超過該天數；這些數字不足以評價地方主管機關的作為。
          </p>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.intro h2 {
  font-size: 1.15rem;
  margin: 0 0 0.4rem;
}

.intro p {
  margin: 0;
  max-width: 62ch;
  font-size: 0.92rem;
  line-height: 1.75;
  color: var(--ink-secondary);
}

.state {
  margin: 0;
  color: var(--ink-muted);
}

/* Not a footnote. The whole page is only honest if this is read first, so it
   sits above the charts rather than under them. */
.caveat {
  background: var(--surface-sunk);
}

.caveat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.7rem;
}

.caveat-tag {
  font-size: 0.75rem;
  color: var(--accent-text);
  border: 1px solid var(--hairline);
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  background: var(--surface);
  white-space: nowrap;
}

.caveat-mark {
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  color: var(--ink-muted);
  white-space: nowrap;
}

.caveat h3 {
  font-size: 1.05rem;
  margin: 0 0 0.5rem;
}

.caveat-lead {
  margin: 0 0 1rem;
  max-width: 74ch;
  font-size: 0.85rem;
  line-height: 1.8;
  color: var(--ink-secondary);
}

/* Three columns rather than a numbered list. Each caveat is a self-contained
   claim, and stacking them made the third one read as an afterthought. */
.caveat-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  background: var(--hairline);
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  overflow: hidden;
}

.caveat-grid > li {
  display: flex;
  flex-direction: column;
  background: var(--surface);
  padding: 0.9rem 1rem 0.8rem;
}

.caveat-num {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--accent-text);
  font-variant-numeric: tabular-nums;
}

.caveat-grid h4 {
  margin: 0.15rem 0 0.5rem;
  font-size: 0.9rem;
}

.caveat-grid p {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.8;
  color: var(--ink-secondary);
}

/* Pushed to the bottom so the three footers line up however long the
   paragraphs above them run. */
.caveat-foot {
  margin-top: auto !important;
  padding-top: 0.7rem;
  border-top: 1px solid var(--hairline);
  font-size: 0.74rem !important;
  color: var(--ink-muted) !important;
}

@media (max-width: 860px) {
  .caveat-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

.controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1.75rem;
}

/* The applied-scope readout sits at the far end of the control row. */
.controls .applied {
  margin-left: auto;
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

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.9rem;
}

.card-head h3 {
  font-size: 1rem;
  margin: 0;
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

/* The notes carry a heading now. Unlabelled grey paragraphs under a chart get
   read as a caption and skipped, and on this page they are the argument. */
.note {
  margin: 1rem 0 0;
  padding: 0.85rem 1rem;
  background: var(--surface-sunk);
  border-radius: var(--radius);
}

.note-title {
  margin: 0 0 0.4rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ink-secondary);
}

.note p {
  margin: 0;
  max-width: 76ch;
  font-size: 0.82rem;
  line-height: 1.85;
  color: var(--ink-muted);
}

.note p + p {
  margin-top: 0.6rem;
}

.card-sub {
  margin: 0.15rem 0 0;
  font-size: 0.78rem;
  color: var(--ink-muted);
}

.applied {
  margin: 0;
  font-size: 0.78rem;
  color: var(--ink-muted);
  font-variant-numeric: tabular-nums;
}

.rank-sub {
  margin: 0.15rem 0 0;
  font-size: 0.78rem;
  color: var(--ink-muted);
}

.table-scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
}

th,
td {
  text-align: right;
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid var(--hairline);
  white-space: nowrap;
}

thead th {
  font-weight: 600;
  color: var(--ink-muted);
  font-size: 0.78rem;
}

tbody th {
  text-align: left;
  font-weight: 600;
}

.lead span {
  display: block;
  font-size: 0.72rem;
  font-weight: 400;
  color: var(--ink-muted);
}
</style>
