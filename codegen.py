import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(storage_state="data/session.json")
    page = context.new_page()
    page.goto("https://timetreeapp.com/calendars/8dCkPitSY4HR")
    page.get_by_role("gridcell", name="4").first.click()
    page.get_by_role("gridcell", name="5", exact=True).click()
    page.get_by_role("gridcell", name="6", exact=True).click()
    page.get_by_role("gridcell", name="3").nth(5).click()
    page.get_by_role("gridcell", name="4").nth(3).click()
    page.get_by_role("gridcell", name="4").nth(3).click()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
