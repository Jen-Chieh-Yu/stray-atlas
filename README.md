# StrayAtlas 浪浪地圖

臺灣公立動物收容所開放資料的分析與互動視覺化。

**Demo**：<https://jen-chieh-yu.github.io/stray-atlas/>

---

## 這個專案在做什麼

農業部「動物認領養」開放資料每日更新，內容是**此刻仍開放認養**的動物名冊。本專案每日自動保存快照、清理欄位、將自由文字的尋獲地補全為可定位的地址，並以互動地圖與分析頁呈現收容所的滯留狀況。

這份資料有幾個反直覺的陷阱，處理不當會得到看似漂亮但站不住腳的結論。**如何避開這些陷阱，是本專案想展示的重點**，勝過任何單一結論。詳見〈資料限制〉與〈我踩過的統計陷阱〉。

---

## 技術棧

| 層 | 選用 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite |
| 部署 | GitHub Pages（Project site，掛在 `/stray-atlas/` 子路徑） |
| 資料抓取 | GitHub Actions cron（每日） |
| 前處理與分析 | Python |
| 產出格式 | JSON / GeoJSON（不產 PNG，例外見 `CLAUDE.md` §4.2） |

---

## 快速開始

抓一份當日快照（Python 3.9+，無外部相依套件）：

```bash
python scripts/fetch_snapshot.py
```

由快照重建前端要吃的 JSON（同樣無外部相依，`build_districts.py` 例外，需要 `pyshp`）：

```bash
python scripts/build_all.py                    # 用最新快照依序重建全部 JSON，並檢查日期一致
python scripts/build_all.py --date 2026-09-03  # 指定快照
```

`build_all.py` 依下列順序執行，每一步都帶同一個 `--date`；單獨執行某一步時也請帶 `--date`，否則會取當下最新的快照，造成各頁日期不一致：

```bash
python scripts/clean.py                 # 清理欄位、產生 areas.json / meta.json
python scripts/geocode.py               # stats/foundplace.json（尋獲地分級）
python scripts/build_stats.py           # stats/counties.json
python scripts/build_shelters.py        # shelters.json + animals.json
python scripts/build_shelter_points.py  # shelter-points.json（地圖圖釘，讀 shelters.json）
python scripts/build_distribution.py    # stats/distribution.json（分析頁）
```

各腳本共用的路徑、log 與 JSON 寫檔集中在 `scripts/common.py`。

**本機更新到最新資料。** 排程每天會把新快照與重建後的 `public/data/` 推上 `main`，本機只要拉下來：

```bash
git switch main
git pull --ff-only
```

在功能分支上工作時，再把 main 併進來（`git switch <分支>`、`git merge main`）。只有要用非最新的快照、或排程重建失敗時，才需要自己跑 `python scripts/build_all.py`，並把 `public/data` 一起 commit（訊息 `data: rebuild public/data from the <快照日期> snapshot`，日期看 `build_all.py` 最後一行）。

跑前端（Node 22+）：

```bash
npm ci
npm run dev       # http://localhost:5173/stray-atlas/
npm run build     # 型別檢查 + 打包，產出 dist/
npm run preview
```

---

## 專案結構

```
stray-atlas/
├── .github/workflows/
│   ├── daily-snapshot.yml   每日抓取、驗證、封存快照；有新快照時重建網站資料並觸發部署
│   └── deploy-pages.yml     打包並發布到 GitHub Pages
├── data/
│   ├── raw/                 每日快照 YYYY-MM-DD.csv.gz 與 _manifest.csv（進 git，見 CLAUDE.md §6.3）
│   └── reference/           行政區界原始檔與對照表
├── scripts/                 Python 前處理與分析（標準函式庫，例外見下）
│   ├── fetch_snapshot.py    每日抓取；驗證、確定性 gzip、manifest
│   ├── clean.py             欄位清理，同時是其他腳本的載入函式庫
│   ├── geocode.py           尋獲地分級（不呼叫 geocoder，見〈尋獲地〉）
│   ├── build_districts.py   由 shapefile 產生行政區／縣市界（需 pyshp，一次性）
│   ├── build_stats.py       縣市層級統計
│   ├── build_shelters.py    收容所與全部動物名冊
│   ├── build_shelter_points.py  收容所定位（行政區形心）
│   └── build_distribution.py    在所天數分布：直方圖、KDE、ECDF
├── public/data/             產出的 JSON / GeoJSON（前端資料契約，見 CLAUDE.md §4.1）
└── src/                     Vue 前端（views / components / composables）
```

### 頁面

| 路徑 | 內容 |
|---|---|
| `/` | 首頁：全站數字、已在所最久的動物、各頁入口與這份資料的邊界 |
| `/animals` | 全部 8,000 餘筆動物，縣市／收容所／類型／品種／在所時間篩選，每頁 16 筆 |
| `/shelters` | 收容所列表：縣市篩選、七種排序、卡片／條列切換 |
| `/shelters/:id` | 收容所介紹：基本資料與地圖、收容動物現況與在所時間分布、該所動物 |
| `/map` | 縣市 choropleth（固定門檻分級）、37 處收容所圖釘、縮放平移，左側面板顯示全國、縣市或單一收容所 |
| `/analysis` | 在所天數分布：長條圖＋KDE（對數／線性、三段平滑）、犬貓 ECDF、分位數表、各縣市排行 |
| `/about` | 關於本站：資料來源、處理方式與限制、相關官方網站 |

頁面上的資料日期只在頁尾顯示一處，讀自 `public/data/meta.json`。

---

## 資料來源

| 項目 | 內容 |
|---|---|
| 名稱 | 動物認領養（農業部） |
| 來源 | [政府資料開放平臺 dataset/85903](https://data.gov.tw/dataset/85903) |
| 介接網址 | `https://data.moa.gov.tw/Service/OpenData/TransService.aspx?UnitId=QcbUEzN6E6DL`（`fetch_snapshot.py` 加上 `&FOTT=CSV&IsTransData=1` 取 CSV） |
| 授權 | 政府資料開放授權條款－第 1 版 |
| 更新頻率 | 每 1 天 |
| 快照規模 | 28 欄，列數逐日變動（2026-09-07 為 8,275 列） |

### 每日快照機制

`.github/workflows/daily-snapshot.yml` 每日臺灣時間 08:00 執行 `scripts/fetch_snapshot.py`：下載當日 CSV、驗證必要欄位與筆數下限、以固定 mtime 壓成 `data/raw/YYYY-MM-DD.csv.gz`，再 commit 回 repo。下載失敗重試 4 次（5／15／45 秒退避），當日檔案已存在則直接跳過、不打來源網站。

`data/raw/` 保存的是**來源的原始位元組**（含 UTF-8 BOM 與 CRLF），刻意不做正規化——這個目錄的用途是可稽核的存檔，若在寫入時改寫編碼，日後就無法分辨變動來自來源還是本專案。讀取時請用 `encoding='utf-8-sig'`。

`data/raw/_manifest.csv` 逐日記錄 `date,status,rows,bytes,sha256,fetched_at_utc`。當日內容與前一份快照完全相同時不重複存檔，只在 manifest 記一列 `unchanged`；抓取失敗記 `failed`。**因此 `data/raw/` 出現缺日不等於當天沒有資料**，manifest 才是判斷依據——階段 3 以「消失的 `animal_id`」建構離所標籤時必須以它為準，否則會把「來源沒變」誤讀成「全部動物同時離所」。

當天存成新快照時，同一個 workflow 接著以 `scripts/build_all.py --date <當日>` 重建 `public/data/`，與快照一起 commit，再以 `workflow_dispatch` 觸發部署（`GITHUB_TOKEN` 的推送不會觸發其他 workflow，所以必須明確呼叫）。來源與前一天相同（`unchanged`）或抓取失敗時不重建、不部署。重建失敗時快照照樣 commit，`public/data/` 維持前一份，該次 run 標為失敗——存檔永遠優先於網站。

手動補抓：

```bash
python scripts/fetch_snapshot.py            # 抓當日快照
python scripts/fetch_snapshot.py --force    # 覆蓋當日已存在的檔案
```

來源網址若變更，設定 repo variable `SNAPSHOT_URL` 即可覆寫，不需改程式。

每次執行都會在該次 run 的 Summary 寫下筆數、欄位數、位元組、sha256，以及最近幾份快照的並排比較。**這張並排表才是稽核的重點**：這類來源最陰險的故障不是抓不到，而是每天回傳一份格式正確但內容凍結的檔案——run 全綠、檔案照存，只有把連續幾天的筆數與 sha 放在一起看才會發現。

### 儲存成本（觀察用）

每日執行會讓 repo 持續變大，以下數字供日後觀察，也作為評估是否改接官方 JSON API 的基準。2026-09-17 實測：

| 項目 | 每次大小 | 進 git 後的實際增量 | 一年約 |
|---|---|---|---|
| 原始快照 `data/raw/YYYY-MM-DD.csv.gz` | 約 0.43 MB（解壓約 2.9 MB，8,300 餘列） | 約 0.43 MB／天——gzip 過的檔案彼此無法做差異壓縮，每天都是完整一份 | 約 160 MB |
| 重建 `public/data/`（有新快照的日子） | 目錄共約 4.9 MB，其中 `animals.json` 約 2.7 MB；兩份行政區 GeoJSON 約 2.0 MB 不會變動 | 約 0.06 MB／天（以 09-15 → 09-16 兩次重建實測，打包後的差異壓縮增量） | 約 22 MB |
| 部署產物（Pages artifact） | 約 5.2 MB（程式約 0.3 MB＋`public/data`） | 不進 repo | — |

- repo 目前（15 份快照）的 `.git` 物件約 10 MB。GitHub 建議 repo 維持在 1 GB 以下，照上表速度數年內不會碰到；真的變大時再考慮把原始存檔移到 Releases 或獨立的資料 repo，**不刪歷史快照**（階段 3 的離所標籤只能從這裡來）。
- 成本的大頭是原始快照，不是網站資料。改接 JSON API 時要比較的是：JSON 回應的大小與壓縮率、能否與既有 CSV 快照接續（`clean.py` 須兩種都能讀），以及欄位是否一致。
- 重新量測：`data/raw/_manifest.csv` 的 `bytes` 欄是來源 CSV 未壓縮的位元組數；壓縮檔大小看 `data/raw/` 目錄；repo 物件大小用 `git count-objects -vH`。

### 部署

`.github/workflows/deploy-pages.yml` 在推上 `main` 時打包並發布到 GitHub Pages。網站由 artifact 提供，不經 `gh-pages` 分支，所以編譯產物完全不進版本歷史。

只動 `data/` 的推送不會觸發部署：`data/raw/` 是分析腳本的輸入、不是網站資產。網站真正吃的 `public/data/*.json` 不在忽略範圍，手動重建後推上 `main` 就會部署。每日排程的重建則由 `daily-snapshot.yml` 以 `workflow_dispatch` 觸發部署（見上）。

---

## 資料限制

**這六條是本專案所有結論的前提。** 任何與之衝突的推論都應先懷疑程式，而非改寫結論。

1. **本資料是存量快照，不是歷史紀錄。** `animal_status` 全為 `OPEN`、`animal_closeddate` 全為 `2999-12-31`。已離所的個體不在資料中，因此**沒有認養結果標籤**。
2. **不可用單一快照討論入所季節性。** `animal_createtime` 的月份分布反映的是 survivorship，不是入所流量。
3. **不可宣稱「黑狗比較難被認養」。** 只能宣稱「目前仍在所的黑狗待得比較久」——存量快照存在 length-biased sampling。
4. **`animal_foundplace` 是自由文字，僅 2.4% 含完整縣市名。** 未經縣市補全就送 geocoder 必然定位錯誤（「西安街」全臺有數十條）。更糟的是這 2.4%（201 筆）裡有 167 筆出自南投縣一家收容所——那不是資料的普遍性質，是一間機構的登錄習慣。
5. **geocode 結果必須分級標註信心水準。** 尋獲地不必然與收容所同縣市（存在跨區送交），補全結果不可當作精確座標呈現。
6. **`民眾不擬續養`、`所內` 等非地點值必須單獨歸類**，不可硬塞座標。

---

## 我踩過的統計陷阱

### 陷阱一：把月份分布當成入所季節性

**我原本這樣算**：對 `animal_createtime` 取月份直方圖，看到 8 月是建檔高峰，準備寫「暑假棄養潮」。

**發現問題**：把 2025 年單獨拉出來看，月份分布是 1 月 51 筆單調遞增到 12 月 298 筆。世界上沒有這種形狀的季節性。

**真正的原因**：這是 survivorship。**越晚進所的動物越可能尚未離所，因此越可能留在這份快照裡。** 我量到的是存量的年齡結構，不是入所流量。

**因此改用**：完全放棄以單一快照討論季節性，改為每日保存快照。累積 2–3 個月後，「今天有、明天沒有」的 `animal_id` 就是離所事件，屆時才有真正的流量與存活資料。

### 陷阱二：把「在所天數長」讀成「比較難被認養」

存量快照對長期滯留者過度取樣：一隻待了三年的狗會出現在一千多份快照裡，一隻三天就被認養的狗只會出現在三份。這是 length-biased sampling。

**因此**：本專案所有毛色、品種、體型的結論一律寫成「**目前仍在所的** X 待得比較久」。要證明「X 比較難被認養」需要離所事件資料，屬於階段 3。

<!-- TODO: 階段 2 完成後補上「黑狗症候群」的收容所內控制方法說明 -->

### 陷阱三：把核密度估計的形狀當成資料的性質

在所天數在對數軸下看起來是雙峰的：一個峰在一年以內，另一個在數年之後。這個形狀有多少來自資料、多少來自頻寬，是必須先回答的問題。

**因此** `/analysis` 提供三段頻寬（Silverman 值的 0.6／1.0／1.7 倍）讓讀者自己推。結果是：狗的雙峰撐得過標準頻寬，但在最寬的設定下併成單峰；貓在最寬的設定下收斂成單峰。**撐不過平滑的結構不當成發現。** 頁面上所有被引用的數字都改讀 ECDF，因為它沒有頻寬也沒有平滑假設。

同一張圖也提醒了尺度的選擇：線性軸下密度是單調遞減的長尾，根本沒有第二個峰。雙峰是「數量級」上的性質，不是「天數」上的性質，所以兩種軸都提供，不挑好看的那個。

---

## 尋獲地：為什麼沒有熱區圖

`animal_foundplace` 為自由文字欄位，4,671 個唯一值。實際可用程度：

| 特徵 | 比例 |
|---|---|
| 空值 | 12.5% |
| 含完整縣市名（佔全部筆數） | **2.4%** |
| 通過官方 368 鄉鎮市區清單驗證的區級資訊 | **36.2%** |
| 含路／街／巷／弄／號 | 70.9% |

`scripts/geocode.py` **不呼叫任何 geocoder**，只做分級：整值比對非地點值、台／臺折算、以官方清單驗證區名，輸出四級信心。

| 信心 | 判準 | 實際比例 |
|---|---|---|
| `high` | 原文自帶縣市＋門牌 | **0.1%**（10 筆） |
| `medium` | 通過官方清單驗證的區＋路名 | 21.5%（1,773 筆） |
| `low` | 僅路名或地標，縣市靠收容所推斷 | 64.4%（5,322 筆） |
| `none` | 空值或非地點值（`所內出生`、`不擬續養`） | 14.0%（1,160 筆） |

縣市來源的分布同樣說明了問題：只有 **197 筆**的縣市讀得自原文，其餘 6,908 筆靠收容所推斷。而那 197 筆裡有 **12 筆與收容它的收容所不同縣市**，甚至有人直接在前面寫「外縣市」——跨區送交是真的存在，所以用收容所縣市回推尋獲地本身就是錯的。

而且 36.2% 的區級覆蓋率在縣市之間差距極大——雲林縣 95.1%、臺北市 1.3%、彰化縣 1.1%。這代表區級 choropleth 畫出來的是**「哪些收容所有填區名」的地圖**，不是流浪動物的分布。

**因此本專案不畫尋獲地熱區圖**，地圖第一層改為縣市 choropleth，以收容所所在縣市為準（100% 覆蓋、零推論），並在頁面上寫明「這是動物現在在哪裡，不是牠在哪裡被撿到」。

### 收容所的位置怎麼來的

37 處收容所的圖釘同樣沒有經過 geocoder。`shelter_address` 一定寫得出鄉鎮市區，而本專案已經有那個行政區的多邊形，所以取**該行政區的形心**作為位置——比門牌粗，但那是資料本身支持的精度，頁面上也明說圖釘標的是行政區而非門牌。新竹市與嘉義市的地址省略「區」，兩筆以明列的對照表人工判定，程式不猜。

---

---

## 架構決策理由

| 決策 | 選擇 | 理由 |
|---|---|---|
| 資料抓取 | GitHub Actions cron，而非本地手動 | 這份資料每日更新且不保留歷史，**漏抓的那天永久補不回來**。人工執行遲早會斷。此外 repo 的 commit history 本身即為「專案持續運作」的證明 |
| 產出格式 | JSON / GeoJSON，而非 PNG | 靜態圖片在 demo 現場無法互動。同樣的前處理成本下，結構化資料可支援縣市篩選、犬貓切換、滯留天數區間篩選 |
| 開發順序 | 前端先於分析 | 先做前端會迫使我定義「前端要吃什麼格式的 JSON」，這份資料契約會反過來約束清理與分析腳本；反向操作容易產出大量前端用不到的中間產物 |
| 前端模型推論 | 不採用 ONNX Runtime Web | 以本資料量而言屬過度工程，預先算好結果存 JSON 查表即可 |
| 收容所定位 | 行政區形心，不呼叫 geocoder | 門牌級座標會讓精度看起來高於來源能支持的程度。行政區形心是資料自己說得出的答案 |
| KDE 與 ECDF | 在 Python 算好存 JSON | 分析留在腳本裡、瀏覽器只負責畫，與其他頁面同一套分工。高斯 KDE 手寫十五行，不為此引入 scipy |
| 頻寬選擇 | 公開三段讓讀者切換 | KDE 的形狀有一半是頻寬的主張。用交叉驗證自動選一條反而把選擇藏起來，與這頁想說的事相反 |
| 地圖繪製 | 內嵌 SVG + d3-geo，自行實作縮放 | 不依賴圖磚服務、不需 API key，demo 現場沒有外部相依可壞。縮放只是一個 transform 加 wheel／pointer 事件，不值得為此引入 d3-zoom |
| 收容所介紹頁地圖 | Google Maps Embed，金鑰缺席時退回外部連結 | 單一地址的街道圖是讀者要的東西，自己畫不划算。金鑰由建置環境注入（本機 `.env.local` 的 `VITE_GOOGLE_MAPS_EMBED_KEY`、CI 的 secret `GOOGLE_MAPS_EMBED_KEY`），必須限制 HTTP referrer；沒有金鑰時頁面仍可用，不影響主地圖 |

---

## 授權

**本專案目前保留所有權利，尚未選定開放授權條款。**

資料源授權與程式碼授權無關，另行標示：

> `data/` 目錄下之資料來源為農業部「動物認領養」開放資料，依政府資料開放授權條款第 1 版使用。
