"""Build the report of the last completed batch of processed URLs.

Usage:
    python -m src.make_report

The script figures out the number of the last complete batch (50 products,
first 3 are a pilot run), writes ``data/report_batchN.txt`` and prints the links.
"""
from __future__ import annotations

import json
import sys

try:
    from .config import PROJECT_DIR
except ImportError:
    from config import PROJECT_DIR

STATE_PATH = PROJECT_DIR / "data" / "state.json"
BATCH = 50
PILOT = 3  # the first 3 done entries are a pilot run, outside the batches

def main() -> None:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    done = [u for u, v in state.items() if v.get("status") == "done"]
    errors = [u for u, v in state.items() if v.get("status") == "error"]

    n = len(done)
    full_batches = (n - PILOT) // BATCH
    if full_batches < 1:
        print(f"No complete batch yet (done={n}, errors={len(errors)}).")
        sys.exit(0)

    start = PILOT + (full_batches - 1) * BATCH
    end = PILOT + full_batches * BATCH
    batch = done[start:end]

    out = PROJECT_DIR / "data" / f"report_batch{full_batches}.txt"
    out.write_text("\n".join(batch) + "\n", encoding="utf-8")

    print(f"Total done: {n} | errors: {len(errors)}")
    print(f"Batch {full_batches}: {len(batch)} links -> {out}")
    if n > end:
        print(f"NOTE: current batch {full_batches + 1} is partially done "
              f"({n - end} of 50) — its report appears after completion.")
    print()
    for u in batch:
        print(u)


if __name__ == "__main__":
    main()
