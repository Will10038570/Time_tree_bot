import io
import re
from contextlib import redirect_stdout
from automation import TimeTreeAutomation

DATE_FULL = r"^\d{4}-\d{2}-\d{2}$"
DATE_SHORT = r"^\d{2}-\d{2}$"

DEFAULT_GROUP = "私人"
DEFAULT_COLOR = "Emerald green"


def _normalize_date(s: str) -> str:
    if re.match(DATE_SHORT, s):
        return f"2026-{s}"
    return s


def _is_date(s: str) -> bool:
    return bool(re.match(DATE_FULL, s)) or bool(re.match(DATE_SHORT, s))


def _parse(text: str) -> tuple[str, dict]:
    parts = text.strip().split()
    if not parts:
        raise ValueError(
            "指令不能為空\n"
            "add <名稱> <日期> [結束日期] [群組] [顏色]\n"
            "delete <日期>  或  delete <名稱> <日期>"
        )

    cmd = parts[0].lower()

    if cmd == "add":
        if len(parts) < 3 or not _is_date(parts[2]):
            raise ValueError(
                "add 格式：add <名稱> <日期> [結束日期] [群組] [顏色]\n"
                "範例：add 吃飯睡覺打電動 01-01\n"
                "　　　add 吃飯睡覺打電動 01-01 01-03 私人 Emerald green"
            )
        title = parts[1]
        date_start = _normalize_date(parts[2])
        date_end = None
        group = DEFAULT_GROUP
        color = DEFAULT_COLOR

        rest = parts[3:]
        idx = 0
        if rest and _is_date(rest[0]):
            date_end = _normalize_date(rest[0])
            idx = 1
        if idx < len(rest):
            group = rest[idx]
            idx += 1
        if idx < len(rest):
            color = " ".join(rest[idx:])

        return "add", {
            "title": title,
            "date_start": date_start,
            "date_end": date_end,
            "group_name": group,
            "color_name": color,
        }

    elif cmd == "delete":
        if len(parts) < 2:
            raise ValueError(
                "delete 格式：delete <日期>  或  delete <名稱> <日期>\n"
                "範例：delete 01-01\n"
                "　　　delete 吃飯睡覺打電動 01-01"
            )
        if len(parts) == 2 and _is_date(parts[1]):
            return "delete", {"date_start": _normalize_date(parts[1]), "title": None}
        if len(parts) >= 3 and _is_date(parts[-1]):
            return "delete", {
                "date_start": _normalize_date(parts[-1]),
                "title": " ".join(parts[1:-1]),
            }
        raise ValueError(
            "日期格式錯誤，請用 YYYY-MM-DD 或 MM-DD\n"
            "範例：delete 01-01  或  delete 吃飯睡覺打電動 01-01"
        )

    else:
        raise ValueError(
            f"未知指令：{cmd}\n"
            "支援：add、delete"
        )


def handle(text: str) -> str:
    try:
        cmd, kwargs = _parse(text)
    except ValueError as e:
        return str(e)

    try:
        with TimeTreeAutomation(headless=True) as tt:
            if cmd == "add":
                buf = io.StringIO()
                with redirect_stdout(buf):
                    tt.add_event(**kwargs)
                return buf.getvalue().strip()

            elif cmd == "delete":
                buf = io.StringIO()
                with redirect_stdout(buf):
                    tt.delete_event(**kwargs)
                return buf.getvalue().strip() or "✅ 刪除完成"

    except Exception as e:
        return f"❌ {e}"
