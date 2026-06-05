import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(storage_state="data/session.json")
    page = context.new_page()
    page.goto("https://timetreeapp.com/calendars/LLvw7s1RGRjM")
    page.locator("[data-test-id=\"calendar-bar-event-add-button\"]").click()
    page.locator("[data-test-id=\"start-date-picker\"]").click()
    page.get_by_role("button", name="9", exact=True).click()
    page.locator("[data-test-id=\"end-date-picker\"]").click()
    page.get_by_role("button", name="12").click()
    page.get_by_role("textbox", name="Title").click()
    page.get_by_role("textbox", name="Title").fill("testtest")
    page.locator("[data-test-id=\"event-form-submit-button\"]").click()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
