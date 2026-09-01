"""Generate a report: URLs of successfully processed products (status=done).

Usage:
    python -m src.report        # all done
    python -m src.report 50     # first 50 done
"""
from __future__ import annotations

import json
import sys

try:
    from .config import PROJECT_DIR
except ImportError:
    from config import PROJECT_DIR

STATE_PATH = PROJECT_DIR / "data" / "state.json"
OUT_PATH = PROJECT_DIR / "data" / "report_links.txt"


def main(limit: int = 0) -> None:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    done = [url for url, v in state.items() if v.get("status") == "done"]
    errors = [url for url, v in state.items() if v.get("status") == "error"]

    if limit > 0:
        done = done[:limit]

    OUT_PATH.write_text("\n".join(done) + ("\n" if done else ""), encoding="utf-8")
    print(f"done: {len(done)} | error: {len(errors)}")
    print(f"Links file: {OUT_PATH}")


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(lim)
