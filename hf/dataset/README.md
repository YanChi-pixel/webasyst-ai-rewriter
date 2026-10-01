---
license: mit
task_categories:
  - text-generation
language:
  - ru
pretty_name: Product card rewrites (RU)
size_categories:
  - n<1K
tags:
  - e-commerce
  - text-generation
  - product-description
  - ai-seo
  - russian
  - instruction-following
---

# Product card rewrites (RU)

Anonymized examples of **product-card description rewriting** for Russian
e-commerce, produced with the same pipeline and prompt that rewrote a real
catalog of 728 cards. Every item is a short block of product facts (the input)
paired with a full rewritten description, a short summary and SEO meta tags (the
output) — following an AI-SEO methodology built for AI-search citation.

The dataset is **synthetic and fully anonymous**: no real brands, article codes,
prices or domains. It documents the *format and quality bar* of the pipeline, not
the client's catalogue.

## Structure

`rewrites.jsonl` — one JSON object per line:

| Field | Meaning |
| --- | --- |
| `vertical` | `textile`, `electronics` or `furniture` |
| `facts` | the raw input the model was given (title, material, specs) |
| `description_html` | the rewritten card: definition, specs, cause→effect, design, characteristics, care, applications, FAQ |
| `summary_text` | 4–6 short lines shown under the product name |
| `meta_title` / `meta_description` | SEO tags (may be `null`) |
| `model` | the model that produced the example |

## The prompt

The rules the examples follow live in the source repository under `prompts/`:

- `prompts/product_prompt.md` — the universal rewrite contract (facts-only, one
  thought per paragraph, strict HTML template, SEO tags only on request);
- `prompts/examples/{textile,electronics,furniture}.md` — one few-shot example per
  vertical, used as the system prompt for generation.

Source and reproduction script:
[github.com/YanChi-pixel/webasyst-ai-rewriter](https://github.com/YanChi-pixel/webasyst-ai-rewriter)
(`hf/build_dataset.py`).

## Use cases

- Fine-tuning / SFT data for Russian product-description generation;
- few-shot examples for "facts → structured product description" tasks;
- a reference for the AI-SEO rewrite format (headings, `faq-item` blocks, SEO tags).

## Caveats

- The labels are model-generated against the prompt, not human-audited.
- The verticals are illustrative; the real pipeline was validated on textiles.

## License

MIT. The content is synthetic and contains no third-party data.
