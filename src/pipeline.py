"""Orchestrator: the full automatic rewrite cycle.

For each pending product the pipeline:
1. checks whether SEO meta tags need to be filled (only empty fields),
2. generates a new description via the LLM,
3. posts it through the Webasyst API (with a backup),
4. validates that the new-format markers appeared on the live page.

Progress is stored in ``data/state.json``, so a run can be safely restarted:
products with status=done are skipped and failed ones are retried.
"""
from __future__ import annotations

import json
import os
import sys
import time

try:
    from . import llm_client, poster, validator, webasyst_api as api
    from .config import PROJECT_DIR, DELAY_SECONDS, BATCH_SIZE, WEBASYST_TOKEN
except ImportError:
    import llm_client
    import poster
    import validator
    import webasyst_api as api
    from config import PROJECT_DIR, DELAY_SECONDS, BATCH_SIZE, WEBASYST_TOKEN

DATA_DIR = PROJECT_DIR / "data"
INVENTORY_PATH = DATA_DIR / "inventory.json"
STATE_PATH = DATA_DIR / "state.json"
LOCK_PATH = DATA_DIR / "pipeline.lock"


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def process_one(product: dict, state: dict) -> str:
    """Process a single product. Returns the new status ('done' or 'error')."""
    url = product["url"]
    product_id = product.get("product_id")

    # 1. Decide whether SEO meta tags are needed (only if empty in the admin).
    seo_required = False
    if WEBASYST_TOKEN and product_id:
        try:
            current = api.get_product(product_id)
            title_empty, desc_empty = poster.seo_is_empty(current)
            seo_required = title_empty or desc_empty
        except Exception as exc:  # noqa: BLE001
            print(f"    getInfo failed: {exc} — SEO is skipped")

    # 2. Generate the new content.
    generated = llm_client.generate(product, seo_required)

    # 3. Post it (with a backup of the previous state).
    result = poster.post(product, generated)
    print(f"    posted: {result['updated_fields']} "
          f"(SEO: {result['seo_written']})")

    # 4. Validate that the markers appeared on the live page.
    ok = validator.validate_url(url)
    status = "done" if ok else "error"
    if not ok:
        print(f"    WARNING: validation failed — check manually: {url}")

    state[url] = {
        "product_id": product_id,
        "status": status,
        "backup": result["backup"],
        "seo_written": result["seo_written"],
    }
    return status

def run(batch: int = 0) -> None:
    """Run the pipeline over pending products.

    Args:
        batch: Maximum number of products to process (0 = BATCH_SIZE from .env).
    """
    if LOCK_PATH.exists():
        raise SystemExit(
            "Another pipeline instance is already running (data/pipeline.lock). "
            "If that is not the case, delete the lock file manually."
        )
    if not INVENTORY_PATH.exists():
        raise SystemExit("No inventory.json — run the scanner first: python -m src.scanner")

    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(f"pid={os.getpid()}\nbatch={batch}\n", encoding="utf-8")
    try:
        items = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        state = load_state()

        todo = [
            it for it in items
            if it.get("needs_rewrite") and "error" not in it
            and state.get(it["url"], {}).get("status") != "done"
        ]
        if batch > 0:
            todo = todo[:batch]
        elif BATCH_SIZE:
            todo = todo[:BATCH_SIZE]

        print(f"To process: {len(todo)} products (batch={batch})", flush=True)
        for idx, product in enumerate(todo, 1):
            url = product["url"]
            print(f"\n[{idx}/{len(todo)}] {url}", flush=True)
            try:
                status = process_one(product, state)
                print(f"    status: {status}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"    ERROR: {exc}", flush=True)
                state[url] = {
                    "product_id": product.get("product_id"),
                    "status": "error",
                    "error": str(exc),
                }
            save_state(state)
            time.sleep(DELAY_SECONDS)

        done = sum(1 for v in state.values() if v.get("status") == "done")
        errors = sum(1 for v in state.values() if v.get("status") == "error")
        print(f"\nDone: done={done}, error={errors}", flush=True)
    finally:
        LOCK_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    batch = int(sys.argv[1]) if len(sys.argv) > 1 else BATCH_SIZE
    run(batch)
