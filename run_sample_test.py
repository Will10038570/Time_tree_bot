from pathlib import Path
from playwright.sync_api import sync_playwright
import locators

SESSION = Path(__file__).parent / "data" / "session.json"

STEPS = ["log_in", "select_group", "delete_event"]

GROUP = "aaaa"
EVENT_TITLE = "測試事件"
EVENT_START = "2026-01-36"
EVENT_END = None  # None 表示單天
DELETE_TITLE = "all"
DELETE_DATE = "2027-05-15"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True, storage_state=str(SESSION) if SESSION.exists() else None)
        page = context.new_page()

        for step in STEPS:
            if step == "log_in":
                if not SESSION.exists():
                    locators.log_in(page)
            elif step == "select_group":
                locators.goto_calendar(page)
                locators.select_group(page, GROUP)
            elif step == "add_event":
                locators.add_event(page, EVENT_TITLE, EVENT_START, EVENT_END)
            elif step == "check_event":
                events = locators.get_events_on_date(page, DELETE_DATE)
                print(f"[{DELETE_DATE}] events: {events}")
            elif step == "delete_event":
                locators.delete_event(page, DELETE_TITLE, DELETE_DATE)

        page.pause()
        context.storage_state(path=str(SESSION))
        browser.close()


if __name__ == "__main__":
    main()
