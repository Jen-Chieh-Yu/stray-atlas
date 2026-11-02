---
name: preflight
description: 在 StrayAtlas 提交或開 PR 之前，依改動的檔案挑出並執行與 CI 相同的檢查（ESLint、Prettier、vue-tsc、vitest、vite build、Playwright 煙霧測試、ruff、pytest、資料重建比對），逐項回報結果與沒跑的項目。使用時機：使用者說「跑檢查」「跑測試」「提交前檢查」「CI 會不會過」「lint 一下」「build 得過嗎」，或改完程式、準備用 deliver 交付之前，即使沒提到 skill 名稱也要用。只檢查與回報；要修正或自動格式化先問。
---

# 提交前檢查（preflight）

目的：CI（`.github/workflows/ci.yml`）有前端與資料管線兩個 job，紅燈合併雖然能修，但
推上去才發現要多一輪 commit。這個 skill 依改動範圍在本機跑同一組檢查，CLAUDE.md §8.1
是依據。

## 步驟

1. **找出改動的檔案**（含未追蹤的檔案）
   ```powershell
   git diff --name-only main...HEAD; git status --short
   ```

2. **依路徑決定要跑什麼**。同時符合多列就都跑；拿不準時全跑。

   | 改動 | 檢查 |
   |---|---|
   | `src/`、`e2e/`、`index.html`、`public/`（`public/data/` 以外）、`vite.config.ts`、`tsconfig*.json`、`package*.json`、`eslint.config.*`、`.prettierrc*`、`.nvmrc` | 前端全套（下方 A） |
   | `public/data/` | `npm run build`、`npm run test:e2e`：資料形狀變了，頁面可能畫不出來 |
   | `scripts/*.py`、`tests/`、`ruff.toml`、`.claude/skills/**/*.py` | Python（下方 B） |
   | `scripts/build_*.py`、`scripts/clean.py`、`scripts/common.py`、`scripts/geocode.py`、`data/reference/` | B，再加資料重建比對（下方 C） |
   | `.github/workflows/` | 本機無法實跑。列出要寫進 PR「Post-merge checks」的驗證項目（§6.6） |
   | `*.ps1` | PowerShell 語法解析（下方 D） |
   | 只有 `*.md` | 不必跑：Prettier 不碰 Markdown（`.prettierignore`），在報告裡寫明 |

3. **執行**。每個指令分開執行，才知道是哪一個失敗。

   **A. 前端**（依序，便宜的在前）
   ```powershell
   npm run lint
   npm run format:check
   npm run type-check
   npm test
   npm run build
   npm run test:e2e
   ```
   - `test:e2e` 測的是 `dist/`，一定要在 `build` 之後。
   - 新增路由時，確認 `e2e/smoke.spec.ts` 的 `ROUTES` 有加一行（§8.1）。

   **B. Python**
   ```powershell
   python -m ruff check .
   python -m pytest -q
   ```
   用 `python -m`：`ruff` 不一定在 PATH 上。

   **C. 資料重建比對**：與 CI 的 pipeline job 相同，證明 `public/data/` 與建置腳本一致。
   ```powershell
   python scripts/build_all.py
   python .claude/skills/preflight/scripts/rebuild_drift.py
   ```
   - 只差 `generated_at` 的檔案：重建必然產生的雜訊，不該提交。告訴人類可用
     `git restore public/data` 還原（AI 不執行）。
   - 有其他差異：改了建置腳本卻沒重建，或重建結果與預期不同。回報差異檔案，
     由人類決定是一起提交重建結果，還是先找原因。

   **D. PowerShell 語法**
   ```powershell
   $e = $null; [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path <file>), [ref]$null, [ref]$e) | Out-Null; $e
   ```
   沒有輸出就是沒有語法錯誤。腳本本身不要執行：`trigger_snapshot.ps1` 會真的觸發 workflow。

4. **失敗時**
   - 貼出關鍵錯誤（檔案、行號、訊息），判斷是這次的改動造成的，還是 `main` 本來就有。
     比對方式：失敗的檔案在不在步驟 1 的清單裡。不要用 `git stash` 切回去驗證。
   - 修正前先說明要改什麼（CLAUDE.md §11：改 repo 檔案前先給 diff）。
   - Prettier 失敗：提議只格式化改動過的檔案（`npx prettier --write <files>`），
     同意後才執行；不要對整個 repo 跑 `npm run format`。

5. **報告**，固定格式：

   ```
   ## 檢查結果
   | 檢查 | 結果 | 備註 |
   |---|---|---|
   | npm run lint | 通過 | |
   | python -m pytest -q | 失敗 | tests/test_x.py::test_y — 一句話原因 |

   ## 沒有跑的
   - npm run test:e2e — 只改了 Python，前端不受影響
   - .github/workflows/daily-snapshot.yml — PR 階段無法實測，合併後要確認：…
   ```

   「沒有跑的」一定要寫：省略的項目和失敗的項目一樣重要，人類要知道哪裡沒被驗證。

## 不可以做的事

- 為了讓檢查通過而修改測試、放寬斷言、關掉 lint 規則或加 `# noqa`，除非人類同意。
- 未經同意執行 `npm ci`（會刪掉重裝 `node_modules`）、`npm run format`、`pip install`、
  `npx playwright install`（下載瀏覽器）。
- 執行 `scripts/fetch_snapshot.py`（會連來源並寫入 `data/raw/`）或任何 `trigger_*` 腳本。
- 報告「全部通過」卻省略沒跑的項目。

## 疑難排解

| 現象 | 原因與處理 |
|---|---|
| `ruff` 無法辨識 | 不在 PATH，改用 `python -m ruff`；沒有安裝就請人類執行 `pip install "pytest>=9,<10" "ruff>=0.15,<0.16"`（與 CI 相同版本） |
| `npm ci` 或 `npm run` 說 engine 不符 | `.npmrc` 設了 `engine-strict=true`；Node 版本以 `.nvmrc` 為準（24） |
| `test:e2e` 說找不到瀏覽器 | 新電腦第一次要 `npx playwright install chromium`，先問人類 |
| `test:e2e` 全部 404 | 沒有先 `npm run build`，或 `dist/` 是舊的 |
| 本機 `type-check` 過、CI 失敗 | `node_modules` 與 `package-lock.json` 不一致（例如剛合併 Dependabot 的 PR）；請人類 `npm ci` 後重跑 |
| `build_all.py` 失敗 | 看錯誤是哪一支 `build_*.py`；`data/reference/shelter-info.json` 格式錯誤也會讓重建失敗（`docs/DATA-PIPELINE.md`〈收容所開放時間〉） |
