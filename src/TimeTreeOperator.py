import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from function.command import run_command


class TimeTreeOperator:
    def run(self, cmd: dict) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_command(cmd)
        return buf.getvalue().strip()
