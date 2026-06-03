from datetime import date as Date
from playwright.sync_api import Page
from .operation_functions import (
    _fmt_date, _is_picker_invalid,
    _goto_target_month, _find_month_cell, _events_in_cell, _UI_BUTTONS,
)


def _select_date(page: Page, start: str, end: str = None, timeout: int = 5000) -> None:
    end = end or start

    page.locator('[data-test-id="start-date-picker"]').click(timeout=timeout)
    page.locator('[data-test-id="start-date-picker"]').press("Control+a")
    page.locator('[data-test-id="start-date-picker"]').fill(_fmt_date(start), timeout=timeout)
    page.locator('[data-test-id="start-date-picker"]').press("Tab")
    if _is_picker_invalid(page, "start-date-picker"):
        raise ValueError(f"無效的開始日期：{start}")

    page.locator('[data-test-id="end-date-picker"]').click(timeout=timeout)
    page.locator('[data-test-id="end-date-picker"]').press("Control+a")
    page.locator('[data-test-id="end-date-picker"]').fill(_fmt_date(end), timeout=timeout)
    page.locator('[data-test-id="end-date-picker"]').press("Enter")
    if _is_picker_invalid(page, "end-date-picker"):
        raise ValueError(f"無效的結束日期：{end}")


def add_event(page: Page, title: str, start: str, end: str = None) -> None:
    T = 300

    def _step(name, fn):
        try:
            fn()
            return True
        except Exception as e:
            print(f"[{name}] timeout: {title} {start} — {type(e).__name__}")
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

    if not _step("open", lambda: page.locator('[data-test-id="calendar-bar-event-add-button"]').click(timeout=T)):
        return
    page.wait_for_timeout(500)

    try:
        _select_date(page, start, end, timeout=1000)
    except ValueError as e:
        print(f"[invalid date] {e}")
        _cancel()
        return
    except Exception as e:
        print(f"[select_date] timeout: {title} {start} — {type(e).__name__}")
        _cancel()
        return

    if not _step("title", lambda: page.get_by_role("textbox", name="Event title (required)").fill(title, timeout=T)):
        _cancel()
        return
    if not _step("label", lambda: page.locator('[data-test-id="label-select"]').click(timeout=T)):
        _cancel()
        return
    if not _step("color", lambda: page.locator('[data-test-id="Deep sky blue"]').click(timeout=T)):
        _cancel()
        return
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


def _delete_one_on_date(page: Page, date: str) -> bool:
    """在目標日 cell 內找第一個可刪除的事件並刪除，成功回傳 True。"""
    T = 1000
    d = Date.fromisoformat(date)
    _goto_target_month(page, date)
    cell = _find_month_cell(page, d.day)
    if cell is None:
        print(f"[delete] cell not found: {date}")
        return False
    btns = _events_in_cell(page, cell)
    if not btns:
        print(f"[delete] no events: {date}")
        return False
    for btn in btns:
        name = (btn.get_attribute("aria-label") or btn.inner_text()).strip()
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
        print(f"[delete] '{name}' {date}")
        return True
    return False


def delete_single_event(page: Page, title: str, date: str) -> bool:
    """導到目標月，在目標日 cell 內找 title 並刪除，成功回傳 True。"""
    try:
        d = Date.fromisoformat(date)
    except ValueError:
        print(f"[delete] invalid date: {date}")
        return False
    T = 1000
    _goto_target_month(page, date)
    cell = _find_month_cell(page, d.day)
    if cell is None:
        print(f"[delete] cell not found: {date}")
        return False
    btns = _events_in_cell(page, cell)
    if not btns:
        print(f"[delete] no events: {date}")
        return False
    for btn in btns:
        name = (btn.get_attribute("aria-label") or btn.inner_text()).strip()
        if name != title:
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
        print(f"[delete] '{name}' {date}")
        return True
    return False


def delete_event(page: Page, title: str, date: str) -> None:
    if title == "all":
        while _delete_one_on_date(page, date):
            pass
    else:
        if not delete_single_event(page, title, date):
            print(f"找不到事件：{title} {date}")
