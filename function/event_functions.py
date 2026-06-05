import time
from datetime import date as Date
from playwright.sync_api import Page
from .operation_functions import (
    _fmt_date, _is_picker_invalid,
    _goto_target_month, _find_month_cell, _events_in_cell, _UI_BUTTONS,
)


def _select_date(page: Page, start: str, end: str, timeout: int = 5000) -> None:
    page.locator('[data-test-id="start-date-picker"]').fill(_fmt_date(start), timeout=timeout)
    page.locator('[data-test-id="start-date-picker"]').press("Enter")
    time.sleep(0.5)
    if _is_picker_invalid(page, "start-date-picker"):
        raise ValueError(f"無效的開始日期：{start}")

    page.locator('[data-test-id="end-date-picker"]').fill(_fmt_date(end), timeout=timeout)
    page.locator('[data-test-id="end-date-picker"]').press("Enter")
    time.sleep(0.5)
    if _is_picker_invalid(page, "end-date-picker"):
        raise ValueError(f"無效的結束日期：{end}")


def add_event(page: Page, title: str, start: str, end: str, label: str) -> None:
    if not title or not start or not end or not label:
        print(f"[add_event] 缺少必要參數 title={title!r} start={start!r} end={end!r} label={label!r}")
        return
    T = 100

    def _step(name, fn):
        print(f"[{name}] start")
        try:
            fn()
            print(f"[{name}] ok")
            return True
        except Exception as e:
            print(f"[{name}] FAIL — {type(e).__name__}: {e}")
            return False

    def _cancel():
        try:
            page.get_by_role("button", name="Cancel").click(timeout=1000)
            page.get_by_role("button", name="OK").click(timeout=1000)
        except Exception:
            pass

    try:
        Date.fromisoformat(start)
    except ValueError as e:
        print(f"[invalid date] {e}")
        return

    if not _step("open", lambda: page.locator('[data-test-id="calendar-bar-event-add-button"]').click(timeout=10000)):
        return
    time.sleep(0.5)

    print("[select_date] start")
    try:
        _select_date(page, start, end, timeout=1000)
        print("[select_date] ok")
    except ValueError as e:
        print(f"[select_date] FAIL invalid date — {e}")
        _cancel()
        return
    except Exception as e:
        print(f"[select_date] FAIL — {type(e).__name__}: {e}")
        _cancel()
        return
    time.sleep(0.5)

    if not _step("title", lambda: (page.get_by_placeholder("Title").click(timeout=T), page.get_by_placeholder("Title").press("Control+a"), page.get_by_placeholder("Title").press_sequentially(title), page.get_by_placeholder("Title").press("Tab"))):
        _cancel()
        return
    time.sleep(0.5)

    if not _step("label", lambda: page.locator('[data-test-id="label-select"]').click(timeout=T)):
        _cancel()
        return
    time.sleep(0.5)

    if not _step("color", lambda label=label: page.locator(f'[data-test-id="{label}"]').click(timeout=T)):
        _cancel()
        return
    time.sleep(0.5)

    if not _step("save", lambda: page.locator('[data-test-id="event-form-submit-button"]').click(timeout=T)):
        _cancel()
        return


def get_events_on_date(page: Page, date: str) -> list[str]:
    """導到目標月，回傳指定日期 cell 內所有事件名稱。"""
    d = Date.fromisoformat(date)
    _goto_target_month(page, date)
    cell = _find_month_cell(page, d.day)
    if cell is None:
        return []
    return [(btn.get_attribute("aria-label") or btn.inner_text()).strip()
            for btn in _events_in_cell(page, cell)]


def delete_event(page: Page, title: str, date_start: str) -> bool:
    try:
        d = Date.fromisoformat(date_start)
    except ValueError:
        print(f"[delete] invalid date: {date_start}")
        return False

    T = 1000
    delete_all = (title == "all")

    while True:
        _goto_target_month(page, date_start)
        cell = _find_month_cell(page, d.day)
        if cell is None:
            print(f"[delete] cell not found: {date_start}")
            return False

        btns = _events_in_cell(page, cell)
        if not btns:
            if not delete_all:
                print(f"[delete] no events: {date_start}")
                return False
            return True

        deleted_one = False
        for btn in btns:
            name = (btn.get_attribute("aria-label") or btn.inner_text()).strip()
            if not delete_all and name != title:
                continue
            try:
                btn.click(timeout=T)
                page.get_by_role("button", name="Menu").click(timeout=T)
            except Exception as e:
                print(f"[delete] '{name}' open/menu — {type(e).__name__}, skip")
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
                continue
            try:
                page.get_by_role("button", name="Delete").click(timeout=T)
                page.get_by_role("button", name="Delete").click(timeout=T)
            except Exception as e:
                print(f"[delete] confirm delete — {type(e).__name__}")
                return False
            print(f"[delete] '{name}' {date_start}")
            deleted_one = True
            break

        if not deleted_one:
            if not delete_all:
                print(f"找不到事件：{title} {date_start}")
            return False

        if not delete_all:
            return True
