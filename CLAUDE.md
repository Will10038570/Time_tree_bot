# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 角色設定

你是一位專業的**系統架構設計師**與**軟體工程師**。在此專案中工作時，請：

- 以**繁體中文**回答所有問題與提供說明（請用中文回答我，**絕對不可使用韓文**）
- 從系統架構角度分析問題，考量模組間的耦合性、擴充性與維護性
- 提出具體、可執行的技術方案，並說明設計取捨
- 程式碼撰寫遵循清晰、可維護的原則

## 互動規則

- 使用者輸入 `?` 時，對當前討論的對象（程式碼、function、class、概念）進行說明

## Project Overview

A LINE chatbot that automates TimeTree calendar operations via Playwright browser automation. Users send text commands to LINE, which are interpreted by Gemini AI and converted into structured JSON commands, then executed against timetreeapp.com.

## 實作狀態

| 檔案 | 狀態 |
|------|------|
| `src/main.py` | ✅ 完成（中控 entry point，管理所有 Manager 生命週期） |
| `src/WebhookManager.py` | ✅ 完成（pyngrok tunnel 管理） |
| `src/GeminiManager.py` | ✅ 完成（Gemini 意圖解析，per-user session 隔離） |
| `src/TimeTreeOperator.py` | ✅ 完成（橋接 `function/` 執行 add / delete / query） |
| `src/QueueWorker.py` | ✅ 完成（背景 thread，解決 Webhook 30 秒超時，用 push message 回覆） |
| `src/LineBotManager.py` | ✅ 完成（Flask webhook，立即回覆「處理中」+ 入列） |
| `function/command.py` | ✅ 完成（add / delete / query 三種指令執行） |
| `function/operation_functions.py` | ✅ 完成（底層 Playwright helpers） |
| `function/event_functions.py` | ✅ 完成（`add_event` / `delete_event` / `get_events_on_date`） |
| `ai_agent/AI_AGENT.md` | ✅ 完成（Gemini system prompt，含 query 指令規則） |
| `configs/json_example.yml` | ✅ 完成（JSON schema，command 支援 add / delete / query） |
| `tools/inspector.py` | ❌ **尚未建立**（UI 偵錯工具） |

## Running the Project

**啟動 LINE Bot（主要 entry point）：**
```bash
.venv\Scripts\activate   # Windows
python src/main.py
```
需要 `.env` 設定 `LINE_CHANNEL_ACCESS_TOKEN`、`LINE_CHANNEL_SECRET`、`GEMINI_API_KEY`、`NGROK_AUTHTOKEN`（可選）。

**Debug/inspect the TimeTree UI（一旦實作）：**
```bash
python tools/inspector.py --action <action> [--date MM-DD] [--title 標題]
```

Actions:
- `sidebar` — dump sidebar calendar buttons
- `day-panel` — click a date cell, dump day panel (requires `--date`)
- `create-form` — open the event creation form (requires `--date`)
- `color-select` — open color dropdown (requires `--date --title`)
- `delete-menu` — open event delete menu (requires `--date --title`)
- `full` — dump entire page + screenshot

## Architecture

### 系統流程

```
LINE User
  → LineBotManager (Flask /callback)   ← 立即回覆「處理中」
      → QueueWorker.enqueue()           ← 入列，避免 30 秒 Webhook 超時
          → GeminiManager.parse()       ← Gemini AI 解析自然語言 → JSON
          → TimeTreeOperator.run()      ← redirect_stdout 捕捉 print 輸出
              → function/command.py     ← Playwright 操作 timetreeapp.com
          → QueueWorker._push()         ← LINE push message 回傳結果
```

### Manager 生命週期（src/main.py）

`main.py` 依序初始化並啟動所有元件，並於 SIGINT/SIGTERM 時依序停止：

1. **WebhookManager** — 用 pyngrok 建立 HTTPS tunnel，印出 `/callback` URL
2. **GeminiManager** — 載入 `GEMINI_API_KEY`、讀取 system prompt（`ai_agent/AI_AGENT.md`）、載入 JSON schema（`configs/json_example.yml`），每個 user_id 維護獨立的對話 history
3. **TimeTreeOperator** — 無狀態橋接層，`run(cmd)` 呼叫 `function/command.run_command()`，用 `redirect_stdout` 捕捉輸出為字串回傳
4. **QueueWorker** — daemon thread 消費佇列，依序呼叫 Gemini 解析 → Operator 執行 → LINE push message
5. **LineBotManager** — Flask app，webhook 驗簽後立即以 reply token 回覆「⏳ 處理中...」，再 `enqueue()` 給 QueueWorker

### 函式庫路線（function/）

```
function/command.py (run_command, command_add, command_delete, command_query)
  → function/event_functions.py  (add_event, delete_event, get_events_on_date)
    → function/operation_functions.py  (log_in, goto_calendar, select_group, ...)
      → timetreeapp.com
```

**`function/command.py`** — 每次指令都用 `sync_playwright()` 開新 browser，執行完後 `context.storage_state()` 更新 session。`initial_page()` 負責登入或載入 session、選擇群組。

**`function/operation_functions.py`** — Page-level Playwright helpers:
- `log_in(page)` — 填入 `TIMETREE_EMAIL`/`TIMETREE_PASSWORD` 並登入
- `goto_calendar(page)` — 前往 `/calendars` 並等 networkidle
- `select_group(page, group)` — 側欄點選指定行事曆群組
- `_goto_target_month(page, date)` — 重置到今日再點 Next/Previous month
- `_find_month_cell(page, day)` — 以兩個 "1" 之間的範圍定位當月 gridcell
- `_events_in_cell(page, cell)` — 用 bounding box 找出格子內的事件按鈕

**`function/event_functions.py`** — 高階操作：
- `add_event(page, title, start, end=None, label=None)`
- `delete_event(page, title, date_start)` — `title="all"` 時 while 迴圈刪除當天全部
- `get_events_on_date(page, date)` — 回傳事件名稱清單

## Import Path Convention

**`src/` 路線**：所有 Manager 使用裸模組名稱 import（`from GeminiManager import ...`），`src/` 必須在 `sys.path` 中。`python src/main.py` 啟動時 Python 自動添加。**不要**改成 `from src.GeminiManager import ...`。

**`function/` 套件**：`event_functions.py` 使用相對 import（`from .operation_functions import ...`），必須作為套件使用（如 `from function.event_functions import add_event`），不能直接執行單一檔案。`TimeTreeOperator` 用 `sys.path.insert(0, project_root)` 確保可從 `src/` 引入 `function/`。

## Gemini JSON Schema

Gemini 輸出固定符合 `configs/json_example.yml` 定義的 schema：

| 欄位 | 必填 | 說明 |
|------|------|------|
| `command` | ✅ | `add` / `delete` / `query` |
| `date_start` | ✅ | `YYYY-MM-DD` |
| `title` | query 時可省略 | 刪除全部時固定為 `"all"` |
| `date_end` | ❌ | 多日活動結束日期 |
| `group` | ❌ | 行事曆群組名稱 |
| `label` | ❌ | `Apple red` / `Deep sky blue` / `Emerald green` |

## Selector Strategy

TimeTree 使用 CSS Modules，class name 會隨 UI 更新變動。操作優先順序：

```
data-test-id  →  aria-label  →  role  →  :has-text()  →  hardcoded className
  (最穩定)                                                   (最脆弱)
```

最容易失效的 hardcoded class：
- `button._1hsbcq11` — sidebar calendar group toggle buttons
- `_72xel51` — 表示 calendar group 已被選取
- `span.lndlxo6` — draggable event button 內的事件標題 span

Selector 失效時，用 `tools/inspector.py` 對應 `--action` 捕捉新 DOM 結構。

## Key Files

| File | Purpose |
|------|---------|
| `data/session.json` | Playwright browser storage state（登入 session）。刪除可強制重新登入 |
| `.env` | `LINE_CHANNEL_ACCESS_TOKEN`、`LINE_CHANNEL_SECRET`、`GEMINI_API_KEY`、`NGROK_AUTHTOKEN`、`TIMETREE_EMAIL`、`TIMETREE_PASSWORD` |
| `ai_agent/AI_AGENT.md` | Gemini system prompt，包含輸出格式、範例、日期自動補年等規則 |
| `configs/json_example.yml` | Gemini structured output 的 JSON schema 定義 |
| `debug/` | JSON snapshots and screenshots produced during debugging |

## Dependencies

Managed in `.venv/` (Python 3.11.9). Key packages: `playwright`, `flask`, `line-bot-sdk`, `google-genai`, `pyngrok`, `python-dotenv`, `pyyaml`. Install Playwright browsers with `playwright install chromium` if missing.
