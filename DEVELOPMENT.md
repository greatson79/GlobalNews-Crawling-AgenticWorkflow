# Development Guide -- GlobalNews Crawling & Analysis System

This guide is for developers who want to contribute to, extend, or debug the GlobalNews system.

---

## Table of Contents

1. [Development Setup](#1-development-setup)
2. [Code Organization](#2-code-organization)
3. [Testing](#3-testing)
4. [Debugging](#4-debugging)
5. [Adding a Site Adapter](#5-adding-a-site-adapter)
6. [Code Style](#6-code-style)
7. [Git Workflow](#7-git-workflow)

---

## 1. Development Setup

### 1.1 Prerequisites

- Python 3.12 or later
- macOS with Apple Silicon (M2 Pro 16GB recommended)
- Git

### 1.2 Clone and Install

```bash
git clone https://github.com/your-org/GlobalNews-Crawling-AgenticWorkflow.git
cd GlobalNews-Crawling-AgenticWorkflow

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install all dependencies (including dev tools)
pip install -r requirements.txt

# Install NLP models
python3 -m spacy download en_core_web_sm
playwright install chromium
```

### 1.3 Verify Setup

```bash
# Check all critical imports
python3 -c "
import yaml, requests, pyarrow, torch, bs4, feedparser
from sentence_transformers import SentenceTransformer
print('All critical imports OK')
"

# Run system status check
python3 main.py --mode status

# Run dry-run to validate pipeline wiring
python3 main.py --mode crawl --dry-run
python3 main.py --mode analyze --all-stages --dry-run
```

### 1.4 Development Tools

The project uses these development tools (configured in `pyproject.toml`):

| Tool | Purpose | Config |
|------|---------|--------|
| pytest | Testing | `[tool.pytest.ini_options]` in `pyproject.toml` |
| black | Code formatting (line length 100) | `[tool.black]` |
| ruff | Linting (E, F, W, I, N, UP, B rules) | `[tool.ruff]` |
| mypy | Type checking (strict mode) | `[tool.mypy]` |

---

## 2. Code Organization

### 2.1 Module Responsibilities

| Module | Responsibility | Key Classes/Functions |
|--------|---------------|----------------------|
| `main.py` | CLI entry point, argument parsing, mode dispatch | `cmd_crawl()`, `cmd_analyze()`, `cmd_full()`, `cmd_status()` |
| `src/config/constants.py` | All project-wide constants (paths, thresholds, timeouts) | `PROJECT_ROOT`, `MAX_RETRIES`, `SBERT_BATCH_SIZE`, etc. |
| `src/utils/config_loader.py` | YAML config loading with validation and caching | `load_sources_config()`, `get_enabled_sites()`, `get_site_config()` |
| `src/utils/error_handler.py` | Exception hierarchy, retry decorator, circuit breaker | `GlobalNewsError`, `CircuitBreaker`, `retry_with_backoff()` |
| `src/utils/logging_config.py` | Structured JSON logging setup | `setup_logging()`, `get_logger()` |
| `src/utils/self_recovery.py` | Lock files, health checks, checkpoints, cleanup | `LockFileManager`, `HealthChecker`, `CheckpointManager` |
| `src/crawling/pipeline.py` | Crawl orchestration (per-site iteration, retry coordination) | `run_crawl_pipeline()` |
| `src/crawling/network_guard.py` | Resilient HTTP client (5 retries, rate limiting) | `NetworkGuard`, `FetchResponse` |
| `src/crawling/url_discovery.py` | 3-tier URL discovery (RSS/Sitemap/DOM) | `URLDiscovery` |
| `src/crawling/article_extractor.py` | Article content extraction (Trafilatura/CSS chain) | `ArticleExtractor`, `ExtractionResult` |
| `src/crawling/dedup.py` | 3-level deduplication (URL/Title/SimHash) | `DedupEngine` |
| `src/crawling/anti_block.py` | 6-tier escalation engine | `AntiBlockEngine`, `EscalationTier`, `SiteProfile` |
| `src/crawling/block_detector.py` | 7-type block diagnosis | `BlockDetector`, `BlockDiagnosis`, `BlockType` |
| `src/crawling/retry_manager.py` | 4-level retry (5x2x3x3=90 max) | `RetryManager`, `StrategyMode` |
| `src/crawling/circuit_breaker.py` | Per-site circuit breaker coordination | `CircuitBreakerCoordinator` |
| `src/crawling/ua_manager.py` | 4-tier UA rotation (61+ agents) | `UAManager` |
| `src/crawling/session_manager.py` | Per-UA cookie jars, header diversification | `SessionManager` |
| `src/crawling/stealth_browser.py` | Playwright/Patchright stealth management | `StealthBrowser` |
| `src/crawling/contracts.py` | Data contracts (RawArticle, CrawlResult) | `RawArticle`, `CrawlResult`, `DiscoveredURL` |
| `src/crawling/adapters/base_adapter.py` | Abstract base class for site adapters | `BaseSiteAdapter` |
| `src/analysis/pipeline.py` | 8-stage analysis orchestrator with memory management | `AnalysisPipeline`, `run_analysis_pipeline()` |
| `src/analysis/stage1_preprocessing.py` | JSONL -> Parquet preprocessing (Kiwi/spaCy) | `run_stage1()` |
| `src/analysis/stage2_features.py` | Feature extraction (SBERT, TF-IDF, NER, KeyBERT) | `run_stage2()` |
| `src/analysis/stage3_article_analysis.py` | Sentiment, emotion, STEEPS classification | `run_stage3()` |
| `src/analysis/stage4_aggregation.py` | BERTopic, HDBSCAN, community detection | `run_stage4()` |
| `src/analysis/stage5_timeseries.py` | STL, burst, changepoint, Prophet, wavelet | `run_stage5()` |
| `src/analysis/stage6_cross_analysis.py` | Granger, PCMCI, cross-lingual analysis | `run_stage6()` |
| `src/analysis/stage7_signals.py` | 5-Layer signal classification (L1-L5) | `run_stage7()` |
| `src/analysis/stage8_output.py` | Parquet merge + SQLite index construction | `run_stage8()` |
| `src/storage/parquet_writer.py` | Schema-validated ZSTD Parquet I/O | `ParquetWriter`, `ARTICLES_PA_SCHEMA` |
| `src/storage/sqlite_builder.py` | FTS5 + sqlite-vec index builder | `SQLiteBuilder` |

### 2.2 Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Module files | `snake_case.py` | `url_discovery.py` |
| Classes | `PascalCase` | `NetworkGuard`, `DedupEngine` |
| Functions | `snake_case` | `run_crawl_pipeline()`, `get_adapter()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `SBERT_BATCH_SIZE` |
| Site adapters | `{SiteName}Adapter` | `ChosunAdapter`, `NYTimesAdapter` |
| Adapter files | `{site_id}.py` | `chosun.py`, `nytimes.py` |
| Parquet schemas | `{TABLE}_PA_SCHEMA` | `ARTICLES_PA_SCHEMA` |

### 2.3 Import Patterns

```python
# Standard library first
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

# Third-party
import pyarrow as pa

# Project imports (absolute, from src.)
from src.config.constants import MAX_RETRIES, BACKOFF_FACTOR
from src.utils.error_handler import NetworkError, CrawlError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
```

Heavy dependencies (torch, sentence-transformers, bertopic) are imported lazily inside functions to reduce startup time:

```python
def _compute_embeddings(texts: list[str]) -> np.ndarray:
    # Lazy import: only loaded when actually needed
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return model.encode(texts, batch_size=64)
```

---

## 3. Testing

### 3.1 Test Structure

The project uses a 3-layer testing hierarchy:

```
tests/
  conftest.py           # Shared fixtures (project_root, tmp_project, SOT loader)
  unit/                 # Fast, isolated tests (no I/O, no network)
  integration/          # Tests with real file I/O and SQLite
  structural/           # Tests that verify codebase structure and conventions
```

### 3.2 Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run only structural tests
pytest tests/structural/

# Run with coverage
pytest --cov=src --cov-report=html

# Run tests excluding slow tests
pytest -m "not slow"

# Run a specific test file
pytest tests/unit/test_dedup.py

# Run a specific test
pytest tests/unit/test_dedup.py::TestDedupEngine::test_url_dedup
```

### 3.3 Test Statistics

From the latest E2E validation report:

- **Total tests**: 1678
- **Passed**: 1657
- **Failed**: 8
- **Skipped**: 13

### 3.4 Structural E2E Validation

The structural validator checks the system without making network requests:

```bash
# Full structural validation (produces testing/e2e-test-report.md)
python3 testing/validate_e2e.py

# JSON output only
python3 testing/validate_e2e.py --json-only

# Skip the pytest suite check
python3 testing/validate_e2e.py --skip-pytest
```

The validator runs 13 checks:

1. Python version and critical dependencies
2. Config files present and valid
3. All 44 adapters importable via ADAPTER_REGISTRY
4. Per-site adapter interface validation
5. All 8 analysis stages importable
6. Pipeline orchestration wiring
7. Storage layer schemas
8. DedupEngine functional
9. Retry system constants verified
10. CLI dry-run modes
11. Synthetic data round-trip
12. Pytest suite health

### 3.5 Writing Tests

Test files follow the pattern `test_{module}.py`:

```python
"""Tests for the dedup engine."""

import pytest
from src.crawling.dedup import DedupEngine


class TestDedupEngine:
    """Unit tests for DedupEngine."""

    def test_url_dedup_detects_exact_match(self, tmp_path):
        """URLs with identical normalized forms are detected as duplicates."""
        engine = DedupEngine(db_path=tmp_path / "test_dedup.sqlite")
        article1 = _make_article(url="https://example.com/article/123")
        article2 = _make_article(url="https://example.com/article/123?utm_source=twitter")

        assert not engine.check_and_add(article1)
        assert engine.check_and_add(article2)  # Duplicate after normalization

    def test_simhash_detects_near_duplicate(self, tmp_path):
        """Near-duplicate content is detected via SimHash fingerprinting."""
        engine = DedupEngine(db_path=tmp_path / "test_dedup.sqlite")
        body = "This is a long article about technology trends in 2026. " * 20
        article1 = _make_article(body=body)
        article2 = _make_article(body=body.replace("2026", "2027"))

        assert not engine.check_and_add(article1)
        assert engine.check_and_add(article2)  # Near-duplicate via SimHash
```

---

## 4. Debugging

### 4.1 Site Not Crawling (0 Articles)

**Diagnosis steps**:

```bash
# 1. Check if the site is enabled in config
python3 -c "
from src.utils.config_loader import get_site_config
cfg = get_site_config('chosun')
print(f\"Enabled: {cfg['meta']['enabled']}\")
print(f\"Method: {cfg['crawl']['primary_method']}\")
"

# 2. Check if the adapter imports correctly
python3 -c "
from src.crawling.adapters import get_adapter
a = get_adapter('chosun')
print(f'Adapter: {a.SITE_ID}, RSS: {a.RSS_URL}')
"

# 3. Test URL discovery in isolation
python3 -c "
from src.crawling.network_guard import NetworkGuard
from src.crawling.url_discovery import URLDiscovery
from src.crawling.adapters import get_adapter

guard = NetworkGuard()
adapter = get_adapter('chosun')
discovery = URLDiscovery(network_guard=guard, adapter=adapter)
# Try RSS directly
urls = discovery._discover_via_rss(adapter=adapter, site_config=None, date=None)
print(f'RSS URLs found: {len(urls)}')
for url in urls[:5]:
    print(f'  {url.url}')
"

# 4. Check circuit breaker state
python3 -c "
from src.crawling.circuit_breaker import CircuitBreakerCoordinator
cb = CircuitBreakerCoordinator()
state = cb.get_state('chosun')
print(f'Circuit state: {state}')
"

# 5. Check crawl log for errors
grep "chosun" data/logs/crawl.log | tail -20
```

### 4.2 Articles Missing Fields

**Diagnosis steps**:

```bash
# 1. Check raw JSONL for field presence
python3 -c "
import json
with open('data/raw/2026-02-25/all_articles.jsonl') as f:
    for i, line in enumerate(f):
        article = json.loads(line)
        missing = [k for k in ['title', 'body', 'url', 'source_id'] if not article.get(k)]
        if missing:
            print(f'Line {i}: missing {missing} (source={article.get(\"source_id\")})')
        if i >= 100:
            break
"

# 2. Check extraction method distribution
python3 -c "
import json
from collections import Counter
methods = Counter()
with open('data/raw/2026-02-25/all_articles.jsonl') as f:
    for line in f:
        a = json.loads(line)
        methods[a.get('crawl_method', 'unknown')] += 1
print(dict(methods))
"

# 3. Test extraction on a specific URL
python3 -c "
from src.crawling.network_guard import NetworkGuard
from src.crawling.article_extractor import ArticleExtractor
from src.crawling.adapters import get_adapter

guard = NetworkGuard()
adapter = get_adapter('chosun')
extractor = ArticleExtractor(network_guard=guard)
result = extractor.extract(
    url='https://www.chosun.com/politics/2026/02/25/TEST',
    adapter=adapter,
)
print(f'Title: {result.title}')
print(f'Body length: {len(result.body)}')
print(f'Method: {result.extraction_method}')
"
```

### 4.3 Memory Issues

**Diagnosis steps**:

```bash
# 1. Check peak memory per stage from logs
grep "peak_memory" data/logs/analysis.log | tail -10

# 2. Monitor memory in real-time
# In one terminal:
python3 main.py --mode analyze --stage 2 --log-level DEBUG

# In another terminal:
while true; do
    ps aux | grep "main.py" | grep -v grep | awk '{print $6/1024 "MB"}'
    sleep 5
done

# 3. Profile a specific stage
python3 -c "
import resource
from src.analysis.stage2_features import run_stage2
result = run_stage2()
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024
print(f'Peak RSS: {peak:.2f} GB')
"
```

### 4.4 Analysis Stage Failures

**Diagnosis steps**:

```bash
# 1. Check which stage failed
grep "FAILED" data/logs/analysis.log | tail -5

# 2. Check stage dependencies (can you start from stage N?)
python3 -c "
from src.analysis.pipeline import STAGE_DEPENDENCIES
for stage, deps in sorted(STAGE_DEPENDENCIES.items()):
    status = []
    for dep in deps:
        exists = dep.exists()
        status.append(f'{dep.name}={\"OK\" if exists else \"MISSING\"}'  )
    print(f'Stage {stage}: {\" | \".join(status) if status else \"no deps\"}'  )
"

# 3. Run a specific stage with DEBUG logging
python3 main.py --mode analyze --stage 3 --log-level DEBUG

# 4. Verify Parquet schema integrity
python3 -c "
import pyarrow.parquet as pq
t = pq.read_table('data/processed/articles.parquet')
print(f'Schema: {t.schema}')
print(f'Rows: {t.num_rows}')
print(f'Columns: {t.num_columns}')
"
```

### 4.5 Enabling Debug Logging

```bash
# CLI flag
python3 main.py --mode crawl --log-level DEBUG

# Or set environment variable
export GLOBALNEWS_LOG_LEVEL=DEBUG
python3 main.py --mode crawl
```

Debug logs include:
- Every HTTP request with timing and status code
- UA selection per request
- Block detection analysis details
- Escalation tier transitions
- Dedup check results
- Memory usage at stage boundaries

---

## 5. Adding a Site Adapter

### 5.1 Template

```python
"""SiteName (domain.com) site adapter.

Group X -- Description.
Primary method: rss|sitemap|dom|playwright. Fallback: Y > Z.
Bot block level: LOW|MEDIUM|HIGH. Proxy: required|not required.
"""

from __future__ import annotations

import logging
from src.crawling.adapters.base_adapter import BaseSiteAdapter

logger = logging.getLogger(__name__)


class SiteNameAdapter(BaseSiteAdapter):
    """Adapter for SiteName (domain.com)."""

    # --- Site identity (REQUIRED) ---
    SITE_ID = "sitename"          # Must match sources.yaml key
    SITE_NAME = "Site Name"
    SITE_URL = "https://www.domain.com"
    LANGUAGE = "en"               # ISO 639-1
    REGION = "us"
    GROUP = "E"                   # A-G

    # --- URL discovery (at least one of RSS_URL, SITEMAP_URL, SECTION_URLS) ---
    RSS_URL = "https://www.domain.com/rss"
    RSS_URLS = []                 # Additional category RSS feeds
    SITEMAP_URL = ""

    # --- Article extraction selectors (REQUIRED) ---
    TITLE_CSS = 'meta[property="og:title"]'
    TITLE_CSS_FALLBACK = "h1"
    BODY_CSS = "article"
    BODY_CSS_FALLBACK = "div.content"
    DATE_CSS = 'meta[property="article:published_time"]'
    AUTHOR_CSS = "span.author"
    ARTICLE_LINK_CSS = "a"

    BODY_EXCLUDE_CSS = "script, style, iframe"

    # --- Section pages for DOM fallback ---
    SECTION_URLS = []
    PAGINATION_TYPE = "none"      # none|page_number|load_more|infinite_scroll
    PAGINATION_PARAM = "page"
    MAX_PAGES = 5

    # --- Rate limiting ---
    RATE_LIMIT_SECONDS = 5
    MAX_REQUESTS_PER_HOUR = 720
    JITTER_SECONDS = 0

    # --- Anti-block ---
    ANTI_BLOCK_TIER = 1
    UA_TIER = 2
    REQUIRES_PROXY = False
    PROXY_REGION = None
    BOT_BLOCK_LEVEL = "LOW"

    # --- Content ---
    PAYWALL_TYPE = "none"         # none|soft-metered|hard
    CHARSET = "utf-8"
    RENDERING_REQUIRED = False
```

### 5.2 Checklist

Before submitting a new adapter:

- [ ] Adapter class inherits from `BaseSiteAdapter`
- [ ] `SITE_ID` matches the key in `data/config/sources.yaml`
- [ ] `SITE_ID` is registered in the sub-package `__init__.py`
- [ ] At least one URL discovery source is configured (RSS, Sitemap, or Section URLs)
- [ ] CSS selectors tested against live HTML (`TITLE_CSS`, `BODY_CSS` at minimum)
- [ ] `BODY_EXCLUDE_CSS` removes ads, navigation, and scripts from body text
- [ ] `RATE_LIMIT_SECONDS` respects the site's robots.txt `Crawl-delay`
- [ ] `BOT_BLOCK_LEVEL` matches the site's observed blocking behavior
- [ ] Module-level docstring includes group, primary method, and bot block level
- [ ] Dry-run succeeds: `python3 main.py --mode crawl --sites sitename --dry-run`
- [ ] Live test produces articles: `python3 main.py --mode crawl --sites sitename`
- [ ] `python3 scripts/validate_site_coverage.py` passes

---

## 6. Code Style

### 6.1 Formatting

- Line length: 100 characters (configured in `pyproject.toml`)
- Formatter: black
- Linter: ruff (rules: E, F, W, I, N, UP, B)

```bash
# Format code
black src/ tests/ main.py

# Lint
ruff check src/ tests/ main.py

# Type check
mypy src/
```

### 6.2 Type Hints

All public functions must have type hints:

```python
def fetch(self, url: str, headers: dict[str, str] | None = None,
          timeout: int = 30) -> FetchResponse:
    """Fetch a URL with retry and rate limiting.

    Args:
        url: Target URL.
        headers: Optional custom headers.
        timeout: Request timeout in seconds.

    Returns:
        FetchResponse with status_code, body, headers.

    Raises:
        NetworkError: After all retries exhausted.
        RateLimitError: If rate limit is violated.
    """
```

### 6.3 Docstring Conventions

All modules, classes, and public functions must have docstrings:

```python
"""Module-level docstring: one-line summary.

Longer description explaining purpose, architecture references,
and key design decisions.

Reference: Step N, Section X.
"""
```

### 6.4 Error Handling Patterns

Always use the project's exception hierarchy:

```python
from src.utils.error_handler import NetworkError, ParseError

# Raise specific exceptions
raise NetworkError(
    f"Request failed: {url}",
    status_code=response.status_code,
    url=url,
)

# Catch at appropriate levels
try:
    result = extractor.extract(url, adapter)
except ParseError as e:
    logger.warning("Extraction failed for %s: %s", url, e)
    # Skip this article, continue with next
except NetworkError as e:
    logger.error("Network error for %s: %s", url, e)
    # Let retry manager handle this
    raise
```

### 6.5 Logging Patterns

Use structured logging with key-value pairs:

```python
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Good: structured with context
logger.info("Article extracted", extra={
    "site_id": "chosun",
    "url": url,
    "method": "trafilatura",
    "body_length": len(body),
})

# Acceptable: format string with positional args
logger.info("Extracted %s articles from %s", count, site_id)

# Bad: f-string (prevents structured log parsing)
logger.info(f"Extracted {count} articles from {site_id}")  # Avoid
```

---

## 7. Git Workflow

### 7.1 Branch Naming

| Pattern | Use |
|---------|-----|
| `feat/add-site-{site_id}` | Adding a new site adapter |
| `feat/{description}` | New feature |
| `fix/{description}` | Bug fix |
| `refactor/{description}` | Code restructuring |
| `docs/{description}` | Documentation changes |
| `test/{description}` | Test additions or fixes |

### 7.2 Commit Messages

Follow the conventional commits format:

```
feat(adapters): add Reuters adapter for Group E

- Create src/crawling/adapters/english/reuters.py
- Register in english/__init__.py
- Add to data/config/sources.yaml
- RSS primary method, API fallback
```

Prefix types:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring (no behavior change)
- `docs`: Documentation
- `test`: Tests
- `chore`: Build, CI, tooling

### 7.3 PR Checklist

Before submitting a pull request:

- [ ] All tests pass: `pytest`
- [ ] Code is formatted: `black --check src/ tests/ main.py`
- [ ] Linting passes: `ruff check src/ tests/ main.py`
- [ ] Type checking passes: `mypy src/`
- [ ] Structural validation passes: `python3 testing/validate_e2e.py`
- [ ] New code has docstrings and type hints
- [ ] Constants are centralized in `src/config/constants.py` (no magic numbers)
- [ ] New site adapters pass the adapter checklist (Section 5.2)
- [ ] `sources.yaml` is updated if sites were added/modified
