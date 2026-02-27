# Operations Guide -- GlobalNews Crawling & Analysis System

This guide is intended for operators responsible for the day-to-day running of the GlobalNews pipeline. It covers monitoring, scheduled jobs, site management, failure handling, data archival, and performance tuning.

---

## Table of Contents

1. [Daily Monitoring](#1-daily-monitoring)
2. [Cron Jobs](#2-cron-jobs)
3. [Adding a New Site](#3-adding-a-new-site)
4. [Handling Blocked Sites](#4-handling-blocked-sites)
5. [Tier 6 Escalation](#5-tier-6-escalation)
6. [Data Archival](#6-data-archival)
7. [Self-Recovery System](#7-self-recovery-system)
8. [Performance Tuning](#8-performance-tuning)
9. [Disaster Recovery](#9-disaster-recovery)

---

## 1. Daily Monitoring

Every morning, verify the previous night's pipeline run succeeded.

### 1.1 Check the Daily Log

```bash
# Today's daily log
cat data/logs/daily/$(date +%Y-%m-%d)-daily.log

# Look for the SUCCESS or FAILED line
grep "GlobalNews Daily Pipeline --" data/logs/daily/$(date +%Y-%m-%d)-daily.log
```

Expected output on success:

```
[2026-02-26T02:47:12Z] [INFO]  GlobalNews Daily Pipeline -- SUCCESS
```

### 1.2 Check for Alerts

```bash
ls -la data/logs/alerts/
# Any file dated today indicates a failure that needs attention
cat data/logs/alerts/$(date +%Y-%m-%d)-daily-failure.log 2>/dev/null || echo "No alerts."
```

### 1.3 Verify Article Count

```bash
# Check raw JSONL output for yesterday
YESTERDAY=$(date -v -1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
wc -l data/raw/${YESTERDAY}/all_articles.jsonl 2>/dev/null || echo "No articles file found."
```

Target: 500+ articles per day across all sites. If consistently below 300, investigate blocked sites.

### 1.4 Check Crawl Report

```bash
# Structured JSON report from the crawl
python3 -c "
import json
with open('data/raw/${YESTERDAY}/crawl_report.json') as f:
    r = json.load(f)
print(f\"Total articles: {r.get('total_articles', 0)}\")
print(f\"Sites attempted: {r.get('total_sites_attempted', 0)}\")
print(f\"Sites failed: {r.get('sites_failed', 0)}\")
print(f\"Elapsed: {r.get('elapsed_seconds', 0):.0f}s\")
" 2>/dev/null || echo "No crawl report found."
```

### 1.5 Check Error Log

```bash
# Recent errors (last 50 lines)
tail -50 data/logs/errors.log

# Count errors by level in the last 24 hours
grep "$(date +%Y-%m-%d)" data/logs/errors.log | wc -l
```

### 1.6 Check Pipeline Status

```bash
python3 main.py --mode status
```

This shows configuration file status, site count, daily article estimate, group breakdown, and data directory inventory.

### 1.7 Check Lock Files

```bash
# Verify no stale locks exist
python3 -m src.utils.self_recovery --check-lock daily
python3 -m src.utils.self_recovery --check-lock weekly
```

If a lock is stale (pipeline crashed without cleanup), force-release it:

```bash
python3 -m src.utils.self_recovery --force-release-lock daily
```

---

## 2. Cron Jobs

Three scheduled jobs automate the pipeline. The cron schedule is defined in `config/crontab.txt`.

### 2.1 Schedule Overview

| Schedule | Script | Purpose |
|----------|--------|---------|
| Daily at 02:00 AM | `scripts/run_daily.sh` | Full crawl + 8-stage analysis |
| Sundays at 01:00 AM | `scripts/run_weekly_rescan.sh` | Validate adapter health, detect broken selectors |
| 1st of month at 03:00 AM | `scripts/archive_old_data.sh` | Compress and archive data older than 30 days |

### 2.2 Installing Cron Jobs

1. Edit `config/crontab.txt` and update `PROJECT_DIR` to your actual project path:

```bash
# Open the template
nano config/crontab.txt

# Update this line:
PROJECT_DIR=/path/to/GlobalNews-Crawling-AgenticWorkflow
```

2. Install the crontab:

```bash
# Replace existing crontab (WARNING: overwrites all cron jobs)
crontab config/crontab.txt

# Or append to existing crontab (safer)
(crontab -l 2>/dev/null; cat config/crontab.txt) | crontab -
```

3. Verify installation:

```bash
crontab -l
```

### 2.3 Verifying Cron Execution

```bash
# Check cron log output
tail -20 data/logs/cron/daily.log
tail -20 data/logs/cron/weekly.log
tail -20 data/logs/cron/archive.log
```

### 2.4 Troubleshooting Cron

| Symptom | Cause | Solution |
|---------|-------|----------|
| Cron does not run | `PATH` not set in crontab | Verify `PATH` line in `config/crontab.txt` |
| "No virtualenv found" | Venv not at expected location | Create `.venv` in project root: `python3 -m venv .venv` |
| Lock acquisition failed | Previous run still executing or crashed | Check with `--check-lock daily`, force-release if stale |
| Permission denied | Script not executable | `chmod +x scripts/run_daily.sh scripts/run_weekly_rescan.sh scripts/archive_old_data.sh` |

### 2.5 Manual Execution

You can run any cron job manually:

```bash
# Daily pipeline (specific date)
scripts/run_daily.sh --date 2026-02-25

# Daily pipeline (dry run)
scripts/run_daily.sh --dry-run

# Weekly rescan
scripts/run_weekly_rescan.sh

# Monthly archival (dry run to preview)
scripts/archive_old_data.sh --dry-run
```

---

## 3. Adding a New Site

This section walks through adding site number 45 to the system.

### 3.1 Prerequisites

Before adding a site, determine:

- **Domain**: e.g., `example.com`
- **Language**: ISO 639-1 code (e.g., `en`, `ko`, `ja`)
- **Group**: Which group it belongs to (A-G)
- **RSS/Sitemap availability**: Check `https://example.com/rss`, `https://example.com/sitemap.xml`
- **Bot-blocking level**: LOW, MEDIUM, or HIGH
- **Paywall type**: `none`, `soft-metered`, or `hard`

### 3.2 Step 1: Create the Site Adapter

Create a new adapter file in the appropriate subdirectory under `src/crawling/adapters/`:

| Group | Directory |
|-------|-----------|
| A (Korean Major), B (Korean Economy), C (Korean Niche) | `src/crawling/adapters/kr_major/` |
| D (Korean IT/Science) | `src/crawling/adapters/kr_tech/` |
| E (English-Language Western) | `src/crawling/adapters/english/` |
| F (Asia-Pacific), G (Europe/ME) | `src/crawling/adapters/multilingual/` |

Create the adapter file, e.g., `src/crawling/adapters/english/example.py`:

```python
"""Example News (example.com) site adapter.

Group E -- English-Language Western.
Primary method: RSS. Fallback: Sitemap > DOM.
Bot block level: LOW. Proxy: Not required.
"""

from __future__ import annotations

import logging
from src.crawling.adapters.base_adapter import BaseSiteAdapter

logger = logging.getLogger(__name__)


class ExampleAdapter(BaseSiteAdapter):
    """Adapter for Example News (example.com)."""

    # --- Site identity ---
    SITE_ID = "example"
    SITE_NAME = "Example News"
    SITE_URL = "https://www.example.com"
    LANGUAGE = "en"
    REGION = "us"
    GROUP = "E"

    # --- URL discovery ---
    RSS_URL = "https://www.example.com/rss/all"
    RSS_URLS = []
    SITEMAP_URL = "https://www.example.com/sitemap.xml"

    # --- Article extraction selectors ---
    TITLE_CSS = 'meta[property="og:title"]'
    TITLE_CSS_FALLBACK = "h1.article-title"
    BODY_CSS = "div.article-body"
    BODY_CSS_FALLBACK = "article"
    DATE_CSS = 'meta[property="article:published_time"]'
    AUTHOR_CSS = "span.byline"
    ARTICLE_LINK_CSS = 'a[href*="/article/"]'

    BODY_EXCLUDE_CSS = "script, style, iframe, div.ad-container"

    # --- Section pages for DOM discovery ---
    SECTION_URLS = [
        "https://www.example.com/world",
        "https://www.example.com/business",
        "https://www.example.com/technology",
    ]
    PAGINATION_TYPE = "page_number"
    PAGINATION_PARAM = "page"
    MAX_PAGES = 5

    # --- Rate limiting ---
    RATE_LIMIT_SECONDS = 5
    MAX_REQUESTS_PER_HOUR = 720
    JITTER_SECONDS = 1

    # --- Anti-block ---
    ANTI_BLOCK_TIER = 1
    UA_TIER = 2
    REQUIRES_PROXY = False
    BOT_BLOCK_LEVEL = "LOW"

    # --- Paywall ---
    PAYWALL_TYPE = "none"
    CHARSET = "utf-8"
    RENDERING_REQUIRED = False
```

### 3.3 Step 2: Register the Adapter

Add the adapter to the sub-package `__init__.py`. For an English-language site, edit `src/crawling/adapters/english/__init__.py`:

```python
from src.crawling.adapters.english.example import ExampleAdapter

ENGLISH_ADAPTERS["example"] = ExampleAdapter
```

### 3.4 Step 3: Add to sources.yaml

Add the site configuration to `data/config/sources.yaml`:

```yaml
  example:
    name: "Example News"
    url: "https://www.example.com"
    region: "us"
    language: "en"
    group: "E"
    crawl:
      primary_method: "rss"
      fallback_methods: ["sitemap", "dom"]
      rss_url: "https://www.example.com/rss/all"
      sitemap_url: "/sitemap.xml"
      rate_limit_seconds: 5
      crawl_delay_mandatory: null
      max_requests_per_hour: 720
      jitter_seconds: 1
    anti_block:
      ua_tier: 2
      default_escalation_tier: 1
      bot_block_level: "LOW"
      requires_proxy: false
    extraction:
      paywall_type: "none"
      rendering_required: false
      charset: "utf-8"
    meta:
      enabled: true
      daily_article_estimate: 100
      difficulty: "Easy"
```

### 3.5 Step 4: Test the Adapter

```bash
# 1. Verify the adapter imports without errors
python3 -c "from src.crawling.adapters import get_adapter; a = get_adapter('example'); print(f'{a.SITE_ID}: OK')"

# 2. Dry-run crawl to check config validity
python3 main.py --mode crawl --sites example --dry-run

# 3. Test a live crawl (single site)
python3 main.py --mode crawl --sites example --date $(date +%Y-%m-%d)

# 4. Check output
wc -l data/raw/$(date +%Y-%m-%d)/all_articles.jsonl
```

### 3.6 Step 5: Run Site Coverage Validation

```bash
python3 scripts/validate_site_coverage.py
```

This validates that all sites in `sources.yaml` have a registered adapter and vice versa.

---

## 4. Handling Blocked Sites

When a site starts blocking crawl requests, the system escalates through 6 tiers automatically.

### 4.1 Diagnosis Flowchart

```
Site returning errors or empty content
    |
    v
[1] Check robots.txt compliance
    - Is the site's robots.txt disallowing the paths you crawl?
    - Is the Crawl-delay being respected?
    |
    v
[2] Check UA rotation
    - Is the UA tier appropriate for the site's bot-block level?
    - Upgrade UA tier: T1 -> T2 -> T3 in sources.yaml
    |
    v
[3] Check rate limits
    - Increase rate_limit_seconds (e.g., 5 -> 10 -> 15)
    - Check if the site returns 429 or Retry-After headers
    |
    v
[4] Check anti-block tier
    - Current tier vs. block type (see block_detector.py for 7 types)
    - Increase default_escalation_tier in sources.yaml
    |
    v
[5] Check if proxy is needed
    - Geo-blocked sites require a regional proxy
    - Set requires_proxy: true and proxy_region: "XX"
    |
    v
[6] Manual intervention (Tier 6)
    - See Section 5 below
```

### 4.2 Block Types and Countermeasures

| Block Type | Detection | Countermeasure |
|------------|-----------|----------------|
| IP Block | 403 status, "access denied" | Session cycling (T2), proxy rotation (T5) |
| UA Filter | 406 status, bot verification redirect | UA tier upgrade (T2/T3) |
| Rate Limit | 429 status, Retry-After header | Increase delay, respect Retry-After |
| CAPTCHA | reCAPTCHA/hCaptcha/Turnstile markers | Stealth browser (T3/T4) |
| JS Challenge | Cloudflare challenge, empty body | Playwright/Patchright (T3/T4) |
| Fingerprint | TLS rejection, 403 with CDN headers | Patchright fingerprint stealth (T4) |
| Geo-Block | Redirect to regional site | Proxy with matching region (T5) |

### 4.3 Adjusting Anti-Block Settings

Edit the site's configuration in `data/config/sources.yaml`:

```yaml
  chosun:
    anti_block:
      ua_tier: 3                    # Was 2, upgraded due to UA detection
      default_escalation_tier: 2    # Was 1, start at session cycling
      bot_block_level: "HIGH"       # Was "MEDIUM"
      requires_proxy: true          # Enable proxy
      proxy_region: "kr"
    crawl:
      rate_limit_seconds: 10        # Was 5, increased to reduce detection
```

---

## 5. Tier 6 Escalation

When all 90 retry attempts (5 x 2 x 3 x 3) are exhausted for a site, a Tier 6 escalation report is generated.

### 5.1 Escalation Report Location

```
logs/tier6-escalation/{site_id}-{date}.json
```

Example: `logs/tier6-escalation/chosun-2026-02-25.json`

### 5.2 Reading the Escalation Report

```bash
python3 -c "
import json
with open('logs/tier6-escalation/chosun-2026-02-25.json') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))
"
```

The report contains:

- `site_id`: Which site failed
- `date`: When it happened
- `total_attempts`: Number of attempts made (up to 90)
- `block_types_observed`: Which block types were detected
- `last_error`: The final error message
- `tier_history`: Progression through escalation tiers
- `recommendation`: Suggested next step

### 5.3 Manual Intervention Steps

1. **Read the report** to understand the block type and progression.

2. **Test manually** using a browser to verify the site is still accessible:

```bash
# Quick check with curl
curl -s -o /dev/null -w "%{http_code}" https://www.example.com/

# Check with the system's network guard
python3 -c "
from src.crawling.network_guard import NetworkGuard
ng = NetworkGuard()
resp = ng.fetch('https://www.example.com/')
print(f'Status: {resp.status_code}, Length: {len(resp.body)}')
"
```

3. **Update the adapter** if selectors have changed (site redesign).

4. **Update anti-block settings** in `data/config/sources.yaml` based on findings.

5. **Test the fix**:

```bash
python3 main.py --mode crawl --sites example --date $(date +%Y-%m-%d)
```

6. **Clear old escalation reports** after resolution:

```bash
rm logs/tier6-escalation/example-*.json
```

---

## 6. Data Archival

### 6.1 How Monthly Archival Works

The `scripts/archive_old_data.sh` script runs on the 1st of each month at 03:00 AM. It:

1. Scans `data/raw/` and `data/processed/` for date-named directories older than 30 days
2. Creates compressed tar.gz archives in `data/archive/YYYY/MM/`
3. Generates SHA-256 checksums for each archive
4. Verifies archive integrity before deleting originals
5. Maintains a 2-day safety margin (never archives the last 2 days)

### 6.2 Archive Structure

```
data/archive/
  2026/
    01/
      raw-2026-01-15.tar.gz
      raw-2026-01-15.tar.gz.sha256
      processed-2026-01-15.tar.gz
      processed-2026-01-15.tar.gz.sha256
```

### 6.3 Manual Archival

```bash
# Preview what would be archived
scripts/archive_old_data.sh --dry-run

# Archive data older than 60 days
scripts/archive_old_data.sh --days 60

# Normal execution (30-day threshold)
scripts/archive_old_data.sh
```

### 6.4 Restoring Archived Data

```bash
# List available archives
ls data/archive/2026/01/

# Verify checksum before restoring
cd data/archive/2026/01
shasum -a 256 -c raw-2026-01-15.tar.gz.sha256

# Restore to original location
tar -xzf raw-2026-01-15.tar.gz -C ../../raw/
```

---

## 7. Self-Recovery System

The self-recovery infrastructure enables >= 7 days of unattended operation with >= 90% auto-recovery rate.

### 7.1 Components

| Component | Purpose | CLI |
|-----------|---------|-----|
| LockFileManager | PID-based lock files, stale detection (> 4 hours) | `--acquire-lock`, `--release-lock`, `--check-lock` |
| HealthChecker | Pre-run validation (disk, Python, deps, config) | `--health-check` |
| CheckpointManager | Pipeline progress tracking, crash resume | `--checkpoint-status` |
| CleanupManager | Stale temp cleanup, log rotation | `--cleanup` |
| RecoveryOrchestrator | Top-level coordination | `--status` |

### 7.2 Health Checks

```bash
# Run all health checks
python3 -m src.utils.self_recovery --health-check
```

The health check verifies:

- **Disk space**: >= 2 GB free
- **Python version**: >= 3.11
- **Critical dependencies**: importable (yaml, requests, pyarrow, etc.)
- **Configuration files**: `data/config/sources.yaml` and `data/config/pipeline.yaml` exist and are valid
- **Log directory**: writable

### 7.3 Circuit Breaker States

Each site has an independent circuit breaker with three states:

```
CLOSED ----[5 consecutive failures]----> OPEN
   ^                                       |
   |                                   [300s timeout]
   |                                       |
   +----[3 consecutive successes]---- HALF_OPEN
```

- **CLOSED**: Normal operation. Failures are counted.
- **OPEN**: Site is skipped. After 300 seconds (5 minutes), transitions to HALF_OPEN.
- **HALF_OPEN**: A single probe request is allowed. 3 consecutive successes return to CLOSED; any failure returns to OPEN.

### 7.4 Checkpoint Resume

If the analysis pipeline crashes mid-stage, it can resume from the last completed stage:

```bash
# Check checkpoint status
python3 -m src.utils.self_recovery --checkpoint-status

# Resume analysis from a specific stage (e.g., stage 3)
python3 main.py --mode analyze --stage 3
```

The pipeline checks for upstream Parquet files before starting any stage. If all dependencies for stage N exist on disk, stage N can be run independently.

### 7.5 Manual Recovery Commands

```bash
# Full system status
python3 -m src.utils.self_recovery --status

# Clean up stale temp files and old logs
python3 -m src.utils.self_recovery --cleanup

# Force-release a stale lock
python3 -m src.utils.self_recovery --force-release-lock daily
```

---

## 8. Performance Tuning

### 8.1 Crawling Concurrency

The crawling pipeline processes sites sequentially within each group but can process up to 6 groups concurrently. Key settings in `src/config/constants.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENT_CRAWL_GROUPS` | 6 | Maximum groups processed in parallel |
| `DEFAULT_RATE_LIMIT_SECONDS` | 5 | Minimum delay between requests per site |
| `DEFAULT_REQUEST_TIMEOUT_SECONDS` | 30 | HTTP request timeout |
| `MAX_ARTICLES_PER_SITE_PER_DAY` | 1000 | Safety cap per site |

### 8.2 Analysis Pipeline Memory

Each analysis stage has a memory budget. The pipeline aborts if RSS exceeds 10 GB and warns above 5 GB. Stage memory profiles on M2 Pro 16GB:

| Stage | Description | Peak Memory |
|-------|-------------|-------------|
| 1 | Preprocessing | ~1.0 GB |
| 2 | Feature Extraction (SBERT) | ~2.4 GB |
| 3 | Article Analysis | ~1.8 GB |
| 4 | Aggregation (BERTopic) | ~1.5 GB |
| 5 | Time Series | ~0.5 GB |
| 6 | Cross Analysis | ~0.8 GB |
| 7 | Signal Classification | ~0.5 GB |
| 8 | Data Output | ~0.5 GB |

Between stages, `gc.collect()` is called to free memory. Torch CUDA/MPS caches are also cleared.

### 8.3 Batch Sizes

Adjust in `data/config/pipeline.yaml` or `src/config/constants.py`:

| Constant | Default | Effect |
|----------|---------|--------|
| `DEFAULT_BATCH_SIZE` | 500 | General article batch size |
| `SBERT_BATCH_SIZE` | 64 | SBERT embedding batch (optimized for M2 Pro) |
| `NER_BATCH_SIZE` | 32 | NER processing batch |
| `KEYBERT_TOP_N` | 10 | Keywords per article |

Reducing batch sizes decreases memory usage at the cost of slower processing.

### 8.4 Pipeline Timeout

The daily pipeline script enforces a 4-hour timeout:

```bash
# In scripts/run_daily.sh
PIPELINE_TIMEOUT=14400  # seconds (4 hours)
```

If the pipeline consistently times out:

1. Check which stage is slowest (review `data/logs/analysis.log`)
2. Reduce the number of sites being crawled (`--groups A,B,E`)
3. Reduce batch sizes
4. Skip optional analysis stages by editing `data/config/pipeline.yaml` (set `enabled: false`)

---

## 9. Disaster Recovery

### 9.1 Full Re-Crawl

To re-crawl all sites for a specific date:

```bash
# Remove existing data for that date
rm -rf data/raw/2026-02-25/

# Re-crawl
python3 main.py --mode crawl --date 2026-02-25
```

### 9.2 Re-Run Analysis

To re-run the entire analysis pipeline:

```bash
# Remove processed data (optional, for clean re-run)
rm -f data/processed/articles.parquet
rm -f data/features/*.parquet
rm -f data/analysis/*.parquet
rm -f data/output/*.parquet data/output/index.sqlite

# Re-run all stages
python3 main.py --mode analyze --all-stages
```

Or re-run from a specific stage:

```bash
# Re-run from stage 4 onwards
python3 main.py --mode analyze --stage 4
python3 main.py --mode analyze --stage 5
python3 main.py --mode analyze --stage 6
python3 main.py --mode analyze --stage 7
python3 main.py --mode analyze --stage 8
```

### 9.3 Restoring from Archive

```bash
# List all archives
find data/archive/ -name "*.tar.gz" | sort

# Verify and restore specific date
cd data/archive/2026/01
shasum -a 256 -c raw-2026-01-15.tar.gz.sha256
tar -xzf raw-2026-01-15.tar.gz -C ../../raw/

# Re-run analysis on restored data
python3 main.py --mode analyze --all-stages
```

### 9.4 Database Reconstruction

If the SQLite index is corrupted, rebuild it from existing Parquet files:

```bash
# Remove corrupted database
rm -f data/output/index.sqlite

# Re-run Stage 8 only (builds SQLite from Parquet)
python3 main.py --mode analyze --stage 8
```

### 9.5 Clean Slate Reset

To reset everything and start fresh:

```bash
# Remove all runtime data (DESTRUCTIVE)
rm -rf data/raw/ data/processed/ data/features/ data/analysis/ data/output/ data/logs/

# Re-create required directories (they are auto-created on first run)
mkdir -p data/config

# Copy config if needed
# The config files in data/config/ should already be in place

# Run full pipeline
python3 main.py --mode full --date $(date +%Y-%m-%d)
```

---

## Appendix: Log File Locations

| Log | Path | Rotation |
|-----|------|----------|
| Daily pipeline | `data/logs/daily/YYYY-MM-DD-daily.log` | 30 days, > 500 MB triggers cleanup |
| Crawl log | `data/logs/crawl.log` | 10 MB, 5 backups |
| Analysis log | `data/logs/analysis.log` | 10 MB, 5 backups |
| Error log | `data/logs/errors.log` | 10 MB, 5 backups |
| Cron daily | `data/logs/cron/daily.log` | Manual |
| Cron weekly | `data/logs/cron/weekly.log` | Manual |
| Cron archive | `data/logs/cron/archive.log` | Manual |
| Alerts | `data/logs/alerts/YYYY-MM-DD-*.log` | Manual review |
| Weekly rescan | `data/logs/weekly/rescan-YYYY-MM-DD.log` | Manual |
| Weekly report | `data/logs/weekly/rescan-YYYY-MM-DD.md` | Manual |
| Tier 6 escalation | `logs/tier6-escalation/{site}-{date}.json` | Manual |
| Archival | `data/logs/archive/YYYY-MM-DD-archive.log` | Manual |
