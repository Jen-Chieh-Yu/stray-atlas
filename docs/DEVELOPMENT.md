# 開發

本機執行、檢查與由快照重建資料的方法，以及專案結構。資料從哪裡來、每天怎麼更新，見 [DATA-PIPELINE.md](DATA-PIPELINE.md)；工作規則與 Git 慣例見 [CLAUDE.md](../CLAUDE.md)。

---

## 環境需求

| 項目 | 版本 |
|---|---|
| Node | 以 `.nvmrc` 為準。`package.json` 的 `engines` 接受 22.13 以上的 22、24 與 26 以上，`.npmrc` 讓版本不合時 `npm ci` 直接失敗 |
| Python | 3.10 以上（兩支 workflow 用 3.12）。資料管線只用標準函式庫，例外見下 |

---

## 跑前端

```bash
npm ci
npm run dev         # http://localhost:5173/stray-atlas/
npm run type-check  # 只做型別檢查（commit 前）
npm run lint        # ESLint：邏輯問題（commit 前）
npm run format      # Prettier：重排格式；只想檢查用 npm run format:check
npm test            # vitest：src/lib 的純函式（commit 前）
npm run build       # 型別檢查 + 打包，產出 dist/（推送前）
npm run test:e2e    # Playwright：以 dist/ 在 /stray-atlas/ 子路徑跑過每一頁（先 build）
npm run preview     # 預覽 dist/

cp .env.example .env.local   # 選用：填入 Google Maps Embed 金鑰，收容所介紹頁才會顯示內嵌地圖
```

第一次跑 `test:e2e` 前要先下載瀏覽器：`npx playwright install chromium`。它只檢查一件單元測試看不到的事：建置後的網站放在子路徑下，每一頁都畫得出來、沒有任何對本站的請求失敗（`CLAUDE.md` §2.2 的整頁空白陷阱）。外部網站（照片、字型）的請求一律以空回應代替，測試不依賴政府網站是否正常。新增路由時，在 `e2e/smoke.spec.ts` 的 `ROUTES` 加一行。

全檔重排的 commit 登記在 `.git-blame-ignore-revs`，GitHub 的 blame 會自動略過。本機的 `git blame` 要略過，clone 後設定一次：

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

---

## 跑建置腳本的檢查

pytest 與 ruff 只有檢查需要，腳本本身維持標準函式庫：

```bash
pip install "pytest>=9,<10" "ruff>=0.15,<0.16"
ruff check .        # 設定在 ruff.toml，只檢查不重排
python -m pytest -q
```

提交前跑的檢查與 CI 相同，完整清單見 `CLAUDE.md` §8.1。

---

## 由快照重建資料

**本機更新到最新資料。** 排程每天會把新快照與重建後的 `public/data/` 推上 `main`，本機只要拉下來：

```bash
git switch main
git pull --ff-only
```

在功能分支上工作時，再把 main 併進來（`git switch <分支>`、`git merge main`）。只有要用非最新的快照、或排程重建失敗時，才需要自己重建：在分支上 commit `public/data`（訊息 `data: rebuild public/data from the <快照日期> snapshot`，日期看 `build_all.py` 最後一行），再經 PR 併回 `main`（見 `CLAUDE.md` §6.6）。

由快照重建前端要吃的 JSON（同樣無外部相依，`build_districts.py` 例外，需要 `pyshp`）：

```bash
python scripts/build_all.py                    # 用最新快照依序重建全部 JSON，並檢查日期一致
python scripts/build_all.py --date 2026-09-03  # 指定快照
python scripts/build_all.py --list             # 只列出步驟，不執行
```

`build_all.py` 依下列順序執行九個步驟，讀快照的步驟都帶同一個 `--date`；單獨執行某一步時也請帶 `--date`，否則會取當下最新的快照，造成各頁日期不一致：

```bash
python scripts/clean.py                 # 清理欄位、產生 areas.json / meta.json
python scripts/geocode.py               # stats/foundplace.json（尋獲地分級）
python scripts/build_stats.py           # stats/counties.json
python scripts/build_shelters.py        # shelters.json + animals.json（併入 data/reference/shelter-info.json）
python scripts/build_shelter_points.py  # shelter-points.json（地圖圖釘，讀 shelters.json）
python scripts/build_home.py            # home.json（首頁計數與卡片，讀 shelters.json + animals.json）
python scripts/build_distribution.py    # stats/distribution.json（分析頁）
python scripts/build_features.py        # stats/features.json（分組中位數、收容所內毛色對照）
python scripts/build_quality.py         # stats/quality.json（資料品質頁）
```

各腳本共用的路徑、log 與 JSON 寫檔集中在 `scripts/common.py`。抓快照的方法見 [DATA-PIPELINE.md](DATA-PIPELINE.md)〈手動補抓〉；本機抓的快照只供測試，不要 commit。

---

## 更換首頁照片

照片由人工從 Unsplash 下載，先在照片頁確認標示為 Unsplash License（不是付費的 Unsplash+），原檔放進 `assets-src/hero/`，在 `scripts/build_hero.py` 與 `src/lib/heroPhotos.ts`（含攝影師、出處與對焦位置）登記後執行：

```bash
pip install pillow
python scripts/build_hero.py   # 產生 src/assets/hero/*.webp
```

`THIRD-PARTY-LICENSES` 的照片清單要一起更新。

---

## 專案結構

```
stray-atlas/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml               PR 的檢查：ESLint、Prettier、型別、vitest、build、Playwright；ruff、pytest、public/data 重建比對
│   │   ├── daily-snapshot.yml   每日抓取、驗證、封存快照；有新快照時重建網站資料並觸發部署；來源停更時讓 run 失敗
│   │   └── deploy-pages.yml     打包並發布到 GitHub Pages
│   └── dependabot.yml       每月檢查 npm 與 GitHub Actions 的新版本
├── data/
│   ├── raw/                 每日快照 YYYY-MM-DD.csv.gz 與 _manifest.csv（進 git，見 CLAUDE.md §6.3）
│   └── reference/
│       ├── districts.json   縣市 → 鄉鎮市區名稱對照（build_districts.py 產出，geocode.py 使用）
│       ├── fields.json      原始欄位的中文名稱
│       └── shelter-info.json  收容所開放時間、參觀方式與認養須知連結（人工整理，見 DATA-PIPELINE.md）
├── scripts/                 Python 前處理與分析（標準函式庫，例外見下）
│   ├── common.py            共用：路徑、log、時間戳記、JSON 寫檔、快照清單
│   ├── fetch_snapshot.py    每日抓取；驗證、確定性 gzip、manifest
│   ├── check_freshness.py   manifest 最新連續 3 列都沒有新快照時回傳失敗
│   ├── build_all.py         固定一份快照，依序跑下列九步並檢查輸出日期一致
│   ├── clean.py             欄位清理，同時是其他腳本的載入函式庫
│   ├── geocode.py           尋獲地分級（不呼叫 geocoder，見 METHODOLOGY.md〈尋獲地〉）
│   ├── build_stats.py       縣市層級統計
│   ├── build_shelters.py    收容所與全部動物名冊，併入人工整理的收容所資訊
│   ├── build_shelter_points.py  收容所定位（行政區形心）
│   ├── build_home.py        首頁的計數與卡片，讓首頁不必先載入整份名冊
│   ├── build_distribution.py    在所天數分布：直方圖、KDE、ECDF
│   ├── build_features.py    分組中位數與四分位距、收容所內毛色對照
│   ├── build_quality.py     各縣市與各收容所的登錄完整度評分
│   ├── build_hero.py        首頁示意照片縮圖成 WebP（需 pillow，一次性，不在 build_all 內）
│   ├── og-image.html        分享預覽預設圖 public/og.png 的原稿（以瀏覽器截圖產生，一次性）
│   └── build_districts.py   由內政部鄉鎮市區界 shapefile 產生對照表與界線（需 pyshp，一次性，不在 build_all 內；原始壓縮檔不進 git）
├── public/
│   ├── favicon.svg
│   ├── og.png               分享預覽的預設圖（1200×630，沒有動物照片時與其他頁面用）
│   └── data/                產出的 JSON / GeoJSON（前端資料契約，見 CLAUDE.md §4.1）
│       ├── meta.json        快照日期與清理摘要（頁尾日期讀這裡）
│       ├── animals.json     全部動物
│       ├── home.json        首頁的計數與卡片（首頁畫完後才在背景載入 animals.json）
│       ├── shelters.json    收容所與各所統計、開放時間
│       ├── shelter-points.json  地圖圖釘
│       ├── areas.json       縣市代碼對照
│       ├── counties.geojson、districts.geojson  縣市與鄉鎮市區界（build_districts.py 產出）
│       └── stats/           counties.json、foundplace.json、distribution.json、features.json、quality.json
├── assets-src/hero/         首頁照片原檔（Unsplash 下載，約 24 MB，不進 git）
├── src/                     Vue 前端
│   ├── main.ts、App.vue     進入點與共用外殼（頂欄、導覽、頁尾）
│   ├── style.css            設計 token 與全域樣式（見 DESIGN.md §3）
│   ├── types.ts             資料契約的型別
│   ├── assets/hero/         首頁示意照片（WebP，1920 與 960 寬各一份）
│   ├── router/              路由與捲動行為
│   ├── views/               九個頁面（Home、Animals、ShelterList、Shelter、Map、Quality、Analysis、About、Shortlist）
│   ├── components/          動物卡片與詳細資料、首頁照片輪播、縣市地圖、分析圖表、載入骨架、圖示
│   ├── composables/         資料載入（useAtlasData）、動物名冊（useRoster）與候選清單（useShortlist）
│   └── lib/                 共用函式：動物、在所天數、分享文字與分享頁、候選清單與它的動態、收容所地址與開放時間、詳細資料視窗路由、圖示資料、首頁照片與出處、捲動淡入
├── tests/                   建置腳本的 pytest 測試（src/lib 的 vitest 測試在 src/lib/__tests__/）
├── e2e/                     Playwright 煙霧測試（playwright.config.ts）
├── docs/                    說明文件（METHODOLOGY、ARCHITECTURE、DEVELOPMENT、DATA-PIPELINE）與 README 的截圖（images/）
├── index.html、vite.config.ts、vitest.config.ts、tsconfig*.json、env.d.ts   vite.config.ts 在 build 時寫出 404.html 與每隻動物的分享頁 /a/<id>/
├── eslint.config.js、.prettierrc、.prettierignore、.editorconfig、ruff.toml   靜態檢查與格式設定
├── .nvmrc、.npmrc           Node 版本與 engine-strict
├── .git-blame-ignore-revs   只改排版的 commit，blame 時略過
├── .env.example             Google Maps Embed 金鑰範本（複製成 .env.local）
├── CLAUDE.md                AI 協作工作規則
├── PROJECT_BRIEF.md         資料剖析結論與已驗證數字
├── DESIGN.md                介面規格與設計約束
└── THIRD-PARTY-LICENSES     複製進原始碼的第三方素材授權（Lucide 圖示、Unsplash 照片）
```

### 路由

| 路徑 | 內容 |
|---|---|
| `/` | 首頁：全站數字、已在所最久的動物、各頁入口與這份資料的邊界 |
| `/animals` | 全部 8,000 餘筆動物，搜尋（含收容編號）與縣市／收容所／類型／品種／毛色／性別／體型／年齡／絕育／在所時間篩選，每頁 16 筆 |
| `/shelters` | 收容所列表：縣市篩選、七種排序、卡片／條列切換 |
| `/shelters/:id` | 收容所介紹：開放時間、參觀方式與認養須知連結、基本資料與地圖、收容動物現況與在所時間分布、該所動物 |
| `/map` | 縣市 choropleth（固定門檻分級）、37 處收容所圖釘、縮放平移，左側面板顯示全國、縣市或單一收容所 |
| `/quality` | 資料品質（不在頂欄，入口在 `/about#ab-data` 與頁尾）：被丟掉的欄位、各欄覆蓋率、各縣市四項登錄完整度評級（不給總分）、同一件事的多種寫法 |
| `/analysis` | 在所天數分布（不在頂欄，入口同上）：長條圖＋KDE（對數／線性、三段平滑）、犬貓 ECDF、分位數表、各分組中位數與四分位距、收容所內毛色對照、各縣市排行 |
| `/about` | 關於本站：服務目的、資料來源、更新頻率、資料品質與分析的入口、技術選擇、免責聲明 |
| `/shortlist` | 候選清單：讀者在卡片或詳細資料上標記的動物，依收容所分組附電話與開放時間，可複製收容編號或列印；存在這個瀏覽器的 localStorage，不需帳號 |
| `/a/<id>/` | 分享連結：build 時為每隻動物產生的小頁面，只帶連結預覽（品種、收容所、照片），讀者打開會立刻轉到該動物的詳細資料；動物離開名單後轉到「不在目前名單」 |

頁面上的資料日期只在頁尾顯示一處，讀自 `public/data/meta.json`。
