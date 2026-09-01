# webasyst-ai-rewriter

Batch AI rewriting of **Webasyst / Shop-Script** product cards using any
OpenAI-compatible LLM (DeepSeek, OpenAI, OpenRouter, local Ollama…).

The tool scans your catalog, detects which product descriptions are still in
the old format, rewrites each one through an LLM following a strict template,
posts the result back through the Webasyst REST API, and validates the change
on the live page — automatically, in controllable batches, with full rollback.

> Русская версия: [README.ru.md](README.ru.md)

---

## What problem it solves

Manually rewriting hundreds of product cards is weeks of monotonous work.
This project turns it into a supervised pipeline:

```
sitemap → scanner → inventory → LLM copywriter → poster → validator
                                   ↑                              │
                                   └──────── state + backups ─────┘
```

It was built for a real catalog of **728 products** and processed the whole
catalog in batches of 50 with zero data loss: every update is backed up before
it is written, and every card is re-checked on the live site before it is
marked as `done`.

## Features

- **Catalog scanner** — walks the shop sitemap, downloads product pages and
  extracts title, features, old description and summary (multithreaded).
- **Deterministic rewrite detection** — a product needs a rewrite when its
  description lacks configurable CSS markers (e.g. `faq-item`, `facts-wrapper`).
- **LLM copywriter** — strict prompt with a few-shot example; the model returns
  JSON (`description_html`, `summary_text`, and optional SEO meta tags).
- **SEO-safe posting** — `meta_title` / `meta_description` are written only
  into fields that are currently empty; existing SEO is never overwritten.
- **Rollback** — the previous state of every product is saved to
  `data/backups/` before each update.
- **Validation** — after posting, the live page is re-fetched to confirm the
  new-format markers actually appeared (with retries for cache).
- **Resumable runs** — progress lives in `data/state.json`; a re-run skips
  `done` products and retries `error` ones.
- **WAF-friendly API client** — sends `access_token` in the query string with
  a browser User-Agent, which works on hostings that block the
  `Authorization: Bearer` header (e.g. reg.ru).
- **Provider-agnostic LLM** — any OpenAI-compatible endpoint, including local
  Ollama models.

## How it works

| Stage | Module | Description |
| --- | --- | --- |
| 1. Scan | `src/scanner.py` | Sitemap → `data/inventory.json` with `needs_rewrite` flags |
| 2. Generate | `src/llm_client.py` + `prompts/product_prompt.md` | LLM returns structured JSON with new HTML |
| 3. Post | `src/poster.py` | Backs up current state, then calls `shop.product.update` |
| 4. Validate | `src/validator.py` | Re-fetches the page and checks the markers |
| 5. Orchestrate | `src/pipeline.py` | Runs the cycle in batches and persists statuses |
| 6. Report | `src/report.py`, `src/make_report.py` | Exports lists of processed URLs |

Product statuses: `pending → generated → posted → done` (or `error`).

## Requirements

- Python 3.10+
- A Webasyst / Shop-Script site with REST API access (`api.php`)
- An OpenAI-compatible LLM endpoint + API key

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/YanChi-pixel/webasyst-ai-rewriter.git
cd webasyst-ai-rewriter
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

# 2. Configure
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
# …then edit .env and fill in your values

# 3. Scan the catalog
python -m src.scanner

# 4. Run a batch of 50 products
python -m src.pipeline 50

# 5. Build a report of processed URLs
python -m src.make_report
```

Each script can also be run directly from the `src/` directory
(e.g. `python src/pipeline.py 50`) — the modules support both launch modes.

## Getting a Webasyst API token

Webasyst uses OAuth 2.0. The easiest way to get a token is the **client flow**:
the token lands in the browser address bar.

1. Log into the shop admin (`https://your-shop.example.com/webasyst`) as a
   user with product permissions.
2. In the same browser open:

   ```
   https://your-shop.example.com/api.php/auth?client_id=ai_rewriter&client_name=Rewriter&response_type=token&scope=shop&redirect_uri=https%3A%2F%2Fyour-shop.example.com%2F&format=json
   ```

3. Approve access.
4. The browser redirects to
   `https://your-shop.example.com/#access_token=TOKEN` — copy the value of
   `access_token` (up to the first `&`).
5. Paste it into `.env` as `WEBASYST_TOKEN`.

Verify the token:

```
GET https://your-shop.example.com/api.php/shop.product.getInfo?id=1&access_token=TOKEN
```

An `invalid_token` error means the token is wrong; product data means it works.

> **Why the token is in the query string?** Some hostings run a WAF that
> blocks the `Authorization: Bearer` header (and `curl`'s User-Agent). Sending
> `access_token` in the query string with a browser User-Agent is the form
> that passes the filter. This is already handled inside `src/webasyst_api.py`.

## Configuration

All settings live in `.env` (see `.env.example`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `WEBASYST_BASE_URL` | — | Shop base URL, no trailing slash |
| `WEBASYST_TOKEN` | — | OAuth access token |
| `WEBASYST_CLIENT_ID` | `ai_rewriter` | Client id used in the authorize URL |
| `SITEMAP_PATH` | `/sitemap-shop.xml` | Path of the sitemap with product URLs |
| `NEW_MARKERS` | `faq-item,facts-wrapper` | CSS classes that mark a rewritten card |
| `LLM_API_BASE` | `https://api.deepseek.com` | OpenAI-compatible endpoint |
| `LLM_API_KEY` | — | API key (also reads `DEEPSEEK_API_KEY`) |
| `LLM_MODEL` | `deepseek-chat` | Model name (also reads `DEEPSEEK_MODEL`) |
| `SCAN_LIMIT` | `0` | Max products to scan (`0` = all) |
| `SCAN_WORKERS` | `8` | Parallel page downloads during scan |
| `BATCH_SIZE` | `50` | Default products per pipeline run |
| `DELAY_SECONDS` | `2` | Pause between products |

The config is defensive: it also accepts the legacy `DEEPSEEK_*` variable names
and strips an accidental `/chat/completions` suffix from the base URL.

## Usage

### Scan the catalog

```bash
python -m src.scanner
```

Produces `data/inventory.json`. Each item contains `url`, `product_id`,
`title`, `needs_rewrite`, `features`, `old_description`, `summary`. Products
with `needs_rewrite: true` are the ones the pipeline will process.

### Run the rewrite pipeline

```bash
python -m src.pipeline 50   # process up to 50 pending products
python -m src.pipeline      # process BATCH_SIZE products from .env
```

A lock file (`data/pipeline.lock`) prevents two concurrent runs. Progress is
written to `data/state.json` after every product, so interrupting the process
loses nothing — the next run continues where it stopped.

### Reports

```bash
python -m src.report          # all done URLs → data/report_links.txt
python -m src.make_report     # last complete batch → data/report_batchN.txt
```

### Rollback

Before every update the current product state is saved to
`data/backups/product_<id>_<timestamp>.json`. To roll a product back, take the
old `description` / `summary` / SEO fields from that JSON and write them back
through `shop.product.update` (see `src/webasyst_api.py`).

## Customizing for your shop

- **Rewrite markers** — set `NEW_MARKERS` in `.env` to the CSS classes that
  identify your "new format" description. If at least one marker is missing,
  the product is treated as needing a rewrite.
- **Copywriter prompt** — edit `prompts/product_prompt.md` (niche-neutral by
  default). For a stronger few-shot anchor, copy one of the ready-made niche
  prompts from `prompts/examples/` (textiles, electronics, furniture) into
  `product_prompt.md`.
- **Theme selectors** — the scanner's HTML extraction assumes the Shop-Script
  `mastershop` theme (`#product-description`, `#product-options`,
  `product-card__summary`, `data-product`). If your theme differs, adjust the
  selectors in `src/scanner.py` and `src/validator.py`.

## Project structure

```
webasyst-ai-rewriter/
├── src/
│   ├── config.py            # .env loader with defensive defaults
│   ├── webasyst_api.py      # Webasyst REST client
│   ├── scanner.py           # sitemap → inventory
│   ├── llm_client.py        # OpenAI-compatible LLM client
│   ├── poster.py            # posting + backups
│   ├── validator.py         # marker validation
│   ├── pipeline.py          # orchestrator
│   ├── report.py            # done-URLs report
│   └── make_report.py       # per-batch report
├── prompts/
│   ├── product_prompt.md    # niche-neutral system prompt
│   └── examples/            # ready-made prompts: textile / electronics / furniture
├── examples/
│   └── inventory.example.json
├── .github/
│   └── workflows/ci.yml     # lint + compile + smoke import test
├── CHANGELOG.md
├── .env.example
└── requirements.txt
```

## Troubleshooting

- **`{"error":"token_required"}`** — normal without a token; it means the API
  endpoint is alive. Supply `WEBASYST_TOKEN`.
- **HTTP 403 from the API** — the hosting WAF is blocking the request form.
  Make sure `access_token` is in the query string and a browser User-Agent is
  used (handled by the client). Do not use `curl` against such hostings.
- **Windows console shows `������`** — console encoding (cp1251) cannot render
  Cyrillic; this is cosmetic. Read UTF-8 files (`data/…`) instead of the
  console output.
- **`invalid_token`** — the token is wrong or expired; re-issue it via the
  client flow above.
- **LLM returns no JSON** — the client raises `LLMError` and retries on
  429/5xx. Check your API key balance and the model name.
- **Hallucinated product facts** — the prompt forbids inventing facts, and the
  few-shot example anchors the model. For extra safety, add a deterministic
  post-check: key numbers from `features` must appear in `description_html`.

## Safety checklist

- Run a small pilot batch (3–5 products) before processing the whole catalog.
- Keep `data/backups/` until you are confident the new texts are good.
- Do not commit `.env` — it is ignored via `.gitignore`.
- The tool writes `meta_title` / `meta_description` **only into empty fields**;
  existing SEO is never touched.

## License

[MIT](LICENSE)

## Disclaimer

This tool writes to a production store via the official REST API. Use it on a
staging copy first, back up your data, and respect the rate limits of both
your LLM provider and your hosting. You are responsible for the content the
LLM generates and for reviewing it before publishing at scale.
