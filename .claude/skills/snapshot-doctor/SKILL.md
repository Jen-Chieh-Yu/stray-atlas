---
name: snapshot-doctor
description: 檢查 StrayAtlas 每日快照排程是否正常：讀 origin/main 的 `data/raw/_manifest.csv`、資料 commit 與網站目前的資料日期，算出最後一次成功抓取、連續失敗或未更新幾天、有沒有缺日，判斷可能原因（桌機關機、Tailscale 出口節點離線、觸發 token 到期、secret 設錯、來源停更、重建或部署失敗），並列出人類要去哪裡確認。使用時機：使用者問「排程有沒有跑」「資料有更新嗎」「今天有抓到嗎」「網站資料是幾號的」「Daily snapshot 失敗了」「收到 Actions 失敗通知」，或貼上 Daily snapshot 的 log，即使沒提到 skill 名稱也要用。只讀不寫：不抓快照、不 commit、不觸發 workflow。
---

# 每日快照健康檢查（snapshot-doctor）

目的：快照漏抓一天就永久補不回來（CLAUDE.md §3 階段 0），而 2026-10-22 起抓取依賴三個
repo 外的元件：在臺灣的桌機、Tailscale 出口節點、桌機上的觸發 token。這個 skill 從 repo
裡看得到的紀錄推斷哪一段壞了，再告訴人類去哪裡確認。機制見 `docs/DATA-PIPELINE.md`
〈每日快照機制〉與〈來源封鎖海外連線〉。

## 每天的流程（判斷的依據）

| 時間（臺灣） | 誰 | 做什麼 |
|---|---|---|
| 21:00 | 桌機的工作排程器執行 `scripts/trigger_snapshot.ps1` | 以 GitHub API 觸發 `workflow_dispatch`，主要的抓取 |
| 21:17，常延後數小時 | cron 備援 | 當天還沒存檔、且仍在 21:00–23:59 才抓；直連與出口節點都連不上就安靜結束 |
| 08:17，常延後到中午前後 | cron 檢查 | 前一天沒有任何紀錄 → 記一列 `failed`，run 失敗並寄出通知 |

manifest 每天一列：`stored`（新快照，同時重建 `public/data/` 並部署）、`unchanged`（與前一份
相同）、`failed`。

## 步驟

1. **取得最新紀錄**（`fetch` 只更新遠端追蹤分支，不動工作目錄）
   ```powershell
   git fetch origin
   git show origin/main:data/raw/_manifest.csv | python .claude/skills/snapshot-doctor/scripts/manifest_report.py -
   ```
   腳本列出：最後一次 `stored`、連續沒有新快照的天數、缺日、最近 10 列，以及每一列
   `failed` 是誰寫的：
   - `run`：當天有 run 走到抓取那一步，抓取失敗。
   - `watchdog`：隔天早上才補記，代表當晚**沒有任何 run 走到抓取**。

2. **對照 commit 與網站資料**
   ```powershell
   git log origin/main --grep="^data:" --format="%h %ad %s" --date=format:"%m-%d %H:%M" -10
   git show origin/main:public/data/meta.json | Select-Object -First 3
   ```
   `meta.json` 的 `snapshot_date` 是網站目前顯示的資料日期，應該等於最後一次 `stored`。

3. **人類貼了 log 或 run 的摘要時**，看是哪一步失敗（步驟名稱在
   `.github/workflows/daily-snapshot.yml`），對照下方〈判斷〉。

4. **依症狀判斷**，再寫報告。

## 判斷

| 看到的 | 最可能的原因 | 請人類確認 |
|---|---|---|
| `failed`，由 `watchdog` 補記 | 21:00 沒有觸發，備援也沒在午夜前跑到 | 桌機那晚是否開機、是否在 21:00 前睡著；工作排程器「上次執行結果」是否為 `0x0`；`STRAY_ATLAS_DISPATCH_TOKEN` 是否過期（fine-grained token 有到期日） |
| `failed`，由 `run` 記錄，摘要有 `Tailscale secrets are not set` | 直連被擋，repo 又沒有 Tailscale 的 secret | repo 的 Settings → Secrets and variables → Actions 是否有 `TS_OAUTH_CLIENT_ID`／`TS_OAUTH_SECRET`（要放在 Repository secrets，不是 Environment 或 Dependabot）；再用 check-host.net 確認封鎖是否回來了 |
| `failed`，由 `run` 記錄，摘要有 `source unreachable directly and through exit node` | 直連被擋，出口節點也不在線 | 桌機的 Tailscale 是否連線、Run exit node 是否開著；管理後台的出口節點是否仍核准、節點金鑰是否過期（key expiry）；repo variable `TS_EXIT_NODE` 是否為桌機目前的 Tailscale IP |
| run 停在 **Join the tailnet** | OAuth client 有問題 | repo secret `TS_OAUTH_CLIENT_ID`／`TS_OAUTH_SECRET` 是否存在且正確；OAuth client 是否有 Auth Keys 寫入權限與 `tag:ci`；tailnet 規則的 `tagOwners` 是否宣告 `tag:ci` |
| `failed`，由 `run` 記錄，出口節點在線 | 來源本身出問題，或來源連臺灣家用網路也擋了 | 從桌機瀏覽器開來源網址（`docs/DATA-PIPELINE.md` 的介接網址）；`data.gov.tw` 資料集頁面是否有公告 |
| 連續 3 列以上 `unchanged`，run 因 freshness 失敗 | 來源停止更新 | `data.gov.tw` 資料集頁面的更新時間；不是本專案的錯，記錄即可 |
| 最近是 `stored`，但 `meta.json` 停在更早的日期 | 重建或部署失敗 | 該次 run 的 Rebuild site data 步驟；Actions 的 Deploy Pages workflow |
| 過去的日期整列沒有紀錄（不只昨天） | 早上的檢查也沒跑 | Actions 頁面 Daily snapshot 是否被停用（repo 60 天無活動時 GitHub 會停用 cron）；GitHub 狀態頁 |
| 只有昨天沒有紀錄 | 早上的檢查還沒跑 | 不用處理，中午後再看 |
| 今天沒有紀錄 | 21:00 前是正常的 | 21:30 後還沒有，就照第一列檢查 |

判斷都是推測：repo 裡看不到 Actions 的 log、桌機與 Tailscale 的狀態。報告時寫明哪些是
從紀錄讀到的、哪些是推測。

## 報告格式

```
## 快照狀態
- 網站資料：YYYY-MM-DD（meta.json）
- 最後一次新快照：YYYY-MM-DD，N 天前
- 連續沒有新快照：N 天（failed N、unchanged N）；缺日：…

## 判斷
- （從紀錄讀到的）…
- （推測）最可能的原因 …

## 請你確認
- [ ] …（具體到哪個畫面、哪個設定）

## 補救
- 當天臺灣時間午夜前：出口節點恢復後，到 Actions → Daily snapshot → Run workflow（`force` 不勾）。
- 已經過了午夜：那天的資料補不回來，manifest 會留著 `failed`，不需要也不能補。
```

## 不可以做的事

- 在本機執行 `scripts/fetch_snapshot.py` 並提交快照：`data/raw/` 只由排程寫入，
  本機的快照會與機器人推上 `main` 的同名檔案衝突（CLAUDE.md §6.2）。
- 代為觸發 workflow、勾 `force` 重跑、執行 `trigger_snapshot.ps1`。
- 修改 `data/raw/_manifest.csv`，或替缺日補列。
- 印出或猜測 `TS_EXIT_NODE`、token、OAuth secret 的值，或請人類貼到對話裡。
- 只看到一兩天 `unchanged` 就斷定來源停更：偶爾一天沒更新是正常的，門檻是 3 天。

## 有 GitHub CLI 時

本機有 `gh` 才能直接看 run：
```powershell
gh run list --workflow daily-snapshot.yml --limit 5
gh run view <run-id> --log-failed
```
沒有就請人類開 Actions 頁面，告訴你失敗的步驟名稱與摘要內容。
