---
name: deliver
description: 把 StrayAtlas 完成的改動整理成交給人類提交的資料：依專案格式寫 `.git/msgNN.txt`（commit message）與 `.git/prNN.md`（PR 內文），用檢查腳本驗證，再給出 git add／commit／push 指令與 PR 標題。使用時機：使用者說「給我提交指令」「整理 commit」「寫 commit message」「準備 PR」「PR 內文」「可以提交了嗎」，或一段工作做完、要交付之前，即使沒提到 skill 名稱也要用。只產出文字檔與指令，不執行 git add、commit、push。
---

# 交付提交資料（deliver）

目的：每段工作的結尾都要交出 commit message、PR 內文與指令，格式規則散在 CLAUDE.md
§5、§6.1、§6.2、§6.4–§6.6，漏一條就要重寫。這個 skill 把它們收成固定步驟，格式交給
`scripts/check_message.py` 檢查。規則以 CLAUDE.md 為準，兩者不一致時改這個 skill。

**AI 不執行任何改動 repo 狀態的 git 指令**（`add`、`commit`、`push`、`switch`、`checkout`、
`restore`、`reset`、`rebase`、`stash`）。提交者對 history 負全責，最後一道確認由人類做
（§6.5）。唯讀指令（`status`、`log`、`diff`、`show`、`fetch`）可以用。

## 步驟

1. **確認分支與工作目錄**
   - `git branch --show-current`、`git status --short`。
   - 在 `main` 上：停下來，請人類開分支，給出指令即可：
     `git switch main; git pull --ff-only; git switch -c feature/YYYYMMDD-topic`。
   - 有不是這次任務改的檔案：可能是另一個工作階段或另一台電腦的改動。列出來問人類，
     不要放進 `git add`。
   - 還沒跑過檢查就先用 `preflight` skill；檢查沒過不交付。

2. **取編號**：在寫檔之前才查，因為其他工作階段可能剛用掉一號。
   ```powershell
   Get-ChildItem .git\msg*.txt, .git\pr*.md -Name
   ```
   取最大的 `NN`（含 `.unused` 檔）加一。PR 內文與該 PR 第一筆 commit 同號；同一個 PR
   的後續 commit 各用新號，不另寫 PR 內文。

3. **寫 commit message** 到 `.git/msgNN.txt`（UTF-8、LF、無 BOM）
   - 標題：`<prefix>: <英文祈使句>`，72 字元以內，句尾不加句號。prefix 依 §6.2：
     `feat`、`fix`、`docs`、`chore`、`refactor`、`ci`、`data`，可加範圍如 `docs(readme):`。
   - 標題與內文之間空一行，否則 git 會把整段當成標題。
   - 內文全部條列：`- ` 開頭、句號結尾、行寬 72，換行處縮排兩格。需要交代前提時，
     條列前可以有**一行**前言。每則條列一件事：改了什麼，或為什麼這樣改。
     面試官會掃 history，條列三秒讀完，散文會被略過。
   - 結尾空一行，加 `Assisted-by: Claude <noreply@anthropic.com>`。
   - 不寫 `.notes/` 工項清單的代號（A、F7、patch A）：讀者看不到那份清單。提到之前的 PR
     寫 `#NN`。
   - 範例：`git log --no-merges --format=%B -n 3` 看最近幾筆，或 CLAUDE.md §6.4。
   - 手動重建資料用固定訊息：`data: rebuild public/data from the YYYY-MM-DD snapshot`
     （§6.2 表格），內文照樣條列。

4. **寫 PR 內文**（要開 PR 時）到 `.git/prNN.md`，英文，行寬 80，四節依序：
   - `## Summary`：為什麼要改，一兩句；接續之前的 PR 就寫 `Follow-up to #NN.`
   - `## Commits`：這個 PR 的 commit 標題，條列。
   - `## Changes`：依檔案分組條列實際改動與理由。
   - `## Post-merge checks`：PR 階段驗證不了、合併後要逐項確認的事，用 `- [ ]`。
     workflow、`schedule`、部署、需要桌機或外部服務的設定都放這裡（§6.6）。
   - 寫到 Post-merge checks 為止，**不加** Generated with Claude Code 之類的結尾。

5. **檢查**
   ```powershell
   python .claude/skills/deliver/scripts/check_message.py .git/msgNN.txt .git/prNN.md
   ```
   有 `error` 就改到通過。`warning` 自己判斷：例如引用中文文件的章節名稱是合理的，
   在回覆裡說明即可。

6. **回覆**，依序給：
   1. 檔名與完整內容（程式碼區塊），讓人類不開檔也能審閱。
   2. 提交指令，`git add` 明列路徑，不用 `-A` 或 `.`：
      ```powershell
      git add <path> <path>
      git commit -F .git/msgNN.txt
      git push -u origin feature/YYYYMMDD-topic
      ```
   3. 要開 PR 時：PR 標題（沿用第一筆 commit 的標題）與內文檔名，並提醒合併方式用
      Create a merge commit、標題與說明沿用 GitHub 預設值。
   4. 合併後的本機指令：
      `git switch main; git pull --ff-only; git branch -d <branch>; git fetch --prune`。

## 修改與作廢

- 還沒提交的 message 要改：直接改原檔，並告訴人類改了哪裡。
- 計畫改變、用不到的檔案：改名為 `msgNN.unused.txt`。AI 沒有刪除權限，編號也不重複使用。

## 不可以做的事

- 執行 `git add`、`commit`、`push` 或任何切換分支、改寫 history 的指令。
- 加 `Co-Authored-By`、`Claude-Session`、「Generated with Claude Code」。
- 引用 `.notes/` 的內容或工項代號。
- 把 `.notes/` 的改動混進主 repo 的提交指令。`.notes/` 是另一個 repo，指令分開給，
  並用 `git -C .notes ...`。
- 把本機測試產生的 `data/raw/` 快照放進提交（§6.2：會與排程機器人當天的檔案衝突）。

## 疑難排解

| 現象 | 原因與處理 |
|---|---|
| 檢查腳本說有 CR 或 BOM | 寫檔工具或編輯器存成 CRLF／BOM。用 LF、無 BOM 重寫 |
| 標題超過 72 字元 | 範圍放進內文；標題只留動詞與對象 |
| 編號和另一個檔案撞號 | 另一個工作階段剛用掉。改用下一號，舊檔不動 |
| `git commit -F` 後 GitHub 上出現亂碼 | 檔案不是 UTF-8。重寫後請人類 `git commit --amend -F`（尚未 push 時） |
| 誤判工項代號（例如真的在講 `F1` 鍵） | 改寫措辭避開；真的必要就在回覆中說明，請人類決定 |
