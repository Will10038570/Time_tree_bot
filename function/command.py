import yaml
from pathlib import Path
from playwright.sync_api import sync_playwright
from .operation_functions import log_in, goto_calendar, select_group
from .event_functions import add_event, delete_event, get_events_on_date

SESSION = Path("data/session.json")
_DEFAULTS_YML = Path(__file__).parent.parent / "configs" / "defaults.yml"

def _load_defaults() -> dict:
    if _DEFAULTS_YML.exists():
        with open(_DEFAULTS_YML, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def initial_page(p, group: str = None, headless: bool = False):
    browser = p.chromium.launch(headless=headless, args=["--start-maximized"])
    context = browser.new_context(
        no_viewport=True,
        storage_state=str(SESSION) if SESSION.exists() else None,
    )
    page = context.new_page()
    if SESSION.exists():
        goto_calendar(page)
    else:
        log_in(page)
    if not group:
        browser.close()
        raise ValueError("[command] group 為必填")
    select_group(page, group)
    return browser, context, page


def command_add(cmd: dict) -> None:
    d = _load_defaults()
    with sync_playwright() as p:
        browser, context, page = initial_page(p, group=cmd.get("group") or d.get("group"))
        add_event(
            page,
            title=cmd["title"],
            start=cmd["date_start"],
            end=cmd.get("date_end"),
            label=cmd.get("label") or d.get("label"),
        )
        context.storage_state(path=str(SESSION))
        browser.close()


def command_delete(cmd: dict) -> None:
    d = _load_defaults()
    with sync_playwright() as p:
        browser, context, page = initial_page(p, group=cmd.get("group") or d.get("group"))
        delete_event(page, title=cmd["title"], date_start=cmd["date_start"])
        context.storage_state(path=str(SESSION))
        browser.close()


def command_query(cmd: dict) -> None:
    d = _load_defaults()
    with sync_playwright() as p:
        browser, context, page = initial_page(p, group=cmd.get("group") or d.get("group"))
        events = get_events_on_date(page, cmd["date_start"])
        context.storage_state(path=str(SESSION))
        browser.close()
    if not events:
        print(f"{cmd['date_start']} 沒有行程")
        return
    print("\n".join(f"・{e}" for e in events))


def run_command(cmd: dict) -> None:
    command = cmd.get("command")
    try:
        if command == "add":
            command_add(cmd)
        elif command == "delete":
            command_delete(cmd)
        elif command == "query":
            command_query(cmd)
        else:
            print(f"[run_command] 未知指令：{command}")
    except ValueError as e:
        print(e)
        return
