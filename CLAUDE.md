# CLAUDE.md — StrayAtlas 工作指示

> 給接手此專案的 AI 協作者。請先完整閱讀 `PROJECT_BRIEF.md`，本文件不重複其中的資料剖析結論。

---

## 0. 專案性質與成功標準

**StrayAtlas 浪浪地圖** — 臺灣公立動物收容所開放資料分析與視覺化。

這是**求職作品集專案**。GitHub repo 連結會放在履歷上，並在面試現場以筆電 demo。

判斷任何取捨時，請以此為準：

- **可 demo > 完整**。面試現場能點擊操作的東西，勝過功能齊全但只能看截圖的東西。
- **展現判斷力 > 展現結論**。在 README 與網頁上主動說明資料限制、已識別的統計陷阱、以及為何選擇某方法而非另一種，比端出漂亮結論更有價值。
- **可獨立成立**。依賴長期資料累積的模組不能是專案主體。

**不要**把這個專案做成需要長篇說明才看得懂的東西。面試官只會看三分鐘。

---

## 1. 絕對不可違反的事實約束

以下每一條都已由實際資料驗證，違反會導致專案結論錯誤：

1. **本資料是存量快照，不是歷史紀錄。** `animal_status` 全為 `OPEN`、`animal_closeddate` 全為 `2999-12-31`。已離所個體不在資料中，因此沒有認養結果標籤。
2. **不可用單一快照討論入所季節性。** `animal_createtime` 的月份分布反映的是 survivorship，不是流量。
3. **不可宣稱「黑狗比較難被認養」。** 只能宣稱「目前仍在所的黑狗待得比較久」。存量快照存在 length-biased sampling。
4. **`animal_foundplace` 是自由文字，僅 5.1% 含縣市名。** 未經縣市補全就送 geocoder 一律視為錯誤實作。
5. **geocode 結果必須分級標註信心水準。** 尋獲地不必然與收容所同縣市。不可將補全結果當作精確座標呈現。
6. **`民眾不擬續養`、`所內` 等非地點值必須單獨歸類**，不可硬塞座標。

若後續發現任何與上述衝突的結果，先懷疑自己的程式，不要先改結論。

---

## 2. 命名慣例

**本機資料夾與遠端 repo 名稱刻意不同，這不是筆誤，不要「順手修正」。**

| 用途 | 寫法 |
|---|---|
| 本機資料夾 | `StrayAtlas` |
| GitHub repo / 網址路徑 | `stray-atlas` |
| `package.json` 的 `name` | `stray-atlas`（npm 規範不接受大寫） |
| `vite.config.ts` 的 `base` | `'/stray-atlas/'` |
| Vue Router `createWebHistory` | `'/stray-atlas/'` |
| README 大標、網頁 `<title>`、履歷 | `StrayAtlas` 或「StrayAtlas 浪浪地圖」 |

駝峰式 `StrayAtlas` 僅用於**顯示用途**，所有路徑與設定值一律小寫連字號。

### 2.1 路徑不可寫死專案根目錄名稱

CI 環境（`actions/checkout`）的工作目錄是 `stray-atlas`，不是 `StrayAtlas`。任何寫死根目錄名稱的路徑在本機會正常、在 GitHub Actions 會失敗。

```python
# 錯誤
df = pd.read_csv('C:/Users/color/source/repos/StrayAtlas/data/raw/2026-09-01.csv.gz')

# 正確
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / 'data' / 'raw' / '2026-09-01.csv.gz')
```

### 2.2 GitHub Pages 子路徑陷阱

Project site 掛在 `/stray-atlas/` 子路徑下。以下三處只要漏一個，本機 `npm run dev` 都正常，一部署就整頁空白且 Console 一排 404：

- `vite.config.ts` 的 `base`
- Vue Router 的 `createWebHistory`
- 資料檔 fetch 路徑 —— 必須用 `` fetch(`${import.meta.env.BASE_URL}data/districts.geojson`) ``，不可寫絕對路徑

---

## 3. 執行優先序

嚴格依此順序。**不要在前一階段完成前跳到下一階段。**

### 階段 0（最優先，1–2 個工作階段內完成）

> 理由：此階段累積的是「時間」而非「工時」。晚一天啟動就永久少一天的標籤資料。

- [ ] GitHub Actions cron workflow：每日下載 CSV，存為 `data/raw/YYYY-MM-DD.csv.gz` 並 commit 回 repo
  - 需處理：下載失敗重試、當日檔案已存在時跳過、UTF-8 BOM
- [ ] 資料清理腳本 `scripts/clean.py`
  - 移除零資訊量欄位（見 `PROJECT_BRIEF.md` §4.1）
  - `animal_Variety` strip trailing spaces
  - `animal_opendate` 的 `1900-01-01` 哨兵值轉為 null
  - `animal_area_pkid` → 縣市對照表（由 `shelter_address` 建立，共 22 縣市）
- [ ] `animal_foundplace` 前處理腳本 `scripts/geocode.py`
  - 非地點值分類（建立關鍵詞黑名單）
  - 縣市補全（以收容所縣市為前綴）
  - 信心分級：`high`（原文含縣市＋完整門牌）/ `medium`（含區＋路名）/ `low`（僅路名，靠收容所推斷）/ `none`
  - geocode 結果快取到本機，**不可每次重跑都打外部 API**

### 階段 1（主力）

- [ ] Vue.js 網頁最小可 demo 版
  - **先做縣市 choropleth**（以收容所縣市為準，100% 覆蓋、零推論）
  - 鄉鎮區 choropleth 降為可選圖層，且必須在 UI 上顯示各縣市的區級覆蓋率
  - 點位泡泡層後補，且必須在 UI 上顯示覆蓋率與信心分級
  - 互動需求：縣市篩選、犬／貓切換、滯留天數區間篩選
- [ ] GitHub Pages 部署 workflow

> **2026-09-03 修正。** 原訂「先做鄉鎮區 choropleth（資料可靠）」，前提不成立。
> 經 `scripts/geocode.py` 以官方 368 鄉鎮市區清單驗證，全國僅 **36.2%** 的資料
> 有可信的區級資訊，且各縣市從 1.1% 到 95.1% 不等（見 `PROJECT_BRIEF.md` §4.3）。
> 逕行繪製會得到一張「哪些收容所有填區名」的地圖：臺北市 978 隻只有 13 隻有區級
> 資料，圖上會是一片空白，而原因是登錄實務不是現實。縣市層級以收容所縣市為準，
> 不需任何推論，且 `PROJECT_BRIEF.md` §5.5 的縣市滯留差異本身就有 16 倍的強訊號。

### 階段 2（主力）

- [ ] 分析模組。依訊號強度排序執行，見 `PROJECT_BRIEF.md` §9.1
  - 先做 1（品種犬 vs 混種犬）、4（收容所量能四象限）、3（存量殘存曲線）
  - 2（黑狗症候群）需保留收容所內控制的比較，不可只做全國彙總
  - 5（資料品質評分卡）可獨立成頁，優先度高於 6、7、8

### 階段 3（加分項，非主體）

- [ ] 累積快照達 2 個月後：建構 label（消失的 `animal_id` 即為離所）
- [ ] Kaplan-Meier 存活曲線、Cox 比例風險模型
- [ ] **注意：這是右設限資料，不是二元分類問題。** 不要做「會不會被認養」的分類器

---

## 4. 輸出格式規範

### 4.1 資料契約優先

**先定義前端要吃的 JSON schema，再寫分析腳本。** 反向操作會產出大量前端用不到的中間產物。

所有分析產出一律輸出結構化資料到 `public/data/`：

```
public/data/
  meta.json              # 快照日期、資料筆數、各欄位覆蓋率
  districts.geojson      # 鄉鎮區 choropleth（含每萬人尋獲數）
  points.geojson         # 高信心點位，properties 需含 confidence 欄位
  shelters.json          # 收容所量能：在所數、滯留中位數、座標
  stats/*.json           # 各分析模組結果
```

**`public/data/` 進 git（2026-09-01 決定）。** 理由：

- repo 自帶可跑的網站 —— clone 後 `npm ci && npm run dev` 即可看到成品，不需先安裝 Python 與資料管線相依套件。要求對方 setup 管線才能看作品，成功率極低
- 部署與資料管線解耦 —— 前端改版不必重跑 Python；管線壞掉（geocoder API 掛掉、套件衝突、來源改格式）時網站仍以前一份資料正常部署，只是資料舊一點，不會整站掛掉
- diff 雜訊已由 `.gitattributes` 的 `linguist-generated=true` 處理，GitHub 上預設摺疊且不計入語言統計

**配套：不要每天重算重 commit。** 快照（`data/raw/`）每日抓取，但 `public/data/` 以每週排程或手動觸發重算即可。存量結構逐日變化極小，每日 commit 只會製造雜訊。

判斷分界：`data/raw/` **不可重現**（漏抓即永久遺失），`public/data/` **可由 `data/raw/` 完整重建**。兩者都進 git，但理由不同——前者是地基，後者是為了部署可靠性。

### 4.2 PNG / GIF 的使用時機

**僅限**不適合前端重算者：訓練曲線、SHAP summary plot、KM 曲線。

其餘一律輸出 JSON 讓前端渲染。靜態圖片在面試 demo 時無法互動，會直接削弱作品說服力。

### 4.3 前端模型推論

暫不採用 ONNX Runtime Web。以本資料量而言屬過度工程。預先算好結果存 JSON 查表即可。

---

## 5. 語言慣例

| 對象 | 語言 |
|---|---|
| 文件、README、網頁 UI 文案 | 繁體中文（臺灣用語） |
| 程式碼、變數命名、註解 | 英文 |
| commit message（標題與內文） | 英文 |

commit message 一律全英文，標題與內文皆然。理由：`git log` 全篇語言一致，且 GitHub 上的 diff、blame、PR 介面對英文 commit 的呈現最無摩擦；面試官掃 commit history 時不會遇到語言切換。

**一經確立不再更動。** 同一 repo 內語言混用造成的印象傷害，大於選錯語言本身。

縣市名稱用字跟隨原始資料，統一用「臺」（臺北市、臺南市、臺灣），不與「台」混用。

---

## 6. Git 慣例

### 6.1 AI 參與標記

代為建立 commit 時，一律使用：

```
Assisted-by: Claude <noreply@anthropic.com>
```

- **不使用** `Co-Authored-By`（AI 非共同作者，人類提交者為唯一作者並負全責）
- **不附** Claude-Session 連結

此標記僅用於「由 AI 直接建立的 commit」。人類自行操作的 commit 不加。

### 6.2 Commit prefix

| prefix | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修 bug |
| `docs` | 文件 |
| `chore` | 建置、設定、依賴更新 |
| `refactor` | 重構，行為不變 |
| `data` | 每日快照自動 commit |

每日快照的 message 固定為 `data: snapshot YYYY-MM-DD`，方便日後以 `git log --grep="^data:"` 與開發 commit 分離。

### 6.3 `.gitignore`

排除 `node_modules/`、`dist/`、`.venv/`、`__pycache__/`、`*.pyc`、`.env`。

**絕對不可排除 `data/`。** 每日快照 workflow 需要 commit 資料檔進 repo；若被 gitignore 擋掉，workflow 會安靜地什麼都沒存，且要數日後才會發現。

---

### 6.4 Commit message 格式

- **標題**：`<prefix>: <英文祈使句摘要>`，72 字元以內，句尾不加句號
- **內文一律條列**，不寫段落散文。每則條列一件事——改了什麼，或為何這樣改
- 條列以 `- ` 開頭，句尾加句號；行寬 72 字元以內，換行處縮排對齊
- 需要交代前提時，可在條列前加**一行**前言；超過一行請改寫成條列
- 結尾空一行後加 §6.1 的 `Assisted-by: Claude <noreply@anthropic.com>`

理由：這個 repo 的 history 會被面試官掃過。條列式在 `git log` 與 GitHub commit 頁面上三秒可讀完，散文式段落會被略過。

範例。**標題與內文之間、內文與 trailer 之間各需一行空行**，缺了會讓 git 把整段當成標題：

```
feat: add daily snapshot workflow

- Fetch the source CSV daily via GitHub Actions cron at 00:00 UTC.
- Store bytes verbatim as data/raw/YYYY-MM-DD.csv.gz with a fixed
  gzip mtime, so identical content yields identical bytes.
- Retry four times with backoff, and fail loudly rather than
  overwrite a good archive with an error page.
- Record one row per day in data/raw/_manifest.csv, so a gap is
  never ambiguous between "source unchanged" and "fetch broke".

Assisted-by: Claude <noreply@anthropic.com>
```

### 6.5 AI 不得代為 commit 或 push

AI 協作者**不得執行**任何改動 repo 狀態的 git 指令，包含但不限於 `git add`、`git commit`、`git push`、`git reset`、`git rebase`、`git checkout`。唯讀指令（`git status`、`git log`、`git diff`）不在此限。

完成一段工作後，只輸出兩樣東西，由人類自行執行：

1. 依 §6.4 格式寫好的 commit message
2. 對應的 git 指令

開發機為 Windows／PowerShell，**不支援 heredoc**（`<< 'EOF'`）。因此 AI 應將 message 寫入 `.git/` 底下的暫存檔——該目錄不受 git 追蹤，不會污染 `git status`——指令一律改用 `-F`：

```powershell
git add scripts/ .github/
git commit -F .git/msg.txt
git push origin main
```

理由：

- 提交者對進入 history 的內容負全責。§6.1 的 `Assisted-by` 僅標示 AI 參與，不轉移責任，因此最後一道確認必須由人類執行
- Cowork device shell 沒有 git 身分設定，commit 會失敗並留下 `.git/index.lock`，卡住後續所有 git 操作

---

## 7. 授權現況

**目前刻意維持 `No license`（保留所有權利），尚未選定開放授權條款。**

這是有意識的決定，不是遺漏。**不要自行新增 `LICENSE` 檔或把 `package.json` 的 license 欄位改成 MIT。**

- `package.json` 維持 `"license": "UNLICENSED"` 與 `"private": true`
- README 需明確寫出「本專案目前保留所有權利，尚未選定開放授權條款」

資料源授權則與程式碼授權無關，**無論如何都必須標示**：

> `data/` 目錄下之資料來源為農業部「動物認領養」開放資料，依政府資料開放授權條款第 1 版使用。

若日後決定開放授權，會由人類決定並獨立成一個 commit。

---

## 8. 開發環境（Windows）

主要開發機為 Windows，CI 為 Linux。跨平台差異需注意：

- `core.autocrlf` 設為 `true`，避免 CRLF/LF 差異造成雜訊 diff
- Windows 檔案系統不區分大小寫，`core.ignorecase` 預設為 `true`。**只改大小寫的檔名變更 git 不會偵測到**，必須用 `git mv` 而非檔案總管操作
- 所有腳本路徑用 `pathlib.Path`，不用字串拼接，避免 `\` 與 `/` 問題

---

## 9. 外部資料源

若需整合以下資料，請先確認授權與取得方式，並回報：

- 農業部「全國公立動物收容所收容處理情形統計表」（用於存量殘存曲線）
- 內政部鄉鎮區人口／家戶數（用於每萬人尋獲數）
- 各收容所公告最大留容量（用於佔床率，可能需人工蒐集）

**爬蟲禮儀**：若執行影像模組，下載 `album_file` 圖片時必須限速並建立本機快取，不可重複打政府網站。同時確認圖片授權範圍。

---

## 10. README 必須包含的內容

這是專案的門面，面試官第一眼看的就是它。除了常規說明外，**必須**包含：

1. **資料限制章節** — 明確寫出 §1 的六條約束
2. **「我踩過的統計陷阱」章節** — 至少包含月份分布的 survivorship bias 案例（見 `PROJECT_BRIEF.md` §6.2）。敘事格式：「我原本這樣算 → 發現是 X 偏誤 → 因此改用 Y 方法」
3. **geocode 覆蓋率與信心分級的說明** — 誠實標示有多少比例的尋獲地無法可靠定位
4. **架構決策理由** — 為何選 GitHub Actions 而非本地手動、為何輸出 JSON 而非 PNG
5. **授權說明** — 見 §7，程式碼與資料分開標示

主動揭露限制不是弱點，是這個專案最有說服力的部分。

---

## 11. 工作方式

一次專注一個階段的任務。完成後回報做了什麼、遇到什麼問題，不要一口氣做完三個階段再一起回報。

### 需要先問，不要自行決定

- 新增外部資料源
- 偏離 §3 的階段優先序
- 大量下載政府網站資源（爬圖片等）
- 視覺設計方向（配色、版面風格）
- 變更授權、命名慣例、語言慣例（§2、§5、§7 皆為已定案的決定）
- 分析結果與 §1 的約束衝突