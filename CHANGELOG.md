# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-02

### Added

- Catalog scanner: sitemap → `data/inventory.json` with rewrite detection.
- LLM copywriter: strict prompt with JSON contract and few-shot examples.
- Poster: `shop.product.update` with per-product rollback backups.
- Validator: live-page marker verification with retries.
- Orchestrator: batch processing, lock file and resumable state.
- Reports: all-done URLs and per-batch exports.
- WAF-friendly Webasyst REST client (token in query string, browser User-Agent).
- Niche-neutral default prompt plus example prompts for textiles, electronics
  and furniture.
- GitHub Actions CI: lint, compile check and smoke import test on Python 3.10/3.12.
- Documentation: README.md (EN) and README.ru.md (RU).

### Changed

- Generalised the original client-specific project into a reusable tool:
  no hardcoded domains, paths or credentials.

### Removed

- All client-specific data, secrets and internal working notes.
