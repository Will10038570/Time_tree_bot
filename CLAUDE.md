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

A LINE chatbot that automates TimeTree calendar operations via Playwright browser automation. Users send text commands to a LINE chat, which triggers browser-based interactions with timetreeapp.com.

## 實作狀態

| 檔案 | 狀態 |
|------|------|
| `src/bot.py` | ✅ 完成 |
| `src/command_handler.py` | ✅ 完成（仍依賴尚未實作的 `TimeTreeAutomation`） |
| `function/operation_functions.py` | ✅ 完成（底層 Playwright helpers） |
| `function/event_functions.py` | ✅ 完成（`add_event` / `delete_event` / `get_events_on_date`） |
| `locators.py` | ❌ **尚未建立**（`testing.py` 的 import 目標，應公開 `function/` 的 API） |
| `src/automation.py` | ❌ **尚未建立**（`command_handler.py` 依賴的 `TimeTreeAutomation` class） |
| `tools/inspector.py` | ❌ **尚未建立**（UI 偵錯工具） |

架構目前有兩條線並行：
- `src/` 路線：`bot.py` → `command_handler.py` → `automation.py`（`TimeTreeAutomation` class，**尚未實作**）
- `function/` 路線：以 Page 為參數的函式集，由 `testing.py` 透過 `locators` 模組驅動

## Running the Project

**Start the LINE bot (main entry point):**
```bash
.venv\Scripts\activate   # Windows
python src/bot.py
```
Starts a Flask server on port 5000. Requires `.env` with `LINE_CHANNEL_ACCESS_TOKEN` and `LINE_CHANNEL_SECRET`.

**Run automation directly (for testing, once implemented):**
```bash
python src/automation.py
```
Edit the `__main__` block to test specific operations. Runs in headed (visible) browser mode with `page.pause()` at the end.

**Debug/inspect the TimeTree UI (once implemented):**
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

Each action dumps a JSON snapshot to `debug/` and calls `page.pause()` for interactive inspection. If `data/session.json` is missing, prompts for manual login before saving the session.

## Architecture

### LINE Bot 路線（src/）

```
src/bot.py (Flask webhook /callback)
  → src/command_handler.py (parses text → structured command)
    → src/automation.py (TimeTreeAutomation class)  ← 尚未實作
      → timetreeapp.com
```

**`src/bot.py`** — LINE Messaging API v3 webhook. Calls `free_port()` on startup to kill any process using port 5000 (`netstat`/`taskkill`, Windows-only). Passes each incoming message to `command_handler.py` and replies with the result.

**`src/command_handler.py`** — Parses raw text into `add`/`delete` commands and invokes the automator with `headless=True`. Uses `redirect_stdout` to capture all `print()` output from `automation.py` and return it as the LINE reply. This means anything printed inside `add_event()`/`delete_event()` — including debug lines — becomes visible to the LINE user.

**`src/automation.py`** _(待實作)_ — Context manager class `TimeTreeAutomation`. Public methods: `add_event(date_start, title, group_name, color_name, date_end)` and `delete_event(date_start, title)`. Loads browser state from `data/session.json`.

### 函式庫路線（function/）

```
testing.py
  → locators (尚未建立的橋接模組)
    → function/event_functions.py   (add_event, delete_event, get_events_on_date)
      → function/operation_functions.py  (goto_calendar, _goto_target_month, _find_month_cell, ...)
        → timetreeapp.com
```

**`function/operation_functions.py`** — Page-level Playwright helpers. Key functions:
- `log_in(page)` — 填入 `TIMETREE_EMAIL`/`TIMETREE_PASSWORD` 並登入
- `goto_calendar(page)` — 前往 `/calendars` 並等 networkidle
- `_goto_target_month(page, date)` — 重置到今日再點 Next/Previous month 到目標月份
- `_find_month_cell(page, day)` — 以兩個 "1" 之間的範圍定位當月 gridcell
- `_events_in_cell(page, cell)` — 用 bounding box 找出視覺上在格子內的事件按鈕

**`function/event_functions.py`** — 高階操作（使用相對 import 引入 operation_functions）:
- `add_event(page, title, start, end=None)` — 點 `calendar-bar-event-add-button` 開啟表單，固定選色 `Deep sky blue`
- `delete_event(page, title, date)` — `title="all"` 時刪除當天所有事件（while 迴圈）
- `get_events_on_date(page, date)` — 回傳指定日期的事件名稱清單

**`testing.py`** — 批次測試工具。產生 20 筆隨機分布在 2026-06 ~ 2026-07 的 test 事件，透過 `locators` 模組（尚未建立）驅動 add/delete 流程。`_fmt_date()` 中使用 `%#d`（Windows 專用，去除日期零填充）。

## Import Path Convention

**`src/` 路線**：`bot.py` 和 `command_handler.py` 使用裸模組名稱 import（`from automation import ...`），`src/` 必須在 `sys.path` 中。`python src/bot.py` 啟動時 Python 自動添加。**不要**改成 `from src.automation import ...`。

**`function/` 套件**：`event_functions.py` 使用相對 import（`from .operation_functions import ...`），必須作為套件使用（如 `from function.event_functions import add_event`），不能直接執行單一檔案。

## Selector Strategy

TimeTree uses CSS Modules with dynamic class names that change on UI updates. All interactive operations use a fallback chain:

```
data-test-id  →  aria-label  →  role  →  :has-text()  →  hardcoded className
  (most stable)                                              (most fragile)
```

Three hardcoded CSS classes that are likely to break first:
- `button._1hsbcq11` — sidebar calendar group toggle buttons (`select_sidebar_calendar`)
- `_72xel51` — indicates a calendar group is selected
- `span.lndlxo6` — event title span inside draggable event buttons

When selectors break, run `tools/inspector.py` with the appropriate `--action` to capture the new DOM structure.

## Command Syntax

Commands parsed by `command_handler.py`:
- `add <title> <date> [end_date] [group] [color]` — Create event
- `delete <date>` — List events on that date
- `delete <title> <date>` — Delete specific event

Date formats: `YYYY-MM-DD` or `MM-DD` (auto-prefixes with `2026-`). The year prefix is hardcoded in `_normalize_date()` and `delete_event()` — update when the year changes. Default group: `私人`. Default color: `Emerald green`.

## Key Files

| File | Purpose |
|------|---------|
| `data/session.json` | Playwright browser storage state (login session). Delete to force re-login. |
| `.env` | `LINE_CHANNEL_ACCESS_TOKEN` and `LINE_CHANNEL_SECRET` |
| `codegen_row.py` | Playwright codegen 原型，展示 session-based 登入流程（根目錄，非正式模組） |
| `tools/inspector.py` | UI inspection tool — run when selectors break after TimeTree UI updates（待實作） |
| `debug/` | JSON snapshots and screenshots produced during debugging |
| `docs/PROJECT_REPORT.md` | Detailed architecture report with full method reference |

## Dependencies

Managed in `.venv/` (Python 3.11.9). Key packages: `playwright`, `flask`, `line-bot-sdk`, `python-dotenv`. Install Playwright browsers with `playwright install chromium` if missing.
