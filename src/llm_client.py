"""OpenAI-compatible LLM client + request assembly from the copywriter prompt."""
from __future__ import annotations

import json
import re
import time

import requests

try:
    from .config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL, PROJECT_DIR
except ImportError:
    from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL, PROJECT_DIR

PROMPT_PATH = PROJECT_DIR / "prompts" / "product_prompt.md"


class LLMError(Exception):
    """Raised when the LLM endpoint fails or returns an unexpected payload."""


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def chat(messages: list[dict], temperature: float = 0.4, max_tokens: int = 4000,
         retries: int = 3) -> str:
    """One chat-completions call with retries on 429 / 5xx / network errors."""
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(
                f"{LLM_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=120,
            )
            if r.status_code == 429 or r.status_code >= 500:
                raise LLMError(f"HTTP {r.status_code}: {r.text[:200]}")
            r.raise_for_status()
            data = r.json()
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as exc:
                raise LLMError(
                    f"Unexpected LLM response: "
                    f"{json.dumps(data, ensure_ascii=False)[:300]}"
                ) from exc
        except Exception as exc:  # noqa: BLE001 - retried below
            last_err = exc
            if attempt < retries:
                time.sleep(3 * attempt)
    raise LLMError(f"LLM unavailable after {retries} attempts: {last_err}")

def build_messages(item: dict, seo_required: bool) -> list[dict]:
    """Assemble system + user messages for one product card."""
    system = load_prompt()

    product_json = json.dumps(
        {
            "название": item.get("title", ""),
            "характеристики": item.get("features", {}),
            "старое_описание": item.get("old_description", "")[:4000],
            "старое_краткое": item.get("summary", "")[:1000],
        },
        ensure_ascii=False,
        indent=2,
    )

    user = (
        f"Товар для обработки:\n{product_json}\n\n"
        f"seo_required: {str(seo_required).lower()}\n\n"
        "Сгенерируй описание строго по шаблону и верни ТОЛЬКО JSON."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_json_response(text: str) -> dict:
    """Extract a JSON object from the model's reply (handles markdown fences)."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise LLMError(f"No JSON found in response: {text[:300]}")
    return json.loads(text[start:end + 1])


def generate(item: dict, seo_required: bool) -> dict:
    """Full generation cycle: build messages -> call LLM -> parse JSON."""
    messages = build_messages(item, seo_required)
    raw = chat(messages)
    return parse_json_response(raw)
