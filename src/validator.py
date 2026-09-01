"""Validation: check that the new-format markers appeared after posting."""
from __future__ import annotations

import time
import urllib.request

try:
    from .config import NEW_MARKERS
except ImportError:
    from config import NEW_MARKERS

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def validate_url(url: str, retries: int = 3, wait: int = 10) -> bool:
    """Download a page and verify the markers.

    A cache may still serve the old version, so we retry with a pause.
    """
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                page = resp.read().decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001
            print(f"    validation attempt {attempt}: error {exc}")
            time.sleep(wait)
            continue

        i = page.find('id="product-description"')
        if i >= 0:
            block = page[i:i + 60000]
            if all(marker in block for marker in NEW_MARKERS):
                return True
        print(f"    validation attempt {attempt}: markers not present yet")
        time.sleep(wait)
    return False
