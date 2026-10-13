# 架構決策

技術棧與主要的設計取捨。每一列寫的是為什麼這樣選，不是版本號。資料怎麼抓、怎麼部署見 [DATA-PIPELINE.md](DATA-PIPELINE.md)，本機開發見 [DEVELOPMENT.md](DEVELOPMENT.md)。

---

## 技術棧

| 層 | 選用 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite |
| 部署 | GitHub Pages（Project site，掛在 `/stray-atlas/` 子路徑） |
| 資料抓取與重建 | GitHub Actions cron（每日），有新快照時重建並觸發部署 |
| 前處理與分析 | Python（標準函式庫） |
| 產出格式 | JSON / GeoJSON（不產 PNG，例外見 `CLAUDE.md` §4.2） |
| 檢查與測試 | ESLint、Prettier、vue-tsc、vitest、Playwright；Python 用 ruff、pytest |

---

## 決策與理由

| 決策 | 選擇 | 理由 |
|---|---|---|
| 資料抓取 | GitHub Actions cron，而非本地手動 | 這份資料每日更新且不保留歷史，**漏抓的那天永久補不回來**。人工執行遲早會斷。此外 repo 的 commit history 本身即為「專案持續運作」的證明 |
| 來源停更偵測 | 連續 3 天沒有新快照就讓排程失敗 | 這類來源最難察覺的故障不是抓不到，而是每天回傳一份格式正確、內容卻凍結的檔案：run 全綠、網站安靜地停在舊資料。來源偶爾一天沒更新是正常的，所以門檻是 3 天 |
| 產出格式 | JSON / GeoJSON，而非 PNG | 靜態圖片在 demo 現場無法互動。同樣的前處理成本下，結構化資料可支援縣市篩選、犬貓切換、滯留天數區間篩選 |
| 開發順序 | 前端先於分析 | 先做前端會迫使我定義「前端要吃什麼格式的 JSON」，這份資料契約會反過來約束清理與分析腳本；反向操作容易產出大量前端用不到的中間產物 |
| 前端模型推論 | 不採用 ONNX Runtime Web | 以本資料量而言屬過度工程，預先算好結果存 JSON 查表即可 |
| 收容所定位 | 行政區形心，不呼叫 geocoder | 門牌級座標會讓精度看起來高於來源能支持的程度。行政區形心是資料自己說得出的答案 |
| 收容所開放時間 | 人工整理，每筆附來源與確認日，只連結認養須知 | 開放資料沒有這幾欄，卻是讀者出門前最需要的。官網沒寫的不推論；認養規定各縣市不同且會改，轉抄只會過時 |
| KDE 與 ECDF | 在 Python 算好存 JSON | 分析留在腳本裡、瀏覽器只負責畫，與其他頁面同一套分工。高斯 KDE 手寫十五行，不為此引入 scipy |
| 頻寬選擇 | 公開三段讓讀者切換 | KDE 的形狀有一半是頻寬的主張。用交叉驗證自動選一條反而把選擇藏起來，與這頁想說的事相反 |
| 地圖繪製 | 內嵌 SVG + d3-geo，自行實作縮放 | 不依賴圖磚服務、不需 API key，demo 現場沒有外部相依可壞。縮放只是一個 transform 加 wheel／pointer 事件，不值得為此引入 d3-zoom |
| 靜態檢查與格式 | ESLint 只管邏輯、Prettier 只管格式，兩者分開跑；Python 用 ruff 只檢查不重排；不掛 `eslint-plugin-prettier`，不裝 husky | 格式問題混進 ESLint 會讓每個空白都變成錯誤；單人專案由 CI 擋住就夠，不需要在本機 commit 時再攔一次。Prettier 不碰 Markdown 與 workflow：前者的表格由人排版，後者在 PR 階段無法實測，不該在格式化時被動到 |
| 測試範圍 | 單元測試只測 `src/lib` 的純函式與建置腳本，不做元件測試；另以 Playwright 對建置後的網站跑煙霧測試 | 這些函式算出來的數字會直接印在頁面上，錯了讀者看不出來；元件測試要維護一整套 DOM 假設，對一個人維護的專案划不來。煙霧測試只確認每一頁在 `/stray-atlas/` 子路徑下畫得出來、沒有失敗的請求，專抓「本機正常、部署後整頁空白」那一類錯誤 |
| 相依套件更新 | Dependabot 每月一次、同類合併成一個 PR、新版發布滿 7 天才提出；安全修補另行立即開 PR | 作品集不需要追最新版，每次更新都要能輕鬆審完、經 CI 驗證；剛發布就被撤下或被植入惡意程式的版本，多半在幾天內就會被發現 |
| `main` 的保護規則 | ruleset 只禁止刪除分支與 force push，**不設必要狀態檢查** | 必要檢查會連同直接 push 一起擋下，而每日排程機器人以 `GITHUB_TOKEN` 直接推 `main`；個人 repo 的 bypass 清單沒有 GitHub Actions（實測 Write 角色無效）。快照漏一天永久補不回來，紅燈合併隨時可以修 |
| 收容所介紹頁地圖 | Google Maps Embed，金鑰缺席時退回外部連結 | 單一地址的街道圖是讀者要的東西，自己畫不划算。金鑰由建置環境注入（本機 `.env.local` 的 `VITE_GOOGLE_MAPS_EMBED_KEY`、CI 的 secret `GOOGLE_MAPS_EMBED_KEY`），必須限制 HTTP referrer；沒有金鑰時頁面仍可用，不影響主地圖 |
