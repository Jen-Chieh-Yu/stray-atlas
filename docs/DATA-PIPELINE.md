# 資料管線

資料從哪裡來、每天怎麼抓、怎麼存檔與稽核，以及網站怎麼部署。本機執行與重建的指令見 [DEVELOPMENT.md](DEVELOPMENT.md)。

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

---

## 每日快照機制

`.github/workflows/daily-snapshot.yml` 每日執行 `scripts/fetch_snapshot.py`：下載當日 CSV、驗證必要欄位與筆數下限、以固定 mtime 壓成 `data/raw/YYYY-MM-DD.csv.gz`，再 commit 回 repo。下載失敗重試 4 次（5／15／45 秒退避），當日檔案已存在則直接跳過、不打來源網站。

每天臺灣時間 21:00 由桌機觸發一次，抓取先直連來源，連不上才經由 Tailscale 出口節點從臺灣連線，原因與做法見下節。2026-10-21 以前排程設在 08:00，GitHub 延後排程後實際多在 11 點前後完成；改到 21:00 後，每份快照的時點從上午移到晚上，交接那天與前一份快照相隔約一天半。`fetched_at_utc` 記錄每次的實際時間。

`data/raw/` 保存的是**來源的原始位元組**（含 UTF-8 BOM 與 CRLF），刻意不做正規化——這個目錄的用途是可稽核的存檔，若在寫入時改寫編碼，日後就無法分辨變動來自來源還是本專案。讀取時請用 `encoding='utf-8-sig'`。

`data/raw/_manifest.csv` 逐日記錄 `date,status,rows,bytes,sha256,fetched_at_utc`。當日內容與前一份快照完全相同時不重複存檔，只在 manifest 記一列 `unchanged`；抓取失敗記 `failed`。**因此 `data/raw/` 出現缺日不等於當天沒有資料**，manifest 才是判斷依據——階段 3 以「消失的 `animal_id`」建構離所標籤時必須以它為準，否則會把「來源沒變」誤讀成「全部動物同時離所」。

當天存成新快照時，同一個 workflow 接著以 `scripts/build_all.py --date <當日>` 重建 `public/data/`，與快照一起 commit，再以 `workflow_dispatch` 觸發部署（`GITHUB_TOKEN` 的推送不會觸發其他 workflow，所以必須明確呼叫）。來源與前一天相同（`unchanged`）或抓取失敗時不重建、不部署。重建失敗時快照照樣 commit，`public/data/` 維持前一份，該次 run 標為失敗——存檔永遠優先於網站。

### 來源封鎖海外連線（2026-10-22 起）

2026-10-22 起，GitHub Actions 連 `data.moa.gov.tw` 一律 TCP 連線逾時，改用出口節點前的快照因此遺失（manifest 記為 `failed`）。10-27 以 check-host.net 從 40 個海外節點測試，39 個逾時；同時間同屬農業部的 `www.moa.gov.tw` 與 `data.gov.tw` 全部連得上，從臺灣的住宅網路則 4 秒內抓完。可見是開放資料這台主機只接受臺灣來源的連線，不是來源停擺。

11-02 再測，封鎖已經解除：check-host.net 的 47 個海外節點有 41 個連得上（逾時的 6 個分散各地），GitHub 的 runner（Microsoft AS8075，美國）直連約 7 秒抓完整份 CSV（8,705 行）。封鎖何時解除、會不會再出現都無從得知，所以出口節點保留為備援。

每次抓取前先直連來源首頁一次，連得上就直接抓。連不上時，讓 GitHub 的 runner 以臨時節點加入 Tailscale 網路，只在抓取那一步改走一台在臺灣、晚上開機的桌機出口，其餘步驟（push、部署）仍走 GitHub 自己的網路。tailnet 的存取規則只允許 `tag:ci` 經出口節點連外，碰不到桌機與其他裝置（規則見下）。經出口節點也先連一次來源首頁，連不上就立刻切回，不必等抓取重試十分鐘才失敗。repo 沒有設定 Tailscale 的 secret 時跳過出口節點，不讓加入 tailnet 的錯誤擋掉當天的 `failed` 紀錄。

每天的執行由三個來源觸發：

| 觸發 | 時間（臺灣） | 做什麼 |
|---|---|---|
| 桌機的 Windows 工作排程器執行 `scripts/trigger_snapshot.ps1` | 21:00 | 以 GitHub API 觸發 `workflow_dispatch`，主要的抓取；臺灣時間 21:00 前不觸發，免得工作排程器在午夜後補跑、佔掉隔天的檔名 |
| cron `17 13 * * *` | 21:17，實際常延後 | 備援：當天還沒存檔、且實際執行時仍在 21:00–23:59 才抓；直連與出口節點都連不上就安靜結束 |
| cron `17 0 * * *` | 08:17，實際常延後 | 檢查前一天：manifest 沒有紀錄就以 `fetch_snapshot.py --mark-failed` 記一列 `failed`，run 失敗、寄出通知 |

主要的抓取不交給 cron，是因為 GitHub 會把排程延後 2–4 小時：21:00 的排程常會拖過午夜，檔名變成隔天、桌機也已關機。備援只在 23:59 前動作，是同一個理由。來源是即時的，沒抓到的那天事後補不回來，所以由隔天早上的檢查補記 `failed`，讓 manifest 每天都有一列。

所需設定：

| 位置 | 名稱 | 內容 |
|---|---|---|
| repo secret | `TS_OAUTH_CLIENT_ID`、`TS_OAUTH_SECRET` | Tailscale OAuth client，權限為可寫入的 Auth Keys，標籤 `tag:ci` |
| repo variable | `TS_EXIT_NODE` | 出口節點（桌機）的 Tailscale IP（`100.x.y.z`） |
| 桌機的使用者環境變數 | `STRAY_ATLAS_DISPATCH_TOKEN` | fine-grained personal access token，只限本 repo，權限 Actions: Read and write |
| 桌機的工作排程器 | 每天 21:00 | 以自己的帳號、只在使用者登入時執行（token 存在使用者環境變數，SYSTEM 帳號讀不到）：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File <repo>\scripts\trigger_snapshot.ps1` |
| Tailscale 管理後台 | 桌機節點 | 開啟 Run exit node 並在後台核准；關閉 key expiry——節點金鑰預設 180 天到期，到期後出口節點會從 tailnet 消失，沒有任何提示 |
| Tailscale 存取規則 | `tagOwners`、`acls` | 見下方 |

token 有到期日，到期後 21:00 的觸發會失敗，只剩備援的 cron。

Tailscale 預設的存取規則是所有裝置互通，`tag:ci` 也包含在內。要把規則裡 `"src": ["*"]` 那條改成只限自己的裝置（`autogroup:member`，帶標籤的節點不算在內），再另給 `tag:ci` 一條只能連外的規則：

```jsonc
{
  "tagOwners": {
    "tag:ci": ["autogroup:admin"],
  },
  "acls": [
    // Your own devices still reach each other, as with the default policy.
    {"action": "accept", "src": ["autogroup:member"], "dst": ["*:*"]},
    // CI runners may use an exit node for the internet and reach nothing else.
    {"action": "accept", "src": ["tag:ci"], "dst": ["autogroup:internet:*"]},
  ],
}
```

現有規則若用的是 `grants` 而不是 `acls`，同樣把 `"src": ["*"]` 改成 `autogroup:member`，再加上 `tag:ci` 那一條。

為什麼排在晚上：來源是即時介接，收容所改一筆、CSV 就變一筆，任何時間抓到的都是當下狀態。比對 2026-09 到 10 月相鄰兩天的快照，平日上午 11 點時當天的修改只出現約 30%、新上架的動物約 22%，其餘發生在之後。晚上抓取更接近當天收盤的狀態。

### 手動補抓

```bash
python scripts/fetch_snapshot.py            # 抓當日快照
python scripts/fetch_snapshot.py --force    # 覆蓋當日已存在的檔案
```

補抓請在 Actions 頁面手動執行 Daily snapshot（`workflow_dispatch`），桌機要開著；當天臺灣時間午夜前都來得及，manifest 裡當天的 `failed` 會被覆蓋。`data/raw/` 由排程負責寫入並推上 `main`。本機抓的快照只供測試，不要 commit，否則會和機器人當天推上的同名檔案衝突。來源網址若變更，設定 repo variable `SNAPSHOT_URL` 即可覆寫，不需改程式。

### 稽核

每次執行都會在該次 run 的 Summary 寫下筆數、欄位數、位元組、sha256，以及最近幾份快照的並排比較。**這張並排表才是稽核的重點**：這類來源最陰險的故障不是抓不到，而是每天回傳一份格式正確但內容凍結的檔案——run 全綠、檔案照存，只有把連續幾天的筆數與 sha 放在一起看才會發現。

內容與前一天位元組完全相同的情況則由 `scripts/check_freshness.py` 自動把關：manifest 最新的連續 3 列都沒有存成新快照（`unchanged` 或 `failed`）時，該次 run 標為失敗，GitHub 會寄出通知。來源偶爾一天沒更新是正常的，所以門檻是 3 天而不是 1 天。

---

## 儲存成本（觀察用）

每日執行會讓 repo 持續變大，以下數字供日後觀察，也作為評估是否改接官方 JSON API 的基準。2026-09-17 實測：

| 項目 | 每次大小 | 進 git 後的實際增量 | 一年約 |
|---|---|---|---|
| 原始快照 `data/raw/YYYY-MM-DD.csv.gz` | 約 0.43 MB（解壓約 2.9 MB，8,300 餘列） | 約 0.43 MB／天——gzip 過的檔案彼此無法做差異壓縮，每天都是完整一份 | 約 160 MB |
| 重建 `public/data/`（有新快照的日子） | 目錄共約 4.9 MB，其中 `animals.json` 約 2.7 MB；兩份行政區 GeoJSON 約 2.0 MB 不會變動 | 約 0.06 MB／天（以 09-15 → 09-16 兩次重建實測，打包後的差異壓縮增量） | 約 22 MB |
| 部署產物（Pages artifact） | 約 5.2 MB（程式約 0.3 MB＋`public/data`） | 不進 repo | — |

- repo 目前（15 份快照）的 `.git` 物件約 10 MB。GitHub 建議 repo 維持在 1 GB 以下，照上表速度數年內不會碰到；真的變大時再考慮把原始存檔移到 Releases 或獨立的資料 repo，**不刪歷史快照**（階段 3 的離所標籤只能從這裡來）。
- 成本的大頭是原始快照，不是網站資料。改接 JSON API 時要比較的是：JSON 回應的大小與壓縮率、能否與既有 CSV 快照接續（`clean.py` 須兩種都能讀），以及欄位是否一致。
- 重新量測：`data/raw/_manifest.csv` 的 `bytes` 欄是來源 CSV 未壓縮的位元組數；壓縮檔大小看 `data/raw/` 目錄；repo 物件大小用 `git count-objects -vH`。

---

## 部署

`.github/workflows/deploy-pages.yml` 在推上 `main` 時打包並發布到 GitHub Pages。網站由 artifact 提供，不經 `gh-pages` 分支，所以編譯產物完全不進版本歷史。

只動 `data/` 的推送不會觸發部署：`data/raw/` 是分析腳本的輸入、不是網站資產。網站真正吃的 `public/data/*.json` 不在忽略範圍，手動重建後推上 `main` 就會部署。每日排程的重建則由 `daily-snapshot.yml` 以 `workflow_dispatch` 觸發部署（見上）。

---

## 收容所開放時間（人工整理）

開放資料只有收容所的地址與電話。開放時間、參觀方式（須先預約、可直接前往或官方未說明）與認養須知連結，由人工整理自各收容所與主管機關的官網，存在 `data/reference/shelter-info.json`，`build_shelters.py` 會把它併進 `shelters.json` 的 `info`。

- 每筆附來源網址與最後確認日（`checked`）。官網沒寫的不推論；認養須知只連結、不轉抄規定。
- 原始資料的電話、地址不被取代；官網的值不同時另列並附出處。
- 檔案格式錯誤（鍵、日期、連結、參觀方式的值）會讓重建失敗；名冊裡出現沒有對應資料的新收容所時只記警告，不擋重建。
- 確認日超過 180 天，網站上的開放時間會淡化並提示可能已過時。重新確認時改 `checked`，規則見 `DESIGN.md` §7〈開放時間與參觀方式〉。
