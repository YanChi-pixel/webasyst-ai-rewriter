"""Minimal REST client for Webasyst / Shop-Script.

Two non-obvious details that matter in production:

* The access token is sent in the query string, not in the
  ``Authorization: Bearer`` header. Some hostings (e.g. reg.ru) run a WAF that
  blocks the Bearer header and ``curl``'s default User-Agent; a browser-like
  User-Agent plus ``access_token`` in the query string is accepted.
* For ``shop.product.update`` the ``id`` parameter goes into the query string,
  while the fields being updated go into the POST body.
"""
from __future__ import annotations

import requests

try:  # allow both `python -m src...` and `python src/...`
    from .config import WEBASYST_BASE_URL, WEBASYST_TOKEN
except ImportError:
    from config import WEBASYST_BASE_URL, WEBASYST_TOKEN

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class WebasystError(Exception):
    """Raised when the Webasyst API returns an error or a non-JSON response."""


def _parse(response: requests.Response, method: str) -> dict:
    try:
        data = response.json()
    except ValueError as exc:
        raise WebasystError(
            f"Non-JSON response ({response.status_code}): {response.text[:200]}"
        ) from exc
    if "error" in data:
        raise WebasystError(
            f"API {method}: {data.get('error')} "
            f"{data.get('error_description', '')}"
        )
    return data

def call(method: str, params: dict | None = None, http: str = "POST",
         query: dict | None = None, timeout: int = 30) -> dict:
    """Call a Webasyst API method.

    Args:
        method: API method name, e.g. ``shop.product.getInfo``.
        params: Parameters for the POST body (or for the query string on GET).
        http: ``"GET"`` or ``"POST"``.
        query: Parameters that must go into the query string (e.g. ``id``).
        timeout: Request timeout in seconds.

    ``access_token`` is always added to the query string.
    """
    params = dict(params or {})
    query = dict(query or {})
    query.setdefault("access_token", WEBASYST_TOKEN)

    url = f"{WEBASYST_BASE_URL}/api.php/{method}"
    headers = {"User-Agent": BROWSER_UA}

    if http.upper() == "GET":
        query.update(params)
        response = requests.get(url, params=query, headers=headers, timeout=timeout)
    else:
        response = requests.post(
            url,
            params=query,
            data=params,
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
            timeout=timeout,
        )
    return _parse(response, method)


def get_product(product_id: int) -> dict:
    """Return product data (description, summary, meta_title, ...)."""
    return call("shop.product.getInfo", {"id": product_id}, http="GET")


def update_product(product_id: int, fields: dict) -> dict:
    """Update product fields.

    ``id`` goes into the query string; the fields to update go into the POST body.
    """
    return call("shop.product.update", fields, http="POST", query={"id": product_id})


def search_products(query_text: str) -> list:
    """Search products by name/article (useful for debugging)."""
    data = call("shop.product.search", {"query": query_text}, http="GET")
    return data.get("products", [])
