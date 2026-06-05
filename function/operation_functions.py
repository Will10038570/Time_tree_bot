import os
from datetime import date as Date
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import Page

load_dotenv(Path(__file__).parent.parent / ".env")


def log_in(page: Page) -> None:
    page.goto("https://timetreeapp.com/intl/en")
    page.get_by_role("link", name="Login").click()
    page.locator('[data-test-id="signin-form-email"]').fill(os.environ["TIMETREE_EMAIL"])
    page.locator('[data-test-id="signin-form-email"]').press("Tab")
    page.locator('[data-test-id="signin-form-password"]').fill(os.environ["TIMETREE_PASSWORD"])
    page.locator('[data-test-id="signin-form-password"]').press("Enter")
    page.wait_for_url("**/calendars", timeout=15000)


def goto_calendar(page: Page) -> None:
    page.goto("https://timetreeapp.com/calendars", wait_until="networkidle")


def get_all_groups(page: Page) -> list[dict]:
    items = page.locator('[data-test-id="compact-calendar-list-item"]').all()
    groups = []
    for item in items:
        name = item.locator('[role="img"]').get_attribute("aria-label")
        selected = item.locator("._72xel51").count() > 0
        groups.append({"name": name, "selected": selected})
    return groups


def is_group_selected(page: Page, group_name: str) -> bool:
    return page.get_by_role("button", name=group_name).locator("._72xel51").count() > 0


def select_group(page: Page, group_name: str) -> None:
    groups = get_all_groups(page)
    valid_names = [g["name"] for g in groups]
    if group_name not in valid_names:
        raise ValueError(f"群組 '{group_name}' 不存在，目前可用群組：{valid_names}")
    for g in groups:
        if g["selected"]:
            page.get_by_role("button", name=g["name"]).click()
    page.get_by_role("button", name=group_name).click()


def _fmt_date(iso: str) -> str:
    # TimeTree date picker 接受的格式：「Wed, Jun 25, 2025」
    return Date.fromisoformat(iso).strftime("%a, %b %#d, %Y")


def _is_picker_invalid(page: Page, test_id: str) -> bool:
    return page.locator(f'[data-test-id="{test_id}"]').get_attribute("aria-invalid") == "true"


_UI_BUTTONS = {"Today", "Next month", "Previous month", "Monthly", "Weekly",
               "Create an event", "Menu", "Delete", "Cancel", "OK"}


def _navigate_month(page: Page, delta: int) -> None:
    if delta == 0:
        return
    btn_name = "Next month" if delta > 0 else "Previous month"
    for _ in range(abs(delta)):
        page.get_by_role("button", name=btn_name).click()


def _month_delta(date: str) -> int:
    target = Date.fromisoformat(date)
    today = Date.today()
    return (target.year - today.year) * 12 + (target.month - today.month)


def _goto_target_month(page: Page, date: str) -> None:
    goto_calendar(page)
    page.get_by_role("button", name="Today").click()
    page.wait_for_timeout(500)
    _navigate_month(page, _month_delta(date))


def _cell_day(cell) -> str:
    d = cell.locator("div > div").first
    return d.inner_text().strip() if d.count() else ""


def _find_month_cell(page: Page, day: int):
    """兩個 '1' 之間為當月範圍，找到指定日的 gridcell。"""
    cells = page.get_by_role("gridcell").all()
    ones = [i for i, c in enumerate(cells) if _cell_day(c) == "1"]
    if not ones:
        return None
    start = ones[0]
    end = ones[1] if len(ones) > 1 else len(cells)
    target = str(day)
    for cell in cells[start:end]:
        if _cell_day(cell) == target:
            return cell
    return None


def _events_in_cell(page: Page, cell) -> list:
    """用 bounding box 找出視覺上在 cell 範圍內的事件按鈕（排除 UI 按鈕）。"""
    cb = cell.bounding_box()
    if not cb:
        return []
    result = []
    for btn in page.get_by_role("button").all():
        name = (btn.get_attribute("aria-label") or btn.inner_text()).strip()
        if not name or name in _UI_BUTTONS:
            continue
        bb = btn.bounding_box()
        if not bb:
            continue
        cx = bb["x"]
        cy = bb["y"] + bb["height"] / 2
        if cb["x"] <= cx <= cb["x"] + cb["width"] and cb["y"] <= cy <= cb["y"] + cb["height"]:
            result.append(btn)
    return result
