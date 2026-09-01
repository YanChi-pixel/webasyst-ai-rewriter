"""Posting generated content to Webasyst via API + backup of previous values."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

try:
    from . import webasyst_api as api
    from .config import PROJECT_DIR
except ImportError:
    import webasyst_api as api
    from config import PROJECT_DIR

BACKUP_DIR = PROJECT_DIR / "data" / "backups"


def backup(product_id: int | None, old_fields: dict) -> Path:
    """Save the current product fields as a rollback point."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"product_{product_id}_{ts}.json"
    path.write_text(
        json.dumps(old_fields, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def seo_is_empty(meta: dict) -> tuple[bool, bool]:
    """Return (title_empty, description_empty) flags."""
    title_empty = not (meta.get("meta_title") or "").strip()
    desc_empty = not (meta.get("meta_description") or "").strip()
    return title_empty, desc_empty

def post(product: dict, generated: dict) -> dict:
    """Write description/summary/SEO to a product and return an action summary."""
    product_id = product.get("product_id")
    if not product_id:
        raise ValueError("No product_id — cannot post")

    # Current data from the admin, used both as a backup and to decide SEO.
    current = api.get_product(product_id)

    fields = {
        "description": generated["description_html"],
        "summary": generated.get("summary_text", ""),
    }

    # SEO meta tags are written only into fields that are currently empty.
    title_empty, desc_empty = seo_is_empty(current)
    if title_empty and generated.get("meta_title"):
        fields["meta_title"] = generated["meta_title"]
    if desc_empty and generated.get("meta_description"):
        fields["meta_description"] = generated["meta_description"]

    backup_path = backup(product_id, current)
    api.update_product(product_id, fields)

    return {
        "product_id": product_id,
        "backup": str(backup_path),
        "updated_fields": list(fields.keys()),
        "seo_written": title_empty or desc_empty,
    }
