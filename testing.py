import random
import calendar
from datetime import date as Date, timedelta
from function.command import run_command

random.seed(42)

LABELS = [
    "Apple red" , "Deep sky blue", "Emerald green",
]

SAMPLE_CMD = {
    "command": "delete",       # "add" | "delete"
    "title": "testtest334s",
    "date_start": "2026-06-09",
    "date_end": "2026-07-28",
    "group":  "aaaa",
    "label": "Apple red",
}




if __name__ == "__main__":
    run_command(SAMPLE_CMD)