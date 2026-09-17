<script setup lang="ts">
/** About: what the site is for, where the data comes from, how fresh it is,
 *  the technical choices, and the disclaimer.
 *
 *  Every figure is read from the data files, so the page follows the snapshot
 *  it describes.
 */
import { computed, onMounted, ref } from 'vue'
import PageHead from '@/components/PageHead.vue'
import { fetchDistribution, useAtlasData } from '@/composables/useAtlasData'
import { formatCount } from '@/lib/animals'
import { HERO_PHOTOS } from '@/lib/heroPhotos'
import type { DistributionPayload } from '@/types'

const REPO_URL = 'https://github.com/Jen-Chieh-Yu/stray-atlas'
/** The ministry's pet registration site, and its adoption listing built on
 *  the same feed. */
const PET_SITE_URL = 'https://www.pet.gov.tw/'
const OFFICIAL_URL = 'https://www.pet.gov.tw/AnimalApp/AnnounceMent.aspx?PageType=Adopt'

const { stats } = useAtlasData()
const distribution = ref<DistributionPayload | null>(null)

onMounted(async () => {
  // One sentence reads this; a failed fetch drops the sentence, not the page.
  try {
    distribution.value = await fetchDistribution()
  } catch {
    distribution.value = null
  }
})

const animalCount = computed(() => stats.value?.total.count ?? null)
const shelterCount = computed(() =>
  stats.value ? stats.value.counties.reduce((sum, county) => sum + county.shelters, 0) : null,
)

function pct(share: number): string {
  return `${(share * 100).toFixed(1)}%`
}

const overFourYears = computed(() => distribution.value?.scopes.all.over_4_years ?? null)

const TECH: { topic: string; choice: string; reason: string }[] = [
  {
    topic: '來源快照',
    choice: 'GitHub Actions 每日排程',
    reason: '來源不保留歷史，沒存下的那一天補不回來；人工執行遲早會斷。存完快照接著重建網站資料並部署。',
  },
  {
    topic: '原始檔存檔',
    choice: '原始位元組原封不動存檔',
    reason: '存檔時若改寫過編碼，日後就分不出變動來自來源還是來自本站。',
  },
  {
    topic: '產出格式',
    choice: 'JSON／GeoJSON，不產圖片',
    reason: '同樣的前處理成本，結構化資料才能支援篩選與切換。',
  },
  {
    topic: '地圖',
    choice: '內嵌 SVG，不用圖磚服務',
    reason: '不需要 API key，也沒有會壞掉的外部相依。',
  },
  {
    topic: '收容所定位',
    choice: '行政區形心，不呼叫 geocoder',
    reason: '門牌級座標會讓精度看起來高於來源能支持的程度。',
  },
  {
    topic: '密度曲線與累積分布',
    choice: '在 Python 算好存成 JSON',
    reason: '分析留在腳本裡，瀏覽器只負責畫。',
  },
  {
    topic: '平滑頻寬',
    choice: '公開三段讓讀者切換',
    reason: '自動選一條等於把選擇藏起來，與這頁想說的事相反。',
  },
]
</script>

<template>
  <div class="about">
    <PageHead title="關於本站">
      StrayAtlas 浪浪地圖整理農業部「動物認領養」開放資料，把全臺{{
        shelterCount ? ` ${shelterCount} 間` : ''
      }}公立收容所目前仍開放認養的動物，做成可以查詢與比較的畫面。
    </PageHead>

    <section aria-labelledby="ab-purpose">
      <h2 id="ab-purpose">服務目的</h2>
      <p>
        農業部的寵物登記管理網站（<a :href="PET_SITE_URL" target="_blank" rel="noreferrer">pet.gov.tw</a>）上，已經有<a :href="OFFICIAL_URL" target="_blank" rel="noreferrer">動物認領養公告頁</a>提供全國收容動物的查詢，本站用的是同一份開放資料，差別在於讀法：<strong>找動物</strong>用地區、種類、性別、體型與已在所時間收斂清單；<strong>收容所</strong>看每一間現在收了多少、狗貓各佔多少；<strong>縣市地圖</strong>看全臺的分布；<strong>資料分析</strong>看在所天數的整體樣貌。
      </p>
      <p>
        這個站把「已在所多久」直接算出來，放到和照片一樣顯眼的位置，也能跨收容所比較。<template
          v-if="overFourYears !== null"
          >目前仍在所的動物裡，有 {{ pct(overFourYears) }} 已經在所超過四年。</template
        >
      </p>
      <p>
        <strong>本站不辦理認養，也不代為保留或媒合動物。</strong>實際認養請直接與該收容所聯絡，每一張動物卡片與收容所頁面上都附有地址與電話。
      </p>
    </section>

    <section aria-labelledby="ab-sources">
      <h2 id="ab-sources">資料來源</h2>
      <p>本站不修改來源內容，只做格式整理與統計。</p>
      <div class="table-scroll">
        <table class="grid-table sources">
          <thead>
            <tr>
              <th scope="col">項目</th>
              <th scope="col">來源</th>
              <th scope="col">授權</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">動物資料</th>
              <td>
                農業部「動物認領養」<a
                  href="https://data.gov.tw/dataset/85903"
                  target="_blank"
                  rel="noreferrer"
                  >政府資料開放平臺 dataset 85903</a
                >
              </td>
              <td>政府資料開放授權條款第 1 版</td>
            </tr>
            <tr>
              <th scope="row">行政區界線</th>
              <td>內政部「鄉鎮市區界線」dataset 7441</td>
              <td>政府資料開放授權條款第 1 版</td>
            </tr>
            <tr>
              <th scope="row">動物照片</th>
              <td>
                由農業部寵物登記管理網站（<a :href="PET_SITE_URL" target="_blank" rel="noreferrer"
                  >pet.gov.tw</a
                >）提供，隨原始資料一併公開
              </td>
              <td>依來源規定</td>
            </tr>
            <tr>
              <th scope="row">首頁示意照片</th>
              <td>
                <a href="https://unsplash.com" target="_blank" rel="noreferrer">Unsplash</a>，共
                {{ HERO_PHOTOS.length }} 張，攝影師列於表格下方
              </td>
              <td>
                <a href="https://unsplash.com/license" target="_blank" rel="noreferrer"
                  >Unsplash License</a
                >
              </td>
            </tr>
            <tr>
              <th scope="row">認養流程</th>
              <td>
                參考<a
                  href="https://www.tcapo.gov.taipei/cp.aspx?n=540601EBB8FD4066"
                  target="_blank"
                  rel="noreferrer"
                  >臺北市動物保護處公告之認養步驟</a
                >整理，各縣市規定不同
              </td>
              <td>—</td>
            </tr>
            <tr>
              <th scope="row">介面圖示</th>
              <td><a href="https://lucide.dev" target="_blank" rel="noreferrer">Lucide</a></td>
              <td>ISC License</td>
            </tr>
            <tr>
              <th scope="row">本站原始碼</th>
              <td>
                <a :href="REPO_URL" target="_blank" rel="noreferrer"
                  >GitHub：Jen-Chieh-Yu/stray-atlas</a
                >
              </td>
              <td>目前保留所有權利，尚未選定開放授權條款</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p>
        首頁輪播的照片僅為示意，照片中的動物不在臺灣的收容所，也不是本站資料裡的動物。攝影與出處：
      </p>
      <ul class="photo-credits">
        <li v-for="photo in HERO_PHOTOS" :key="photo.id">
          <a :href="photo.url" target="_blank" rel="noreferrer">{{ photo.alt }}</a>
          <span>Photo by {{ photo.photographer }} / Unsplash</span>
        </li>
      </ul>
    </section>

    <section aria-labelledby="ab-freshness">
      <h2 id="ab-freshness">更新頻率</h2>
      <div class="updatebox">
        <div class="ubox">
          <b
            >{{ animalCount !== null ? formatCount(animalCount) : '—' }} 隻 ·
            {{ shelterCount ?? '—' }} 間</b
          >
          <span>這份快照的動物與收容所數</span>
        </div>
        <div class="ubox">
          <b>每日</b>
          <span>每天早上排程更新；來源沒有變動時沿用前一份</span>
        </div>
      </div>
      <p>
        網站上的名單與數字<strong>以頁尾標示的快照日期為準</strong>，一天更新一次，不等於收容所現場的即時狀況——名單上的動物可能已經被認養、被原飼主領回或轉出。要看最新名單，請到<a
          :href="OFFICIAL_URL"
          target="_blank"
          rel="noreferrer"
          >動物認領養公告頁</a
        >，或直接致電收容所。
      </p>
      <p>
        每天的原始快照也會另外存檔：來源只提供「此刻」的名冊，沒存下的那一天永遠補不回來。這些存檔留給日後分析離所事件用。
      </p>
    </section>

    <section aria-labelledby="ab-tech">
      <h2 id="ab-tech">技術選擇</h2>
      <p>每一列寫的是為什麼這樣選，不是版本號。</p>
      <div class="table-scroll">
        <table class="grid-table tech">
          <thead>
            <tr>
              <th scope="col">項目</th>
              <th scope="col">選擇</th>
              <th scope="col">理由</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in TECH" :key="row.topic">
              <th scope="row">{{ row.topic }}</th>
              <td>{{ row.choice }}</td>
              <td>{{ row.reason }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="stack">
        前端是 Vue 3 + TypeScript + Vite，部署在 GitHub Pages；資料前處理是 Python 標準函式庫。
      </p>
    </section>

    <section aria-labelledby="ab-disclaimer">
      <h2 id="ab-disclaimer">免責聲明</h2>
      <div class="disclaimer">
        <ul>
          <li>
            本站為個人專案，<strong>與農業部及各地動物保護機關並無隸屬或合作關係</strong>，也不代表任何收容所發言。
          </li>
          <li>
            所有內容均取自前述公開資料。本站不修改資料內容，若與來源或收容所現場公告有出入，<strong>一律以原始資料與收容所公告為準</strong>。
          </li>
          <li>
            名單上的動物可能已被認養、被原飼主領回或轉出。<strong>前往收容所前，請務必先以電話確認該動物仍在所內。</strong>
          </li>
          <li>
            地圖上的收容所圖釘標示的是<strong>行政區位置，不是門牌地址</strong>，僅供辨識方位；實際地址請以頁面上的文字為準。
          </li>
          <li>
            本站的統計數字只描述「目前仍在所」的動物，<strong>不能用來推論認養率、認養速度或收容所績效</strong>。各頁底部另有該頁的資料限制說明。
          </li>
          <li>本站不蒐集個人資料，也不提供認養媒合、寄養或送養服務。</li>
        </ul>
      </div>
    </section>
  </div>
</template>

<style scoped>
.about > section {
  padding-top: 3rem;
}

.about > section:first-of-type {
  padding-top: 2.5rem;
}

h2 {
  margin-bottom: 0.9rem;
  font-size: 1.15rem;
}

section > p {
  max-width: 46rem;
  margin: 0;
  color: var(--ink-secondary);
  font-size: 0.92rem;
  line-height: 1.85;
  font-variant-numeric: tabular-nums;
}

section > p + p,
.table-scroll + p,
.updatebox + p {
  margin-top: 0.8rem;
}

strong {
  color: var(--ink);
}

a {
  color: var(--accent-text);
}

/* ── Tables ── */
.table-scroll {
  overflow-x: auto;
  margin-top: 0.75rem;
}

.grid-table {
  width: 100%;
  min-width: 36rem;
  border-collapse: collapse;

  & th,
  & td {
    padding: 0.75rem 0.6rem;
    border-bottom: 1px solid var(--hairline);
    font-size: 0.88rem;
    line-height: 1.7;
    text-align: left;
    vertical-align: top;
  }

  & thead th {
    color: var(--ink-muted);
    font-size: 0.78rem;
    font-weight: 400;
  }

  & tbody th {
    font-weight: 700;
    white-space: nowrap;
  }

  & td {
    color: var(--ink-secondary);
  }
}

.sources thead th:first-child,
.tech thead th:first-child {
  width: 9rem;
}

.sources thead th:last-child {
  width: 16rem;
}

.tech thead th:nth-child(2) {
  width: 15rem;
}

section > p.stack {
  color: var(--ink-muted);
  font-size: 0.86rem;
}

/* ── Photo credits ── */
.photo-credits {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem 1.5rem;
  max-width: 46rem;
  margin: 0.6rem 0 0;
  padding: 0;
  list-style: none;
  font-size: 0.86rem;

  & li {
    display: flex;
    flex-direction: column;
  }

  & span {
    color: var(--ink-muted);
    font-size: 0.78rem;
  }
}

/* ── Freshness ── */
.updatebox {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 0.5rem;
}

.ubox {
  padding: 1.1rem 1.2rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);

  & b {
    display: block;
    color: var(--accent-text);
    font-size: 1.15rem;
    line-height: 1.35;
    font-variant-numeric: tabular-nums;
  }

  & span {
    color: var(--ink-muted);
    font-size: 0.82rem;
  }
}

/* ── Disclaimer ── */
.disclaimer {
  margin-top: 0.5rem;
  padding: 1.6rem;
  border-radius: var(--radius);
  background: var(--surface-sunk);

  & ul {
    margin: 0;
    padding-left: 1.15rem;
  }

  & li {
    margin-bottom: 0.55rem;
    color: var(--ink-secondary);
    font-size: 0.88rem;
    line-height: 1.8;

    &:last-child {
      margin-bottom: 0;
    }
  }
}

@media (max-width: 700px) {
  .updatebox,
  .photo-credits {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 520px) {
  .disclaimer {
    padding: 1.1rem;
  }
}
</style>
