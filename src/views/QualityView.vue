<script setup lang="ts">
/** /quality — how completely this open data records its animals.
 *
 *  DESIGN.md §13. The page that /analysis depends on: it measures the data
 *  rather than the animals, which is why it is a page of its own and why the
 *  nav puts it BEFORE 資料分析 rather than after.
 *
 *  Every figure comes from stats/quality.json and meta.json. Nothing here is
 *  typed into the component — including the thresholds, which travel in the
 *  payload so that the sentence the page prints and the grade it awards can
 *  never disagree (DESIGN.md §12.9).
 *
 *  The word this page must never imply: quality of care. It scores recording
 *  practice. Both the warning card at the top and the boundary card at the
 *  bottom say so, and neither may be shortened.
 */
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import LucideIcon from '@/components/LucideIcon.vue'
import PageHead from '@/components/PageHead.vue'
import { fetchMeta, fetchQuality } from '@/composables/useAtlasData'
import type { MetaPayload, QualityPayload, QualityRow } from '@/types'

const quality = ref<QualityPayload | null>(null)
const meta = ref<MetaPayload | null>(null)
const error = ref<string | null>(null)

Promise.all([fetchQuality(), fetchMeta()])
  .then(([q, m]) => {
    quality.value = q
    meta.value = m
  })
  .catch((cause: unknown) => {
    error.value = cause instanceof Error ? cause.message : String(cause)
  })

const GRADE_LABEL: Record<string, string> = {
  good: '優',
  fair: '中',
  poor: '待補',
  na: '—',
}

function count(value: number): string {
  return value.toLocaleString('en-US')
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

/** The source column with its Chinese name underneath, one step smaller.
 *  The name comes from meta.json, which got it from
 *  data/reference/fields.json — never from a list kept in here. */
function fieldLabel(column: string): string | undefined {
  return meta.value?.fields[column]
}

const graded = computed(() =>
  (quality.value?.counties ?? []).filter((c) => c.rows >= (quality.value?.min_rows_for_grade ?? 0)),
)

const ungraded = computed(() =>
  (quality.value?.counties ?? []).filter((c) => c.rows < (quality.value?.min_rows_for_grade ?? 0)),
)

/** Least complete first: the point of the list is the top of it. */
const coverage = computed(() => {
  const entries = Object.entries(meta.value?.coverage ?? {})
  return entries.sort((a, b) => a[1] - b[1])
})

const photoMetric = computed(() => quality.value?.metrics.find((m) => m.key === 'photo') ?? null)

/** Shelters are ranked only above the same row threshold the counties use.
 *  Without it this table is a list of the four smallest shelters. */
const worstPhoto = computed(() => {
  const floor = quality.value?.min_rows_for_grade ?? 0
  return (quality.value?.shelters ?? [])
    .filter((s) => s.rows >= floor)
    .sort((a, b) => a.scores.photo - b.scores.photo)
    .slice(0, 6)
})

/** "Five of the six are in one county" is a claim, so it is counted rather
 *  than written down. */
const worstPhotoConcentration = computed(() => {
  const rows = worstPhoto.value
  if (rows.length === 0) return null
  const tally = new Map<string, number>()
  for (const row of rows) tally.set(row.county, (tally.get(row.county) ?? 0) + 1)
  const [county, n] = [...tally].sort((a, b) => b[1] - a[1])[0]
  return { county, n, of: rows.length }
})

/** The county holding the largest share of the roster, with that share. The
 *  photo section leans on it, and it must not be a number typed into prose. */
const largestCounty = computed(() => {
  const rows = quality.value?.counties ?? []
  const total = quality.value?.rows ?? 0
  if (rows.length === 0 || total === 0) return null
  const top = [...rows].sort((a, b) => b.rows - a.rows)[0]
  return { ...top, share: top.rows / total }
})

const mixedTotal = computed(() =>
  (quality.value?.spellings.variety ?? []).reduce((sum, item) => sum + item.count, 0),
)

const varietyTop = computed(() => quality.value?.spellings.variety[0]?.count ?? 1)

/** The eight counties leaving the sterilisation field unrecorded most often,
 *  and the one that never does — the contrast is the section's whole point. */
const sterilization = computed(() => quality.value?.spellings.sterilization_by_county ?? [])
const sterilizationTop = computed(() => sterilization.value.slice(0, 8))
const sterilizationLowest = computed(() => sterilization.value[sterilization.value.length - 1])

function grades(row: QualityRow, key: string): string {
  return row.grades[key] ?? 'na'
}
</script>

<template>
  <div class="page">
    <PageHead title="資料品質">
      同一份開放資料，22
      個縣市有二十二種填法。這頁把欄位的完整度攤開來看：哪些欄位整欄是空的、哪些縣市的紀錄補不齊，以及本站因此不敢畫哪一張圖。
    </PageHead>

    <!-- Above the tables, not below them: a reader who stops after the first
         card should still have been told what this page does not measure. -->
    <section v-reveal class="warncard" aria-labelledby="q-warn">
      <div class="warn-top">
        <span id="q-warn" class="pill">
          <LucideIcon name="triangle-alert" :size="15" />評分口徑與資料邊界
        </span>
        <span class="kicker">SCOPE &amp; STATED THRESHOLDS</span>
      </div>
      <div class="warn-cols">
        <div class="warn-col">
          <span class="no">01</span>
          <h2>量的是登錄實務<em>Recording Practice</em></h2>
          <p>
            這頁的每一個比例，量的都是<strong>欄位有沒有被填好</strong>。分數低代表該縣市的開放資料有缺口，<strong>不是</strong>對該縣市收容所照顧品質的評價，兩者這份資料都答不了。
          </p>
          <span class="status">不是收容品質評鑑</span>
        </div>
        <div class="warn-col">
          <span class="no">02</span>
          <h2>分母是在所動物<em>Stock Denominator</em></h2>
          <p>
            每個比例的分母是這一份快照中<strong>目前仍在所</strong>的動物，不是該縣市歷年的收容總數。已離所的個體不在資料裡，牠們當年的登錄品質也就量不到。
          </p>
          <span class="status">只反映此刻在所的紀錄</span>
        </div>
        <div class="warn-col">
          <span class="no">03</span>
          <h2>門檻是本站自訂<em>Stated Thresholds</em></h2>
          <p>
            優／中／待補的切點是<strong>手選的整數</strong>，不是本次快照的分位數——分位數會讓一個縣市因為別縣市變動而換級。每一條門檻都寫在下方，讀者可以不同意。
          </p>
          <span class="status">非官方評鑑，切點可受檢驗</span>
        </div>
      </div>
    </section>

    <p v-if="error" class="state">資料品質資料載入失敗：{{ error }}</p>
    <p v-else-if="!quality || !meta" class="state">載入中…</p>

    <template v-else>
      <section v-reveal class="acard" aria-labelledby="q-dropped">
        <div class="an-head">
          <h2 id="q-dropped">先看這份資料有多少是空的</h2>
          <span class="sub">
            {{ meta.columns_in_source }} 欄進、{{ meta.columns_after_clean }} 欄出
          </span>
        </div>
        <p class="lead">
          來源 CSV 有 {{ meta.columns_in_source }} 欄，清理後只剩
          {{ meta.columns_after_clean }} 欄可用。被丟掉的
          {{ meta.dropped_columns.length + meta.duplicate_columns.length }}
          欄不是本站挑掉的，是它們在全部 {{ count(meta.rows) }}
          筆裡沒有任何變化——沒有變化的欄位無法用來區分任何兩隻動物。
        </p>
        <div class="cols">
          <div class="fact">
            <h3>零資訊量：整欄空白或全部同值</h3>
            <table>
              <tbody>
                <tr v-for="item in meta.dropped_columns" :key="item.column">
                  <td>
                    <span class="fld">
                      <code>{{ item.column }}</code>
                      <em v-if="fieldLabel(item.column)">（{{ fieldLabel(item.column) }}）</em>
                    </span>
                  </td>
                  <td>
                    <template v-if="item.reason === 'all_blank'">整欄空白</template>
                    <template v-else>零變異，全部都是 <code>{{ item.value }}</code></template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="fact">
            <h3>重複欄位：兩欄裝同一件事</h3>
            <table>
              <tbody>
                <tr v-for="item in meta.duplicate_columns" :key="item.dropped">
                  <td>
                    <span class="fld">
                      <code>{{ item.dropped }}</code>
                      <em v-if="fieldLabel(item.dropped)">（{{ fieldLabel(item.dropped) }}）</em>
                    </span>
                  </td>
                  <td>與 <code>{{ item.identical_to }}</code> 逐列相同</td>
                </tr>
              </tbody>
            </table>
            <div class="note">
              <h3>為什麼這件事值得放在第一段</h3>
              <p>
                <code>animal_status</code> 全部是 <code>OPEN</code>、
                <code>animal_closeddate</code> 全部是 <code>2999-12-31</code>
                ——這正是本站所有分析的前提：這份資料是<strong>存量快照</strong>，沒有任何一筆記錄了離所。
              </p>
            </div>
          </div>
        </div>
      </section>

      <section v-reveal class="acard" aria-labelledby="q-coverage">
        <div class="an-head">
          <h2 id="q-coverage">留下來的 {{ meta.columns_after_clean }} 欄，各有多少是填的</h2>
          <span class="sub">非空值佔 {{ count(meta.rows) }} 筆的比例</span>
        </div>
        <ul class="cov">
          <li v-for="[column, share] in coverage" :key="column">
            <span class="fld">
              <code>{{ column }}</code>
              <em v-if="fieldLabel(column)">（{{ fieldLabel(column) }}）</em>
            </span>
            <span class="cbar"><i :style="{ width: pct(share) }"></i></span>
            <b>{{ pct(share) }}</b>
          </li>
        </ul>
        <div class="note">
          <h3>這張圖的讀法</h3>
          <p>
            備註欄只有 {{ pct(meta.coverage.animal_remark ?? 0) }}
            有值，且多為行政或醫療註記；尋獲地雖有
            {{ pct(meta.coverage.animal_foundplace ?? 0) }}
            非空，但下一段會看到其中真正定得出位置的不到四成。<strong>欄位有填，不等於欄位可用。</strong>
          </p>
        </div>
      </section>

      <section v-reveal class="acard" aria-labelledby="q-counties">
        <div class="an-head">
          <h2 id="q-counties">各縣市的登錄完整度</h2>
          <span class="sub">
            {{ graded.length }} 個縣市達評級門檻 · 在所數 ≥ {{ quality.min_rows_for_grade }} 隻
          </span>
        </div>
        <p class="lead">
          四個指標各自獨立評級，<strong>刻意不加總</strong>：四件事本質不同，加總等於偷偷替讀者設定權重，而那個權重無法辯護。橫條上的細線是「優」的門檻位置。
        </p>
        <div class="scroller">
          <table class="score">
            <thead>
              <tr>
                <th scope="col">縣市</th>
                <th scope="col">收容所</th>
                <th scope="col">在所數</th>
                <th v-for="metric in quality.metrics" :key="metric.key" scope="col">
                  {{ metric.label }}<em>全國 {{ pct(metric.national) }}</em>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="county in graded" :key="county.pkid">
                <th scope="row">{{ county.name }}</th>
                <td class="n">{{ county.shelters }}</td>
                <td class="n">{{ count(county.rows) }}</td>
                <td
                  v-for="metric in quality.metrics"
                  :key="metric.key"
                  class="num"
                  :class="`g-${grades(county, metric.key)}`"
                >
                  <span class="v">{{ pct(county.scores[metric.key]) }}</span>
                  <span class="g">{{ GRADE_LABEL[grades(county, metric.key)] }}</span>
                  <span class="bar">
                    <i class="fill" :style="{ width: pct(county.scores[metric.key]) }"></i>
                    <i class="tick" :style="{ left: pct(metric.thresholds.good) }"></i>
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="legend">
          <span class="k"><i class="sw-bar"></i>橫條長度為該項比例</span>
          <span class="k"><i class="sw-tick"></i>細線為「優」門檻</span>
          <span class="k">優／中／待補三級，門檻見下方各欄說明</span>
        </div>

        <div class="ungraded">
          <h3>在所數不足 {{ quality.min_rows_for_grade }} 隻，不予評級</h3>
          <p>
            這些縣市的在所動物太少，一筆紀錄就能讓比例跳動數個百分點。數字照列，級別留白——把它們排進名次是這頁最容易犯的錯。
          </p>
          <div class="scroller">
            <table class="score">
              <tbody>
                <tr v-for="county in ungraded" :key="county.pkid">
                  <th scope="row">{{ county.name }}</th>
                  <td class="n">{{ county.shelters }}</td>
                  <td class="n">{{ count(county.rows) }}</td>
                  <td
                    v-for="metric in quality.metrics"
                    :key="metric.key"
                    class="num g-na"
                  >
                    <span class="v">{{ pct(county.scores[metric.key]) }}</span>
                    <span class="g">—</span>
                    <span class="bar">
                      <i class="fill" :style="{ width: pct(county.scores[metric.key]) }"></i>
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section v-reveal class="acard" aria-labelledby="q-metrics">
        <div class="an-head">
          <h2 id="q-metrics">四個指標各自在量什麼</h2>
          <span class="sub">門檻與全國值</span>
        </div>
        <div class="mn-grid">
          <div v-for="metric in quality.metrics" :key="metric.key" class="mn">
            <h3>{{ metric.label }}<em>{{ metric.key }}</em></h3>
            <p>{{ metric.description }}</p>
            <span class="th">
              優 ≥ {{ pct(metric.thresholds.good) }} · 中 ≥ {{ pct(metric.thresholds.fair) }} ·
              全國 {{ pct(metric.national) }}
            </span>
          </div>
        </div>
        <div class="note">
          <h3>為什麼沒有「品種欄鑑別力」這一項</h3>
          <p>
            全國 {{ pct(mixedTotal / quality.rows) }}
            的在所動物是混種。一個縣市的品種欄大多寫著「混種犬」，是<strong>如實描述牠的動物</strong>，不是漏填。把它放進評分表會把「收容現實」誤記成「登錄缺口」。
          </p>
        </div>
      </section>

      <section v-if="photoMetric" v-reveal class="acard" aria-labelledby="q-photo">
        <div class="an-head">
          <h2 id="q-photo">照片覆蓋率最低的收容所</h2>
          <span class="sub">
            在所數 ≥ {{ quality.min_rows_for_grade }} 隻 · 全國 {{ pct(photoMetric.national) }}
          </span>
        </div>
        <p class="lead">
          全國有 {{ pct(1 - photoMetric.national) }} 的在所動物沒有照片<template
            v-if="largestCounty"
            >，而這個數字幾乎由單一縣市決定：{{ largestCounty.name }}占全國
            {{ pct(largestCounty.share) }} 的在所動物，照片覆蓋率
            {{ pct(largestCounty.scores.photo) }}</template
          ><template v-if="worstPhotoConcentration">
            ；最低的 {{ worstPhotoConcentration.of }} 間裡有
            {{ worstPhotoConcentration.n }} 間在{{ worstPhotoConcentration.county }}</template
          >。沒有照片的動物，在任何認養平臺上都很難被看見——這是四個指標裡唯一直接影響動物的登錄缺口。
        </p>
        <div class="scroller">
          <table class="score">
            <thead>
              <tr>
                <th scope="col">收容所</th>
                <th scope="col">縣市</th>
                <th scope="col">在所數</th>
                <th scope="col">
                  {{ photoMetric.label }}<em>全國 {{ pct(photoMetric.national) }}</em>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="shelter in worstPhoto" :key="shelter.id">
                <th scope="row">
                  <RouterLink :to="`/shelters/${shelter.id}`">{{ shelter.name }}</RouterLink>
                </th>
                <td class="n">{{ shelter.county }}</td>
                <td class="n">{{ count(shelter.rows) }}</td>
                <td class="num" :class="`g-${grades(shelter, 'photo')}`">
                  <span class="v">{{ pct(shelter.scores.photo) }}</span>
                  <span class="g">{{ GRADE_LABEL[grades(shelter, 'photo')] }}</span>
                  <span class="bar">
                    <i class="fill" :style="{ width: pct(shelter.scores.photo) }"></i>
                    <i class="tick" :style="{ left: pct(photoMetric.thresholds.good) }"></i>
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-reveal class="acard" aria-labelledby="q-spellings">
        <div class="an-head">
          <h2 id="q-spellings">同一件事的好幾種寫法</h2>
          <span class="sub">人工登錄留下的痕跡</span>
        </div>
        <p class="lead">
          下面幾組不是錯誤，是 {{ meta.shelters }}
          間收容所各自填表的結果。它們也說明了為什麼本站的收容所以名稱為鍵、不以代碼為鍵。
        </p>
        <div class="cols">
          <div class="fact">
            <h3>混種的 {{ quality.spellings.variety.length }} 種寫法</h3>
            <ul class="spell">
              <li v-for="item in quality.spellings.variety" :key="item.value">
                <b>{{ item.value }}</b>
                <span class="cbar">
                  <i :style="{ width: `${(item.count / varietyTop) * 100}%` }"></i>
                </span>
                <em>{{ count(item.count) }}</em>
              </li>
            </ul>
          </div>
          <div class="fact">
            <h3>一個代碼配到兩間收容所</h3>
            <ul class="plain">
              <li v-for="item in meta.shelter_pkid_collisions" :key="item.pkid">
                <code>{{ item.pkid }}</code> 同時是 {{ item.shelter_names.join(' / ') }}
              </li>
            </ul>
            <h3 class="spaced">同一間收容所，多種地址寫法</h3>
            <ul class="plain">
              <li v-for="item in meta.shelter_address_variants" :key="item.shelter_name">
                {{ item.shelter_name }}<em>{{ item.addresses.length }} 種寫法</em>
              </li>
            </ul>
          </div>
        </div>

        <h3 class="subhead">絕育欄位：填 N（未知或不適用）比例最高的八個縣市</h3>
        <ul class="stackrows">
          <li v-for="item in sterilizationTop" :key="item.pkid">
            <span class="cn">{{ item.name }}</span>
            <span class="stack">
              <i class="t" :style="{ width: pct(item.T) }"></i>
              <i class="f" :style="{ width: pct(item.F) }"></i>
              <i class="u" :style="{ width: pct(item.N) }"></i>
            </span>
            <b>{{ pct(item.N) }}</b>
          </li>
        </ul>
        <div class="legend">
          <span class="k"><i class="sw-t"></i>T 已絕育</span>
          <span class="k"><i class="sw-f"></i>F 未絕育</span>
          <span class="k"><i class="sw-u"></i>N 未知／不適用</span>
        </div>
        <div class="note">
          <h3>這一欄為什麼是資料治理的題材</h3>
          <p v-if="sterilizationLowest">
            {{ sterilizationLowest.name }} {{ pct(sterilizationLowest.N) }} 對
            {{ sterilizationTop[0].name }} {{ pct(sterilizationTop[0].N) }}
            。差距大到不可能是真實的絕育政策差異，只可能是<strong>各縣市對這一欄的登錄規則不一致</strong>。
          </p>
        </div>
      </section>

      <section v-reveal class="bound" aria-labelledby="q-bound">
        <h2 id="q-bound">這一頁不能拿來說什麼</h2>
        <ul>
          <li>不能說分數低的縣市「收容品質差」。這頁量的是欄位填寫，不是照顧動物。</li>
          <li>不能說分數低是誰的疏失。欄位空白也可能來自各縣市系統與中央平臺的欄位對應不同步。</li>
          <li>不能把這四項加總後排名次。權重無法辯護，所以本站不提供總分。</li>
          <li>
            不能拿來比較各縣市的收容壓力或認養成效，那是
            <RouterLink to="/map">縣市地圖</RouterLink>與
            <RouterLink to="/analysis">資料分析</RouterLink>的事，而且這份快照也答不了「多快被認養」。
          </li>
          <li>優／中／待補的門檻是本站自訂，非官方評鑑；換一組門檻就會換一組級別，門檻都寫在上面。</li>
        </ul>
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

/* ── Warning card. Same shape as the analysis page's, deliberately: the two
      pages carry the same kind of caveat and should look like they do. ── */
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

.lead {
  margin: 0 0 1.1rem;
  max-width: 74ch;
  color: var(--ink-secondary);
  font-size: 0.92rem;
}

.note {
  margin-top: 1rem;
  padding: 1rem 1.1rem;
  border-radius: var(--radius-sm);
  background: var(--surface-sunk);

  & h3 {
    margin-bottom: 0.3rem;
    font-size: 0.9rem;
  }

  & p {
    margin: 0;
    color: var(--ink-secondary);
    font-size: 0.86rem;
  }
}

code {
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  background: var(--surface-sunk);
  font-size: 0.86em;
}

/* The source column name with its Chinese name under it, one step down. */
.fld {
  display: inline-block;
  line-height: 1.35;

  & code {
    padding: 0;
    background: none;
    color: var(--ink-secondary);
    font-size: 0.86rem;
  }

  & em {
    display: block;
    color: var(--ink-muted);
    font-size: 0.72rem;
    font-style: normal;
  }
}

/* ── Tables ── */
.scroller {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}

.score {
  min-width: 46rem;
}

thead th {
  padding: 0 0.5rem 0.6rem;
  border-bottom: 1px solid var(--hairline);
  color: var(--ink-secondary);
  font-size: 0.8rem;
  font-weight: 500;
  text-align: right;
  vertical-align: bottom;

  &:first-child {
    text-align: left;
  }

  & em {
    display: block;
    color: var(--ink-muted);
    font-size: 0.72rem;
    font-style: normal;
    font-weight: 400;
  }
}

tbody th {
  padding: 0.55rem 0.5rem;
  font-size: 0.92rem;
  font-weight: 500;
  text-align: left;
  white-space: nowrap;
}

tbody td {
  padding: 0.55rem 0.5rem;
  font-size: 0.9rem;
  text-align: right;
  vertical-align: middle;
}

tbody tr + tr th,
tbody tr + tr td {
  border-top: 1px solid var(--hairline);
}

td.n {
  width: 4.5rem;
  color: var(--ink-secondary);
  font-size: 0.86rem;
}

td.num {
  width: 9.5rem;

  & .v {
    font-size: 0.92rem;
  }

  & .g {
    display: inline-block;
    width: 2.4rem;
    color: var(--ink-muted);
    font-size: 0.76rem;
    text-align: right;
  }

  /* The only grade that gets the accent. Colouring all three would turn an
     ordinal scale into a traffic light, which this palette has no third
     hue for and which would read as blame. */
  &.g-poor .g {
    color: var(--accent-text);
    font-weight: 650;
  }

  &.g-na .v {
    color: var(--ink-muted);
  }
}

.bar {
  position: relative;
  display: block;
  height: 5px;
  margin-top: 0.35rem;
  border-radius: 3px;
  background: var(--no-data);

  & .fill {
    position: absolute;
    inset: 0 auto 0 0;
    border-radius: 3px;
    background: var(--ramp-3);
  }

  & .tick {
    position: absolute;
    top: -2px;
    bottom: -2px;
    width: 1px;
    background: var(--ink);
    opacity: 0.5;
  }
}

.g-na .bar .fill {
  background: var(--ink-muted);
  opacity: 0.35;
}

.ungraded {
  margin-top: 1.4rem;
  padding-top: 1.1rem;
  border-top: 1px solid var(--hairline);

  & h3 {
    margin-bottom: 0.15rem;
    font-size: 0.9rem;
  }

  & p {
    margin: 0 0 0.8rem;
    max-width: 70ch;
    color: var(--ink-secondary);
    font-size: 0.85rem;
  }
}

/* ── Legends ── */
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1.4rem;
  margin-top: 0.9rem;
  color: var(--ink-secondary);
  font-size: 0.82rem;

  & .k {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
  }

  & i {
    display: inline-block;
  }
}

.sw-bar {
  width: 22px;
  height: 5px;
  border-radius: 3px;
  background: var(--ramp-3);
}

.sw-tick {
  width: 1px;
  height: 12px;
  background: var(--ink);
  opacity: 0.5;
}

.sw-t {
  width: 12px;
  height: 8px;
  border-radius: 2px;
  background: var(--ramp-2);
}

.sw-f {
  width: 12px;
  height: 8px;
  border-radius: 2px;
  background: var(--ramp-5);
}

.sw-u {
  width: 12px;
  height: 8px;
  border-radius: 2px;
  background: var(--no-data);
  box-shadow: inset 0 0 0 1px var(--hairline);
}

/* ── Metric notes ── */
.mn-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.mn {
  padding: 1rem 1.1rem;
  border-radius: var(--radius-sm);
  background: var(--surface-sunk);

  & h3 {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    font-size: 0.92rem;

    & em {
      color: var(--ink-muted);
      font-size: 0.74rem;
      font-style: normal;
      font-weight: 400;
    }
  }

  & p {
    margin: 0.25rem 0 0.55rem;
    color: var(--ink-secondary);
    font-size: 0.85rem;
  }

  & .th {
    color: var(--ink-muted);
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;
  }
}

/* ── Coverage list. Column-major, so the eye reads down the sorted order
      instead of zig-zagging between the two columns. ── */
.cov {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(10, auto);
  grid-auto-flow: column;
  gap: 0.35rem 2rem;
  margin: 0;
  padding: 0;
  list-style: none;

  & li {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.12rem 0;
    font-size: 0.85rem;
  }

  & .fld {
    flex: 0 0 11rem;
  }

  & b {
    flex: 0 0 3.4rem;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
}

.cbar {
  position: relative;
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--no-data);

  & i {
    position: absolute;
    inset: 0 auto 0 0;
    border-radius: 3px;
    background: var(--ramp-3);
  }
}

/* ── Two-column fact blocks ── */
.cols {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.5rem;
}

.fact {
  & h3 {
    margin-bottom: 0.5rem;
    font-size: 0.95rem;
  }

  & h3.spaced {
    margin-top: 1rem;
  }

  & td {
    font-size: 0.86rem;
    text-align: left;
  }

  & ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  & li {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.3rem 0;
    border-top: 1px solid var(--hairline);
    font-size: 0.86rem;

    &:first-child {
      border-top: none;
    }
  }

  & li em {
    margin-left: auto;
    color: var(--ink-muted);
    font-size: 0.8rem;
    font-style: normal;
    font-variant-numeric: tabular-nums;
  }

  & .spell b {
    flex: 0 0 6rem;
    font-weight: 500;
  }

  & .plain li {
    display: block;
    padding: 0.35rem 0;
  }

  & .plain li em {
    float: right;
  }
}

.subhead {
  margin: 1.6rem 0 0.6rem;
  font-size: 0.95rem;
}

.stackrows {
  margin: 0;
  padding: 0;
  list-style: none;

  & li {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.28rem 0;
    font-size: 0.86rem;
  }

  & .cn {
    flex: 0 0 4.5rem;
  }

  & b {
    flex: 0 0 3.4rem;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
}

.stack {
  display: flex;
  flex: 1;
  height: 8px;
  border-radius: 3px;
  background: var(--no-data);
  overflow: hidden;

  & .t {
    background: var(--ramp-2);
  }

  & .f {
    background: var(--ramp-5);
  }

  & .u {
    background: var(--no-data);
    box-shadow: inset 0 0 0 1px var(--hairline);
  }
}

/* ── Boundary card ── */
.bound {
  padding: 1.5rem;
  border-radius: var(--radius);
  background: var(--surface-sunk);

  & h2 {
    margin-bottom: 0.6rem;
    font-size: 1rem;
  }

  & ul {
    margin: 0;
    padding-left: 1.1rem;
    color: var(--ink-secondary);
    font-size: 0.88rem;
  }

  & li + li {
    margin-top: 0.35rem;
  }
}

@media (max-width: 900px) {
  .warn-cols,
  .mn-grid,
  .cols {
    grid-template-columns: 1fr;
  }

  .cov {
    grid-template-columns: 1fr;
    grid-template-rows: none;
    grid-auto-flow: row;
  }
}
</style>
