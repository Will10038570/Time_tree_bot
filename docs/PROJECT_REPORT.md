# 專案技術分析報告

> **專案名稱**：TimeTree LINE Bot 自動化系統  
> **分析日期**：2026-05-10  
> **分析者**：Claude Code（系統架構設計師 / 軟體工程師角色）

---

## 目錄

1. [系統概覽](#1-系統概覽)
2. [系統架構圖](#2-系統架構圖)
3. [模組詳細分析](#3-模組詳細分析)
   - [bot.py](#31-botpy--line-webhook-伺服器)
   - [command_handler.py](#32-command_handlerpy--指令解析層)
   - [timetree_automation.py](#33-timetree_automationpy--瀏覽器自動化核心)
   - [test.py](#34-testpy--除錯工具)
4. [類別與方法總覽](#4-類別與方法總覽)
5. [變數與常數總覽](#5-變數與常數總覽)
6. [資料流分析](#6-資料流分析)
7. [設計模式與架構決策](#7-設計模式與架構決策)
8. [已知問題與技術債](#8-已知問題與技術債)
9. [系統依賴關係](#9-系統依賴關係)

---

## 1. 系統概覽

這是一個整合 **LINE Messaging API** 與 **Playwright 瀏覽器自動化** 的行事曆管理機器人。

使用者透過 LINE 傳送文字指令（如 `add 開會 05-20`），後端解析後驅動 Chromium 瀏覽器操作 [timetreeapp.com](https://timetreeapp.com/calendars)，完成新增或刪除行程，再將結果回傳給使用者。

### 技術堆疊

| 層級 | 技術 |
|------|------|
| 訊息入口 | LINE Messaging API v3 |
| Web 框架 | Flask |
| 瀏覽器自動化 | Playwright (Chromium) |
| 語言 | Python 3.11.9 |
| 環境管理 | python-dotenv |

---

## 2. 系統架構圖

### 整體系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│                          使用者端                                │
│                    LINE App（傳送文字指令）                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTPS POST Webhook
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       bot.py  (Flask)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  /callback  端點                                         │   │
│  │  1. 驗證 X-Line-Signature                                │   │
│  │  2. 解析 MessageEvent                                    │   │
│  │  3. 呼叫 handle(text)                                    │   │
│  │  4. 用 reply_token 回傳結果                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│  Port: 5000    free_port() 啟動時清理佔用行程                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │  純文字字串
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   command_handler.py                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  _parse(text)                                            │   │
│  │  ├── 解析指令類型（add / delete）                       │   │
│  │  ├── 驗證日期格式                                       │   │
│  │  └── 標準化日期（MM-DD → 2026-MM-DD）                  │   │
│  │                                                          │   │
│  │  handle(text)                                            │   │
│  │  ├── 呼叫 _parse 取得 (cmd, kwargs)                     │   │
│  │  ├── 建立 TimeTreeAutomation(headless=True)             │   │
│  │  └── 用 redirect_stdout 捕獲輸出作為回覆訊息           │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │  結構化 kwargs
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                timetree_automation.py                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TimeTreeAutomation 類別（Context Manager）              │   │
│  │                                                          │   │
│  │  add_event()                   delete_event()            │   │
│  │  ├── select_sidebar_calendar   ├── select_sidebar_cal..  │   │
│  │  ├── goto_target_month         ├── goto_target_month     │   │
│  │  ├── click_day_cell            ├── click_day_cell        │   │
│  │  ├── open_create_event         ├── _collect_panel_events │   │
│  │  ├── fill_title                ├── match title           │   │
│  │  ├── set_start/end_date        └── _delete_one_event()   │   │
│  │  └── ensure_color + submit                               │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │  Playwright CDP
                           ▼
               ┌───────────────────────┐
               │  Chromium 瀏覽器      │
               │  timetreeapp.com      │
               │  session: storage.json│
               └───────────────────────┘
```

### 選擇器策略架構

TimeTree 的 UI 會動態更改 class 名稱，因此每個操作都使用多層 fallback 選擇器：

```
優先嘗試 data-test-id  →  aria-label  →  role  →  :has-text()  →  className（hardcoded）
          最穩定                                                        最脆弱
```

---

## 3. 模組詳細分析

### 3.1 `bot.py` — LINE Webhook 伺服器

**職責**：系統的最外層入口，負責接收 LINE 平台的 Webhook 事件並回傳結果。

#### 關鍵函式

| 函式 | 說明 |
|------|------|
| `free_port(port)` | 啟動時透過 `netstat -ano` 找到佔用指定 port 的 PID，使用 `taskkill /F` 強制終止（Windows 專用） |
| `callback()` | Flask 路由 `/callback`，驗證 LINE 簽章後交給 `handler` 處理 |
| `handle_message(event)` | 從 `MessageEvent` 取出文字，呼叫 `command_handler.handle()`，再用 `reply_token` 回傳 |
| `_shutdown(*_)` | 捕獲 SIGINT/SIGTERM，呼叫 `os._exit(0)` 強制結束 |

#### 初始化流程

```python
# 1. 從 .env 載入環境變數
load_dotenv()

# 2. 建立 LINE SDK 設定物件（含 access token）
configuration = Configuration(access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"])

# 3. 建立 Webhook 驗證器（用 channel secret 驗章）
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])
```

---

### 3.2 `command_handler.py` — 指令解析層

**職責**：將 LINE 傳來的原始文字轉換為結構化指令，並協調自動化執行。

#### 常數

| 常數 | 值 | 用途 |
|------|----|------|
| `DATE_FULL` | `r"^\d{4}-\d{2}-\d{2}$"` | 完整日期格式正規表達式 |
| `DATE_SHORT` | `r"^\d{2}-\d{2}$"` | 簡短日期格式正規表達式 |
| `DEFAULT_GROUP` | `"私人"` | 未指定群組時的預設值 |
| `DEFAULT_COLOR` | `"Emerald green"` | 未指定顏色時的預設值 |

#### 函式說明

| 函式 | 輸入 | 輸出 | 說明 |
|------|------|------|------|
| `_normalize_date(s)` | `"MM-DD"` | `"2026-MM-DD"` | 短日期補上年份 |
| `_is_date(s)` | 任意字串 | `bool` | 判斷是否為有效日期格式 |
| `_parse(text)` | 原始文字 | `(cmd, kwargs)` | 核心解析邏輯，失敗拋 `ValueError` |
| `handle(text)` | 原始文字 | 回覆字串 | 公開入口，捕獲 stdout 作為回傳內容 |

#### 指令解析邏輯

```
輸入文字 → split() → parts[0] 為 cmd

cmd == "add"：
  parts = [add, title, date_start, ?date_end, ?group, ?color...]
  └── title = parts[1]
  └── date_start = parts[2]（必須是日期）
  └── rest = parts[3:]
      ├── rest[0] 是日期 → date_end
      ├── 下一個 → group_name
      └── 剩餘全部 join → color_name（允許空格，如 "Emerald green"）

cmd == "delete"：
  parts[-1] 是日期 → date_start
  parts[1:-1] join → title（可為空）
```

#### stdout 捕獲技巧

```python
buf = io.StringIO()
with redirect_stdout(buf):
    tt.add_event(**kwargs)      # 所有 print() 輸出被攔截
return buf.getvalue().strip()   # 作為 LINE 回覆訊息
```

---

### 3.3 `timetree_automation.py` — 瀏覽器自動化核心

**職責**：封裝所有與 TimeTree 網頁的互動邏輯。

#### 模組常數

| 常數 | 值 | 用途 |
|------|----|------|
| `BASE_URL` | `"https://timetreeapp.com/calendars"` | 日曆首頁網址 |
| `STORAGE_FILE` | `"timetree_storage.json"` | 瀏覽器 session 存檔路徑 |

---

#### 類別：`TimeTreeAutomation`

實作 Python **Context Manager**（`with` 語法），確保 Playwright 資源在任何情況下都能正確釋放。

##### 建構子參數

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `storage_file` | `"timetree_storage.json"` | 瀏覽器 session 檔案路徑 |
| `headless` | `False` | 是否無頭模式（LINE Bot 使用時設為 `True`） |

##### 實例屬性

| 屬性 | 類型 | 說明 |
|------|------|------|
| `self.storage_file` | `str` | session 檔案路徑 |
| `self.headless` | `bool` | 無頭模式開關 |
| `self.playwright` | `Playwright` | Playwright 主物件 |
| `self.browser` | `Browser` | Chromium 瀏覽器實例 |
| `self.context` | `BrowserContext` | 含 session 狀態的瀏覽器 context |
| `self.page` | `Page` | 操作中的分頁 |

##### Context Manager 行為

```python
def __enter__(self):
    # 啟動 Playwright → 啟動 Chromium（slow_mo=150ms）
    # 載入 timetree_storage.json 的 session 狀態
    # 回傳 self

def __exit__(self, ...):
    # 無論成功失敗都關閉 browser 與 playwright
    # 不抑制例外
```

---

#### 方法分類總覽

##### 導航類

| 方法 | 說明 |
|------|------|
| `goto_calendars()` | 前往 `BASE_URL`，等待 networkidle + 1.5 秒 |
| `ensure_monthly_view()` | 確保日曆切換到月視圖，使用 3 種 selector fallback |
| `get_visible_month_ym()` | 讀取目前顯示月份（`YYYY-MM` 格式），從 `<time datetime>` 屬性取得 |
| `goto_target_month(target_date)` | 反覆點上/下月按鈕直到到達目標月份，最多 24 次迭代（防無窮迴圈） |
| `click_day_cell(day)` | 在月曆格中找到指定日數的格子並點擊 |

##### 事件新增類

| 方法 | 說明 |
|------|------|
| `open_create_event()` | 點擊新增活動按鈕，5 種 selector fallback |
| `fill_title_if_possible(title)` | 嘗試填入標題，12 種 selector fallback，回傳 `(bool, selector_used)` |
| `select_sidebar_calendar(group_name)` | 在側邊欄切換到指定群組，關閉其他已選群組 |
| `open_color_select()` | 開啟顏色選擇下拉，4 種點擊策略（包含 `force=True` 與 JS `el.click()`） |
| `click_color_option(color_name)` | 點選指定顏色選項，5 種 selector fallback |
| `ensure_color(color_name)` | 組合 `open_color_select` + `click_color_option` |
| `set_start_date(date_str)` | 填入開始日期（格式轉換：`YYYY-MM-DD` → `Fri, May 20, 2026`） |
| `set_end_date(date_str)` | 填入結束日期 |
| `_set_date_picker(test_id, date_str)` | 底層日期填入邏輯（click×3 全選 → fill → 點 title 失焦） |
| `add_event(...)` | **主要公開方法**，完整新增流程 |

##### 事件刪除類

| 方法 | 說明 |
|------|------|
| `_get_day_cell(day)` | 取得月曆中指定日的格子 locator |
| `_collect_panel_events()` | 收集點擊日期後面板中的所有 `button[draggable="true"]` 事件 |
| `_collect_titles_from_panel()` | 從 `_collect_panel_events()` 只取標題清單 |
| `_extract_event_title(locator)` | 先嘗試 `span.lndlxo6`，失敗則 `inner_text()` |
| `_delete_one_event()` | 點擊刪除按鈕，11 種 selector fallback，處理二次確認對話框 |
| `delete_event(...)` | **主要公開方法**，title=None 時列出當天事件，否則刪除符合的第一筆 |

##### 除錯 / 診斷類

| 方法 | 輸出檔案 | 說明 |
|------|----------|------|
| `dump_create_dialog_elements(out_file)` | `create_dialog_elements.json` | 擷取 dialog 中所有互動元素的 HTML、屬性資訊 |
| `debug_color_select_state(tag)` | `create_dialog_elements_{tag}.json` | 印出顏色選擇相關 selector 的存在狀態 + body 預覽 |
| `dump_day_cell_elements(day, out_file)` | `day_cell_debug.json` | 擷取指定日格子內所有子元素 |
| `_dump_all_clickable(out_file)` | `delete_clickable_debug.json` | 擷取頁面上所有可點擊元素 |
| `create_event_scaffold(...)` | `create_dialog_elements.json` | 建立事件表單骨架並回傳除錯資訊（dict） |
| `read_current_calendar_ids()` | — | 從 `localStorage` 讀取目前選中的 calendar IDs |

---

#### `add_event()` 詳細流程

```
add_event(date_start, title, group_name, color_name, date_end)
│
├── 日期格式正規化（MM-DD → 2026-MM-DD）
├── 驗證 date_end >= date_start
│
├── goto_calendars()
├── ensure_monthly_view()
├── select_sidebar_calendar(group_name)  ← 切換到指定群組
├── [debug] dump after sidebar
├── goto_target_month(date_start)
├── click_day_cell(15)                   ← 固定點第 15 日開啟表單
├── open_create_event()
├── [debug] dump after form open
│
├── fill title（textarea[name="title"]）
├── set_start_date(date_start)
├── set_end_date(date_end)               ← 選填
├── ensure_color(color_name)
│
└── 點擊 Submit（5 種 selector fallback）
    └── 成功 → print 成功訊息
    └── 失敗 → dump debug → raise RuntimeError
```

> **注意**：`click_day_cell(15)` 固定點第 15 日（非目標日期）來開啟新增表單，實際日期透過 `set_start_date()` 填入。這是因為直接點選目標日期的「+」按鈕不穩定。

---

#### `delete_event()` 詳細流程

```
delete_event(date_start, title, date_end, group_name)
│
├── 日期正規化
├── 若有 date_end → 展開成日期列表（逐日處理）
│
└── for each date:
    ├── goto_calendars()
    ├── ensure_monthly_view()
    ├── [若有 group_name] select_sidebar_calendar()
    ├── goto_target_month(date)
    ├── click_day_cell(day)
    ├── _collect_panel_events()  ← 取得面板上的事件列表
    │
    ├── title == None → 印出當天所有事件（列表模式）
    │
    └── title != None → 比對標題
        ├── 找不到 → 印出錯誤 + 當天現有事件
        └── 找到 → click event → _delete_one_event()
```

---

### 3.4 `test.py` — 除錯工具

**職責**：一次性 UI 探索腳本，用於逆向工程 TimeTree 的頁面結構。

#### 輸出檔案

| 檔案 | 內容 |
|------|------|
| `timetree_storage.json` | 瀏覽器 session（首次執行手動登入後儲存） |
| `body_text.txt` | 頁面全文純文字 |
| `interactive_elements.json` | 所有 button/input/textarea/a/role=button 元素 |
| `possible_event_elements.json` | 依關鍵字評分排序的可能事件元素（取前 200 筆） |
| `network_logs.json` | XHR/Fetch 請求與回應記錄 |
| `timetree_page.png` | 全頁截圖 |

#### 事件評分邏輯

```python
score = (
    (1 if re.match(r'event|schedule|title|date|time', text) else 0) +
    (1 if re.match(r'event|schedule|calendar', className) else 0) +
    (1 if el.getAttribute('data-testid') else 0)
)
# 最高 3 分，依 score 降序排列
```

---

## 4. 類別與方法總覽

```
TimeTreeAutomation
├── __init__(storage_file, headless)
├── __enter__()
├── __exit__(exc_type, exc, tb)
│
├── [導航]
│   ├── goto_calendars()
│   ├── ensure_monthly_view()
│   ├── get_visible_month_ym() → str | None
│   └── goto_target_month(target_date)
│
├── [日曆格操作]
│   ├── click_day_cell(day)
│   └── _get_day_cell(day) → Locator | None
│
├── [表單操作]
│   ├── open_create_event()
│   ├── fill_title_if_possible(title) → (bool, str|None)
│   ├── select_sidebar_calendar(group_name)
│   ├── open_color_select() → bool
│   ├── click_color_option(color_name) → bool
│   ├── ensure_color(color_name)
│   ├── _set_date_picker(test_id, date_str)
│   ├── set_start_date(date_str)
│   └── set_end_date(date_str)
│
├── [事件操作 - 公開]
│   ├── add_event(date_start, title, group_name, color_name, date_end)
│   └── delete_event(date_start, title, date_end, group_name)
│
├── [事件收集 - 私有]
│   ├── _collect_panel_events() → list[dict]
│   ├── _collect_titles_from_panel() → list[str]
│   ├── _extract_event_title(locator) → str
│   └── _delete_one_event()
│
└── [除錯工具]
    ├── dump_create_dialog_elements(out_file) → list
    ├── debug_color_select_state(tag)
    ├── dump_day_cell_elements(day, out_file) → list
    ├── _dump_all_clickable(out_file) → list
    ├── create_event_scaffold(target_date, title, group_name, color_name) → dict
    └── read_current_calendar_ids() → list
```

---

## 5. 變數與常數總覽

### 全域常數

| 檔案 | 常數 | 值 |
|------|------|-----|
| `timetree_automation.py` | `BASE_URL` | `"https://timetreeapp.com/calendars"` |
| `timetree_automation.py` | `STORAGE_FILE` | `"timetree_storage.json"` |
| `command_handler.py` | `DATE_FULL` | `r"^\d{4}-\d{2}-\d{2}$"` |
| `command_handler.py` | `DATE_SHORT` | `r"^\d{2}-\d{2}$"` |
| `command_handler.py` | `DEFAULT_GROUP` | `"私人"` |
| `command_handler.py` | `DEFAULT_COLOR` | `"Emerald green"` |
| `test.py` | `BODY_TEXT_FILE` | `"body_text.txt"` |
| `test.py` | `INTERACTIVE_FILE` | `"interactive_elements.json"` |
| `test.py` | `POSSIBLE_EVENTS_FILE` | `"possible_event_elements.json"` |
| `test.py` | `NETWORK_LOG_FILE` | `"network_logs.json"` |
| `test.py` | `SCREENSHOT_FILE` | `"timetree_page.png"` |

### 環境變數（來自 `.env`）

| 變數名 | 用途 |
|--------|------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot 發訊用的 Access Token |
| `LINE_CHANNEL_SECRET` | 驗證 Webhook 請求真實性的 Secret |

### TimeTree UI 中已知的 CSS Class（脆弱，可能改變）

| Class | 用途 |
|-------|------|
| `button._1hsbcq11` | 側邊欄群組切換按鈕 |
| `_72xel51` | 表示群組已被選中的 class |
| `span.lndlxo6` | 事件標題 span |

---

## 6. 資料流分析

### 新增事件完整資料流

```
LINE 使用者輸入：
  "add 開會 05-20 05-21 私人 Emerald green"
          │
          ▼
bot.py: event.message.text.strip()
  → "add 開會 05-20 05-21 私人 Emerald green"
          │
          ▼
command_handler._parse():
  parts = ["add", "開會", "05-20", "05-21", "私人", "Emerald", "green"]
  cmd   = "add"
  title = "開會"
  date_start = "2026-05-20"  ← _normalize_date("05-20")
  date_end   = "2026-05-21"  ← _normalize_date("05-21")
  group_name = "私人"
  color_name = "Emerald green"  ← " ".join(["Emerald", "green"])
          │
          ▼
  回傳 ("add", {title, date_start, date_end, group_name, color_name})
          │
          ▼
command_handler.handle():
  with TimeTreeAutomation(headless=True) as tt:
      buf = io.StringIO()
      with redirect_stdout(buf):
          tt.add_event(**kwargs)
  return buf.getvalue().strip()
          │
          ▼
TimeTreeAutomation.add_event():
  1. Chromium 啟動 (headless)
  2. 載入 timetree_storage.json
  3. 前往 timetreeapp.com/calendars
  4. 切換側邊欄到「私人」群組
  5. 切換到 2026年5月
  6. 點擊第 15 日格子
  7. 開啟新增表單
  8. 填入標題「開會」
  9. 設定開始日期 2026-05-20
  10. 設定結束日期 2026-05-21
  11. 選擇顏色 Emerald green
  12. 點擊儲存
  13. print("[add] 新增成功\n  事件：開會\n  日期：2026-05-20 ~ 2026-05-21...")
          │
          ▼
LINE 回覆：
  "[add] 新增成功
   事件：開會
   日期：2026-05-20 ~ 2026-05-21
   標籤：Emerald green
   群組：私人"
```

---

## 7. 設計模式與架構決策

### Context Manager 模式

`TimeTreeAutomation` 使用 `__enter__`/`__exit__` 確保 Playwright 資源必然釋放，避免殭屍 Chromium 行程。

### 多層 Selector Fallback 策略

TimeTree 使用 CSS Modules（動態 class 名）且版本更新頻繁，因此所有互動操作都實作多層 fallback：

```
最優先（語意穩定）：data-test-id > aria-label > role > :has-text()
最後手段（可能失效）：hardcoded CSS class
```

### stdout 重導向作為介面協議

`command_handler.py` 透過 `redirect_stdout` 攔截 `timetree_automation.py` 的 `print()` 輸出，作為 LINE 回覆內容。這使得自動化層不需要知道自己是被 LINE Bot 呼叫，保持模組解耦。

### 模組責任分層

```
bot.py          → 傳輸層（HTTP / LINE Protocol）
command_handler → 應用層（指令解析 / 業務邏輯）
timetree_auto   → 基礎設施層（瀏覽器操作）
```

---

## 8. 已知問題與技術債

### 硬編碼的脆弱點

| 位置 | 問題 | 風險 |
|------|------|------|
| `timetree_automation.py:308` | `button._1hsbcq11` 為動態 CSS class | TimeTree 版本更新後失效 |
| `timetree_automation.py:320` | `_72xel51` 判斷選中狀態 | 同上 |
| `timetree_automation.py:571` | `span.lndlxo6` 取事件標題 | 同上 |
| `timetree_automation.py:779` | `click_day_cell(15)` 固定點第 15 日 | 月份不足 15 日或佈局變化時可能出錯 |

### 除錯碼殘留於正式流程

`add_event()` 中有多個 `dump_create_dialog_elements()` 呼叫與 `print("[debug] ...")` 輸出，這些訊息會被 `redirect_stdout` 捕獲後一併傳給 LINE 使用者，造成訊息雜訊。

### 缺少重試機制

網路不穩定或 TimeTree 頁面加載緩慢時，沒有自動重試邏輯，直接拋出例外。

### 日期年份硬編碼為 2026

`_normalize_date()` 與 `delete_event()` 中短日期格式都補 `2026-` 前綴，跨年後需手動修改。

---

## 9. 系統依賴關係

### Python 套件依賴（`.venv`）

```
核心依賴：
├── playwright          → 瀏覽器自動化
├── flask               → Web 框架
├── line-bot-sdk (v3)   → LINE Messaging API
└── python-dotenv       → .env 檔案載入

開發/安裝：
└── playwright install chromium  ← 首次環境建立需執行
```

### 外部服務依賴

```
LINE Platform
├── Webhook URL 需公開可達（ngrok / 固定 IP）
└── Channel Access Token + Channel Secret

TimeTree
├── 需要有效的登入 session（timetree_storage.json）
└── 頁面結構異動會導致 selector 失效
```

### 執行環境依賴

```
Windows
└── free_port() 使用 netstat + taskkill（Windows 專用指令）
    → 移植到 Linux/Mac 需改寫此函式
```

---

*報告由 Claude Code 自動分析生成*
