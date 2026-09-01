"""Catalog scanner: sitemap → inventory of products that need a rewrite.

For every product URL it downloads the page, detects whether the description
already uses the "new format" markers, and extracts the data needed by the
copywriter (title, features, old description, summary). The result is written
to ``data/inventory.json``.

A thread pool is used because scanning hundreds of pages sequentially is slow.
"""
from __future__ import annotations

import html as html_mod
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    from .config import (
        PROJECT_DIR, SCAN_LIMIT, SCAN_WORKERS, NEW_MARKERS,
        WEBASYST_BASE_URL, SITEMAP_PATH,
    )
except ImportError:
    from config import (
        PROJECT_DIR, SCAN_LIMIT, SCAN_WORKERS, NEW_MARKERS,
        WEBASYST_BASE_URL, SITEMAP_PATH,
    )

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Shop URLs that are not product cards and should be skipped.
NON_PRODUCT_PREFIXES = (
    "/pokupatelyam/", "/o-kompanii/", "/kontakty/", "/sotrudnichestvo/",
    "/blog/", "/search/", "/compare/", "/cart/", "/checkout/", "/order/",
    "/login/", "/signup/", "/forgotpassword/",
)

DATA_DIR = PROJECT_DIR / "data"
INVENTORY_PATH = DATA_DIR / "inventory.json"


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def get_sitemap_urls() -> list[str]:
    """Return product URLs from the shop sitemap (``SITEMAP_PATH``)."""
    if not WEBASYST_BASE_URL:
        raise RuntimeError("WEBASYST_BASE_URL is not set — check your .env")

    xml = fetch(f"{WEBASYST_BASE_URL}{SITEMAP_PATH}")
    root = ET.fromstring(xml)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    out: list[str] = []
    for loc in root.findall(".//s:loc", ns):
        url = (loc.text or "").strip()
        if not url.startswith(WEBASYST_BASE_URL):
            continue
        if url.rstrip("/") == WEBASYST_BASE_URL:
            continue
        if "/category/" in url or url.endswith(".xml"):
            continue
        if any(url.startswith(WEBASYST_BASE_URL + p) for p in NON_PRODUCT_PREFIXES):
            continue
        if url not in out:
            out.append(url)
    return out

def extract_product_id(page_html: str) -> int | None:
    match = re.search(r'data-product="(\d+)"', page_html)
    return int(match.group(1)) if match else None


def needs_rewrite(page_html: str) -> bool:
    """Return True when the description block lacks the new-format markers."""
    i = page_html.find('id="product-description"')
    if i < 0:
        return True
    block = page_html[i:i + 60000]
    return not any(marker in block for marker in NEW_MARKERS)


def extract_title(page_html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", page_html, re.S)
    return html_mod.unescape(match.group(1)).strip() if match else ""


def extract_features(page_html: str) -> dict[str, str]:
    """Extract the full features table from the #product-options block."""
    i = page_html.find('id="product-options"')
    if i < 0:
        i = page_html.find("product_features")
    block = page_html[i:i + 40000] if i >= 0 else ""
    feats: dict[str, str] = {}
    for match in re.finditer(
        r'<tr class="product_features-item[^"]*">\s*<td class="product_features-title">'
        r'<span>(.*?)</span></td>\s*<td class="product_features-value">(.*?)</td>',
        block, re.S,
    ):
        key = clean(match.group(1))
        val = clean(match.group(2))
        if key and key not in feats:
            feats[key] = val
    return feats

def extract_old_description(page_html: str) -> str:
    """Extract the content of ``<div itemprop='description'>``."""
    i = page_html.find('id="product-description"')
    if i < 0:
        return ""
    block = page_html[i:i + 60000]
    match = re.search(r'<div itemprop="description">(.*?)</div></div></div>', block, re.S)
    return match.group(1).strip() if match else ""


def extract_summary(page_html: str) -> str:
    match = re.search(r'<div class="product-card__summary">(.*?)</div>', page_html, re.S)
    return clean(match.group(1)) if match else ""


def clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html_mod.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _process_one(idx: int, total: int, url: str) -> tuple[int, str, str, dict]:
    """Process a single URL. Return (idx, flag, url, item)."""
    try:
        page = fetch(url)
    except Exception as exc:  # noqa: BLE001
        return idx, "ERR", url, {"url": url, "error": str(exc)}

    item = {
        "url": url,
        "product_id": extract_product_id(page),
        "title": extract_title(page),
        "needs_rewrite": needs_rewrite(page),
        "features": extract_features(page),
        "old_description": extract_old_description(page),
        "summary": extract_summary(page),
    }
    flag = "REWRITE" if item["needs_rewrite"] else "ok"
    return idx, flag, url, item

def scan(limit: int | None = None, workers: int | None = None) -> list[dict]:
    """Scan the catalog and write ``data/inventory.json``. Returns the items."""
    urls = get_sitemap_urls()
    if limit:
        urls = urls[:limit]
    total = len(urls)
    workers = workers or SCAN_WORKERS

    results: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_process_one, i, total, u): i for i, u in enumerate(urls, 1)}
        for fut in as_completed(futures):
            idx, flag, url, item = fut.result()
            print(f"[{idx}/{total}] {flag} {url}", flush=True)
            results[idx] = item

    items = [results[i] for i in sorted(results)]

    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    rewrite = sum(1 for it in items if it.get("needs_rewrite"))
    errors = sum(1 for it in items if "error" in it)
    print(f"\nSaved: {INVENTORY_PATH}")
    print(f"Products: {len(items)} | to rewrite: {rewrite} | errors: {errors}")
    return items


if __name__ == "__main__":
    scan(SCAN_LIMIT or None)
