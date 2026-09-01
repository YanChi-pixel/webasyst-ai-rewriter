"""Configuration loader.

Reads settings from environment variables and an optional `.env` file located
in the project root. The project root is auto-detected (the parent of `src/`),
so the repository can be cloned anywhere.

Every value has a sensible default and can be overridden via `.env` or real
environment variables.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional

    def load_dotenv(*args, **kwargs) -> None:
        """No-op fallback when python-dotenv is not installed."""
        return None

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = Path(os.getenv("PROJECT_DIR", str(BASE_DIR)))

load_dotenv(PROJECT_DIR / ".env")


def get(name: str, default: str = "") -> str:
    """Read an environment variable and strip surrounding whitespace."""
    return os.getenv(name, default).strip()


# --- Webasyst / Shop-Script -------------------------------------------------
WEBASYST_BASE_URL = get("WEBASYST_BASE_URL").rstrip("/")
WEBASYST_TOKEN = get("WEBASYST_TOKEN")
WEBASYST_CLIENT_ID = get("WEBASYST_CLIENT_ID", "ai_rewriter")

# Path of the shop sitemap that lists product URLs.
SITEMAP_PATH = get("SITEMAP_PATH", "/sitemap-shop.xml")

# --- LLM (any OpenAI-compatible endpoint) ------------------------------------
LLM_API_BASE = (
    get("LLM_API_BASE")
    or get("DEEPSEEK_API_URL")
    or "https://api.deepseek.com"
).rstrip("/")
# Defensive: if a full /chat/completions URL was supplied, trim the suffix,
# because llm_client appends it itself.
LLM_API_BASE = LLM_API_BASE.removesuffix("/chat/completions")

LLM_API_KEY = get("LLM_API_KEY") or get("DEEPSEEK_API_KEY")
LLM_MODEL = get("LLM_MODEL") or get("DEEPSEEK_MODEL") or "deepseek-chat"

# --- Scanner / validator -----------------------------------------------------
# CSS classes that mark an already-rewritten ("new format") description.
# A product needs a rewrite when at least one of these markers is missing.
NEW_MARKERS = tuple(
    m for m in get("NEW_MARKERS", "faq-item,facts-wrapper").split(",") if m
)

# --- Pipeline tuning ---------------------------------------------------------
SCAN_LIMIT = int(get("SCAN_LIMIT", "0") or 0)      # 0 = scan the whole catalog
SCAN_WORKERS = int(get("SCAN_WORKERS", "8") or 8)
BATCH_SIZE = int(get("BATCH_SIZE", "50") or 50)
DELAY_SECONDS = float(get("DELAY_SECONDS", "2") or 2)
