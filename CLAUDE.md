# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 角色設定

你是一位專業的**系統架構設計師**與**軟體工程師**。在此專案中工作時，請：

- 以**繁體中文**回答所有問題與提供說明（請用中文回答我）
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
| `src/command_handler.py` | ✅ 完成 |
| `src/automation.py` | ❌ **尚未建立**（核心自動化模組，缺少此檔案時 bot 無法運作） |
| `tools/inspector.py` | ❌ **尚未建立**（UI 偵錯工具） |

`command_handler.py` 已寫好 `from automation import TimeTreeAutomation`，但 `src/automation.py` 尚未實作。

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

```
src/bot.py (Flask webhook /callback)
  → src/command_handler.py (parses text → structured command)
    → src/automation.py (Playwright browser automation)  ← 尚未實作
      → timetreeapp.com
```

**`src/bot.py`** — LINE Messaging API v3 webhook. Calls `free_port()` on startup to kill any process using port 5000 (`netstat`/`taskkill`, Windows-only). Passes each incoming message to `command_handler.py` and replies with the result.

**`src/command_handler.py`** — Parses raw text into `add`/`delete` commands and invokes the automator with `headless=True`. Uses `redirect_stdout` to capture all `print()` output from `automation.py` and return it as the LINE reply. This means anything printed inside `add_event()`/`delete_event()` — including debug lines — becomes visible to the LINE user.

**`src/automation.py`** _(待實作)_ — Core automation class `TimeTreeAutomation` (context manager). Key behaviors:
- Loads browser state from `data/session.json` to avoid re-login
- Uses multiple selector fallback strategies (CSS, ARIA, data-test-id) due to TimeTree's dynamic UI
- `add_event()` and `delete_event()` are the primary public methods
- `add_event()` always opens the create form by clicking **day 15** of the target month (not the actual target date) — the real dates are filled in via the date picker fields. This is a deliberate workaround for unreliable behavior when clicking the target day's "+" button directly.
- Debug methods (`dump_create_dialog_elements()`, `debug_color_select_state()`) write JSON snapshots to `debug/` for troubleshooting selector breakage

## Import Path Convention

`bot.py` 和 `command_handler.py` 都使用**裸模組名稱** import（`from automation import ...`、`from command_handler import ...`），不含套件前綴。這代表：

- 所有 `src/` 內的模組必須在 `src/` 是 `sys.path` 的一部分時才能運作
- 使用 `python src/bot.py` 啟動時，Python 會自動將 `src/` 加入路徑，運作正常
- **不要**改成 `from src.automation import ...`，會破壞現有的 import 結構

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
