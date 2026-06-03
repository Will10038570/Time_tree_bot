import random
import calendar
from pathlib import Path
from playwright.sync_api import sync_playwright
import locators

SESSION = Path("data/session.json")

random.seed(42)


def _generate_test_events(n: int = 20) -> list[dict]:
    events = []
    base_year, base_month = 2026, 7  # spread across 2026-07 ~ 2027-06
    for i in range(n):
        month_offset = random.randint(0, 11)
        year = base_year + (base_month - 1 + month_offset) // 12
        month = (base_month - 1 + month_offset) % 12 + 1

        day_type = random.choice(["start", "end", "mid"])
        if day_type == "start":
            day = 1
        elif day_type == "end":
            day = calendar.monthrange(year, month)[1]
        else:
            day = 15

        events.append({
            "title": f"test_{i + 1}",
            "date": f"{year}-{month:02d}-{day:02d}",
        })
    return events


TEST_EVENTS = _generate_test_events()


def add_test() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True, storage_state=str(SESSION) if SESSION.exists() else None)
        page = context.new_page()
        locators.goto_calendar(page)
        for event in TEST_EVENTS:
            locators.add_event(page, event["title"], event["date"])
            page.wait_for_timeout(500)
        context.storage_state(path=str(SESSION))
        browser.close()


def delete_test() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True, storage_state=str(SESSION) if SESSION.exists() else None)
        page = context.new_page()
        for event in TEST_EVENTS:
            locators.delete_event(page, event["title"], event["date"])
        context.storage_state(path=str(SESSION))
        browser.close()


if __name__ == "__main__":
    add_test()
    delete_test()
