# GlobalNews Crawling & Analysis System

A staged-monolith Python system that crawls 44 international news sites daily, runs an 8-stage NLP analysis pipeline with 56 techniques, and produces Parquet/SQLite datasets for social trend research. Designed for unattended operation on macOS with self-recovery, 4-level retry, and 6-tier anti-block escalation.

---

## Table of Contents

- [Quick Start](#quick-start)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Directory Structure](#directory-structure)
- [Configuration](#configuration)
- [Analysis Pipeline](#analysis-pipeline)
- [5-Layer Signal Classification](#5-layer-signal-classification)
- [Troubleshooting](#troubleshooting)
- [Further Reading](#further-reading)
- [License](#license)

---

## Quick Start

Get the system running with your first crawl in under 5 minutes.

```bash
# 1. Clone the repository
git clone https://github.com/your-org/GlobalNews-Crawling-AgenticWorkflow.git
cd GlobalNews-Crawling-AgenticWorkflow

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download the spaCy English model
python3 -m spacy download en_core_web_sm

# 5. Install Playwright browsers (needed for JS-rendered sites)
playwright install chromium

# 6. Verify configuration
python3 main.py --mode status

# 7. Dry-run to validate everything works
python3 main.py --mode crawl --dry-run

# 8. Run your first crawl (today's date)
python3 main.py --mode crawl --date $(date +%Y-%m-%d)

# 9. Run the analysis pipeline
python3 main.py --mode analyze --all-stages

# 10. Check results
ls -la data/output/
```

---

## System Requirements

| Requirement | Specification |
|-------------|--------------|
| **OS** | macOS (Apple Silicon M2 Pro or later recommended) |
| **Python** | 3.12 or later |
| **RAM** | 16 GB minimum (10 GB pipeline budget) |
| **Disk** | 5 GB free minimum (monthly data ~2-4 GB) |
| **Network** | Stable internet connection |
| **Optional** | `coreutils` for GNU `timeout` (`brew install coreutils`) |

---

## Installation

### Step 1: Python Environment

```bash
# Verify Python version (3.12+ required)
python3 --version

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

The system uses 44+ Python packages. Key dependencies:

| Category | Packages |
|----------|----------|
| Crawling | httpx, beautifulsoup4, trafilatura, playwright, patchright |
| Korean NLP | kiwipiepy |
| English NLP | spacy |
| Embeddings | sentence-transformers, torch |
| Topics | bertopic, hdbscan |
| Time Series | statsmodels, prophet, ruptures |
| Storage | pyarrow, duckdb, sqlite-vec |

### Step 3: NLP Models

```bash
# spaCy English model
python3 -m spacy download en_core_web_sm

# Playwright browsers
playwright install chromium
```

Other models (SBERT, KoBERT, BERTopic) are downloaded automatically on first use by HuggingFace transformers.

### Step 4: Verify Installation

```bash
python3 main.py --mode status
```

Expected output:

```
============================================================
GlobalNews Crawling & Analysis System -- Status
============================================================

Configuration Files:
  sources.yaml:  FOUND (data/config/sources.yaml)
  pipeline.yaml: FOUND (data/config/pipeline.yaml)

  Sites: 44 total, 44 enabled
  Daily article estimate: ~6395
  Groups: A(5), B(4), C(3), D(7), E(12), F(6), G(7)

Data Directories:
  data/raw/:       EXISTS (0 files)
  data/processed/: MISSING (0 files)
  ...
```

### Step 5: Cron Setup (Optional, for daily automation)

```bash
# Edit PROJECT_DIR in the crontab template
nano config/crontab.txt

# Install cron jobs
(crontab -l 2>/dev/null; cat config/crontab.txt) | crontab -

# Verify
crontab -l
```

---

## Usage

### CLI Commands

The system is controlled through `main.py` with four modes.

#### Crawl Mode

Discovers URLs and extracts articles from all configured news sites.

```bash
# Crawl all enabled sites for today
python3 main.py --mode crawl

# Crawl a specific date
python3 main.py --mode crawl --date 2026-02-25

# Crawl specific sites only
python3 main.py --mode crawl --sites chosun,donga,yna

# Crawl specific groups only (A=Korean Major, E=English)
python3 main.py --mode crawl --groups A,E

# Dry run (validate config, show plan, no network requests)
python3 main.py --mode crawl --dry-run
```

Output: `data/raw/YYYY-MM-DD/all_articles.jsonl`

#### Analyze Mode

Runs the 8-stage NLP analysis pipeline on crawled articles.

```bash
# Run all 8 stages
python3 main.py --mode analyze --all-stages

# Run a specific stage (e.g., stage 3)
python3 main.py --mode analyze --stage 3

# Dry run (check dependencies, show plan)
python3 main.py --mode analyze --all-stages --dry-run
```

Output: Parquet files in `data/processed/`, `data/features/`, `data/analysis/`, `data/output/`

#### Full Mode

Runs crawl + all 8 analysis stages in sequence.

```bash
# Full pipeline for today
python3 main.py --mode full

# Full pipeline for a specific date
python3 main.py --mode full --date 2026-02-25

# Full pipeline dry run
python3 main.py --mode full --dry-run
```

#### Status Mode

Shows configuration summary and data inventory.

```bash
python3 main.py --mode status
```

### Common Options

| Flag | Description |
|------|-------------|
| `--mode` | Required. One of: `crawl`, `analyze`, `full`, `status` |
| `--date YYYY-MM-DD` | Target date (default: today) |
| `--sites s1,s2,...` | Comma-separated site IDs (default: all enabled) |
| `--groups A,B,...` | Comma-separated group letters (default: all) |
| `--stage N` | Specific analysis stage 1-8 (use with `--mode analyze`) |
| `--all-stages` | Run all 8 analysis stages |
| `--dry-run` | Validate without executing |
| `--log-level LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |
| `--version` | Show version |

### Automation Scripts

| Script | Schedule | Purpose |
|--------|----------|---------|
| `scripts/run_daily.sh` | Daily at 02:00 AM | Full pipeline with lock, health check, timeout |
| `scripts/run_weekly_rescan.sh` | Sundays at 01:00 AM | Validate adapter health and site structures |
| `scripts/archive_old_data.sh` | 1st of month at 03:00 AM | Compress and archive data older than 30 days |

---

## Directory Structure

```
GlobalNews-Crawling-AgenticWorkflow/
|
+-- main.py                              # CLI entry point
+-- requirements.txt                     # Python dependencies (44+ packages)
+-- pyproject.toml                       # Project metadata, tool config
|
+-- config/
|   +-- sources.yaml                     # Draft site list (44 sites, 7 groups)
|   +-- crontab.txt                      # Cron schedule template
|
+-- data/
|   +-- config/
|   |   +-- sources.yaml                 # Runtime site configuration (authoritative)
|   |   +-- pipeline.yaml               # Analysis pipeline configuration
|   +-- raw/                             # JSONL articles per date (gitignored)
|   |   +-- YYYY-MM-DD/
|   |       +-- all_articles.jsonl       # All articles for that date
|   |       +-- crawl_report.json        # Per-site crawl statistics
|   +-- processed/                       # Stage 1 output (gitignored)
|   |   +-- articles.parquet             # Preprocessed articles (12 columns)
|   +-- features/                        # Stage 2 output (gitignored)
|   |   +-- embeddings.parquet           # SBERT 384-dim embeddings
|   |   +-- tfidf.parquet                # TF-IDF vectors
|   |   +-- ner.parquet                  # Named entities
|   +-- analysis/                        # Stages 3-6 output (gitignored)
|   |   +-- article_analysis.parquet     # Sentiment, emotion, STEEPS
|   |   +-- topics.parquet               # BERTopic topics
|   |   +-- networks.parquet             # Co-occurrence networks
|   |   +-- timeseries.parquet           # Time series decomposition
|   |   +-- cross_analysis.parquet       # Granger, PCMCI, cross-lingual
|   +-- output/                          # Final output (gitignored)
|   |   +-- signals.parquet              # 5-layer signal classification (12 cols)
|   |   +-- analysis.parquet             # Merged analysis (21 cols)
|   |   +-- index.sqlite                 # FTS5 + vector search index
|   +-- models/                          # Cached NLP models (gitignored)
|   +-- logs/                            # Structured JSON logs (gitignored)
|   |   +-- crawl.log                    # Crawl events
|   |   +-- analysis.log                 # Analysis events
|   |   +-- errors.log                   # All errors
|   |   +-- daily/                       # Daily pipeline logs
|   |   +-- weekly/                      # Weekly rescan reports
|   |   +-- alerts/                      # Failure alerts
|   |   +-- cron/                        # Cron output logs
|   +-- archive/                         # Compressed old data (gitignored)
|   +-- dedup.sqlite                     # Deduplication database (gitignored)
|
+-- src/
|   +-- config/
|   |   +-- constants.py                 # All project-wide constants
|   +-- crawling/
|   |   +-- pipeline.py                  # Crawl orchestrator
|   |   +-- network_guard.py             # Resilient HTTP client (5 retries)
|   |   +-- url_discovery.py             # 3-tier URL discovery (RSS/Sitemap/DOM)
|   |   +-- article_extractor.py         # Multi-library extraction chain
|   |   +-- dedup.py                     # 3-level dedup (URL/Title/SimHash)
|   |   +-- anti_block.py               # 6-tier escalation engine
|   |   +-- block_detector.py            # 7-type block diagnosis
|   |   +-- retry_manager.py             # 4-level retry (90 max attempts)
|   |   +-- circuit_breaker.py           # Per-site circuit breaker
|   |   +-- ua_manager.py               # 4-tier UA rotation (61+ agents)
|   |   +-- session_manager.py           # Cookie/header management
|   |   +-- stealth_browser.py           # Playwright/Patchright stealth
|   |   +-- url_normalizer.py            # URL normalization
|   |   +-- contracts.py                 # RawArticle data contract
|   |   +-- crawler.py                   # JSONL writer, crawl state
|   |   +-- crawl_report.py              # Statistics report generator
|   |   +-- adapters/                    # 44 site-specific adapters
|   |       +-- base_adapter.py          # Abstract base class
|   |       +-- kr_major/                # Groups A+B+C: 11 Korean sites
|   |       +-- kr_tech/                 # Group D: 8 Korean IT/science
|   |       +-- english/                 # Group E: 12 English sites
|   |       +-- multilingual/            # Groups F+G: 13 Asia-Pacific/Europe
|   +-- analysis/
|   |   +-- pipeline.py                  # 8-stage orchestrator
|   |   +-- stage1_preprocessing.py      # Kiwi + spaCy tokenization
|   |   +-- stage2_features.py           # SBERT, TF-IDF, NER, KeyBERT
|   |   +-- stage3_article_analysis.py   # Sentiment, emotion, STEEPS
|   |   +-- stage4_aggregation.py        # BERTopic, HDBSCAN, community
|   |   +-- stage5_timeseries.py         # STL, PELT, Kleinberg, Prophet
|   |   +-- stage6_cross_analysis.py     # Granger, PCMCI, network analysis
|   |   +-- stage7_signals.py            # 5-Layer L1-L5 classification
|   |   +-- stage8_output.py             # Parquet merge + SQLite index
|   +-- storage/
|   |   +-- parquet_writer.py            # Schema-validated ZSTD Parquet
|   |   +-- sqlite_builder.py            # FTS5 + sqlite-vec index
|   +-- utils/
|       +-- config_loader.py             # YAML config loading/validation
|       +-- error_handler.py             # Exception hierarchy, circuit breaker
|       +-- logging_config.py            # Structured JSON logging
|       +-- self_recovery.py             # Lock files, health checks, checkpoints
|
+-- scripts/
|   +-- run_daily.sh                     # Daily cron wrapper (4-hour timeout)
|   +-- run_weekly_rescan.sh             # Weekly adapter health check
|   +-- archive_old_data.sh              # Monthly data archival
|
+-- testing/
|   +-- validate_e2e.py                  # Structural validation (13 checks)
|   +-- run_e2e_test.py                  # Live E2E test runner
|   +-- e2e-test-report.md               # Latest validation report
|
+-- docs/
    +-- operations-guide.md              # Daily ops, cron, adding sites
    +-- architecture-guide.md            # System design, data flow, extension
```

---

## Configuration

### sources.yaml

The authoritative site configuration at `data/config/sources.yaml`. Each site entry has this structure:

```yaml
  chosun:                           # Site ID (unique key, used in adapters)
    name: "Chosun Ilbo"             # Human-readable name
    url: "https://www.chosun.com"   # Canonical base URL
    region: "kr"                    # Geographic region (kr, us, uk, cn, jp, ...)
    language: "ko"                  # ISO 639-1 language code
    group: "A"                      # Site group (A-G)
    crawl:
      primary_method: "rss"         # Primary URL discovery (rss, sitemap, api, playwright, dom)
      fallback_methods:             # Ordered fallback chain
        - "sitemap"
        - "dom"
      rss_url: "http://www.chosun.com/site/data/rss/rss.xml"
      sitemap_url: "/sitemap.xml"
      rate_limit_seconds: 5         # Minimum delay between requests
      crawl_delay_mandatory: null   # robots.txt Crawl-delay (null = not specified)
      max_requests_per_hour: 720    # Safety cap
      jitter_seconds: 0             # Random jitter added to delay
    anti_block:
      ua_tier: 2                    # UA rotation tier (1=bot, 2=desktop, 3=diverse, 4=Patchright)
      default_escalation_tier: 1    # Starting anti-block tier (1-6)
      bot_block_level: "MEDIUM"     # Expected blocking (LOW, MEDIUM, HIGH)
      requires_proxy: false         # Whether a proxy is needed
      proxy_region: null            # Required proxy region
    extraction:
      paywall_type: "none"          # none, soft-metered, hard
      rendering_required: false     # Whether JS rendering is needed
      charset: "utf-8"             # Character encoding
    meta:
      enabled: true                 # Whether to crawl this site
      daily_article_estimate: 200   # Expected articles per day
      difficulty: "Medium"          # Easy, Medium, Hard, Extreme
```

### pipeline.yaml

Analysis pipeline configuration at `data/config/pipeline.yaml`. Key settings:

```yaml
pipeline:
  global:
    max_memory_gb: 10               # Hard memory limit (abort above this)
    gc_between_stages: true         # Force garbage collection between stages
    parquet_compression: "zstd"     # Compression algorithm
    parquet_compression_level: 3    # ZSTD compression level
    batch_size_default: 500         # Default article batch size

  stages:
    stage_1_preprocessing:
      enabled: true
      memory_limit_gb: 1.5
      timeout_seconds: 1800
      models:
        - name: "kiwipiepy"
          singleton: true           # Must be loaded once (760 MB)
    # ... stages 2 through 8 follow the same structure
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `GLOBALNEWS_LOG_LEVEL` | Override log level | `INFO` |
| `PROXY_URL` | HTTP proxy for Tier 5 escalation | None |
| `PROXY_USERNAME` | Proxy authentication | None |
| `PROXY_PASSWORD` | Proxy authentication | None |

Proxy credentials should be stored securely (e.g., macOS Keychain or `.env` file with restricted permissions).

### Site Groups

| Group | Region | Sites | Languages |
|-------|--------|-------|-----------|
| A | Korean Major Dailies | Chosun, JoongAng, Dong-A, Hankyoreh, Yonhap | ko |
| B | Korean Economy | MK, Hankyung, FNNews, Money Today | ko |
| C | Korean Niche | Kookmin, NoCut, OhMyNews | ko |
| D | Korean IT/Science | 38North, Bloter, ETNews, iRobot, ScienceTimes, TechNeedle, ZDNet | ko |
| E | English-Language | Bloomberg, BuzzFeed, CNN, FT, HuffPost, LA Times, MarketWatch, National Post, NYT, VOA Korea, WSJ, + others | en |
| F | Asia-Pacific | Global Times, People's Daily, SCMP, Taiwan News, The Hindu, Yomiuri | zh, ja, en |
| G | Europe/Middle East | Al Jazeera, Arab News, Bild, Israel Hayom, Le Monde, Moscow Times, The Sun | ar, de, fr, he, en |

---

## Analysis Pipeline

The 8-stage analysis pipeline processes raw JSONL articles into structured analytical datasets.

| Stage | Name | Techniques | Output |
|-------|------|-----------|--------|
| 1 | Preprocessing | Kiwi morphemes (ko), spaCy lemmas (en), langdetect, normalization | `articles.parquet` |
| 2 | Feature Extraction | SBERT embeddings, TF-IDF, NER, KeyBERT keywords | `embeddings.parquet`, `tfidf.parquet`, `ner.parquet` |
| 3 | Article Analysis | Sentiment, emotion, STEEPS classification, stance detection | `article_analysis.parquet` |
| 4 | Aggregation | BERTopic, HDBSCAN clustering, NMF/LDA, community detection | `topics.parquet`, `networks.parquet` |
| 5 | Time Series | STL decomposition, Kleinberg bursts, PELT changepoint, Prophet, wavelet | `timeseries.parquet` |
| 6 | Cross Analysis | Granger causality, PCMCI, co-occurrence, cross-lingual topic alignment | `cross_analysis.parquet` |
| 7 | Signal Classification | 5-Layer L1-L5 hierarchy, novelty detection (LOF/IF), singularity scoring | `signals.parquet` |
| 8 | Data Output | Parquet merge, SQLite FTS5/vec indexing | `analysis.parquet`, `index.sqlite` |

---

## 5-Layer Signal Classification

The system classifies detected signals into 5 temporal persistence layers:

| Layer | Name | Duration | Characteristics |
|-------|------|----------|-----------------|
| L1 | Fad | < 1 week | Spike-and-decay, single source, volume z-score > 3.0 |
| L2 | Short-term | 1-4 weeks | 2+ sources, sustained above baseline for 7+ days |
| L3 | Mid-term | 1-6 months | Structural change indicators, changepoint significance > 0.8 |
| L4 | Long-term | 6+ months | Institutional adoption, embedding drift > 0.3, wavelet period > 90d |
| L5 | Singularity | Unprecedented | Composite score >= 0.65, 2-of-3 independent detection pathways |

The **Singularity Composite Score** uses 7 weighted indicators:

```
Score = 0.20 * OOD_score
      + 0.15 * changepoint_score
      + 0.20 * cross_domain_score
      + 0.15 * BERTrend_score
      + 0.10 * entropy_change
      + 0.10 * novelty_score
      + 0.10 * network_anomaly
```

---

## Troubleshooting

### Issue 1: Site Blocking Crawl Requests (R1)

**Symptoms**: 403 status codes, empty article bodies, CAPTCHA pages in HTML.

**Resolution**:
1. Check which block type is detected: `grep "block_detected" data/logs/crawl.log | tail -20`
2. Increase the site's `ua_tier` in `data/config/sources.yaml` (1 -> 2 -> 3)
3. Increase `default_escalation_tier` (1 -> 2 -> 3)
4. Increase `rate_limit_seconds` (5 -> 10 -> 15)
5. If geo-blocked, enable proxy: `requires_proxy: true` with `proxy_region`
6. For persistent blocks, check `logs/tier6-escalation/` for detailed diagnostics

### Issue 2: BERTopic Producing Low-Quality Topics (R2)

**Symptoms**: Topics with incoherent keywords, too many or too few clusters.

**Resolution**:
1. Verify Korean preprocessing is working: check `articles.parquet` for tokenized fields
2. Ensure Kiwi is loaded as singleton (check for "Kiwi singleton" in logs)
3. Adjust `min_topic_size` in `data/config/pipeline.yaml` stage 4 settings
4. Minimum 50 articles required for topic modeling (`MIN_ARTICLES_FOR_TOPICS` in constants)

### Issue 3: Memory Exhaustion (R3)

**Symptoms**: Process killed by OS, "MemoryLimitError" in logs, system becomes unresponsive.

**Resolution**:
1. Check which stage caused OOM: `grep "peak_memory" data/logs/analysis.log`
2. Reduce `SBERT_BATCH_SIZE` in `src/config/constants.py` (default 64, try 32)
3. Reduce `DEFAULT_BATCH_SIZE` (default 500, try 250)
4. Ensure `gc_between_stages: true` in `data/config/pipeline.yaml`
5. Close other memory-intensive applications during pipeline runs
6. Monitor with: `python3 -c "import resource; print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 'GB')"`

### Issue 4: Site Structure Changed, Adapter Broken (R4)

**Symptoms**: 0 articles from a previously working site, CSS selector errors in logs.

**Resolution**:
1. Run weekly rescan: `scripts/run_weekly_rescan.sh`
2. Check the rescan report: `cat data/logs/weekly/rescan-$(date +%Y-%m-%d).md`
3. Visit the site in a browser and inspect current HTML structure
4. Update CSS selectors in the site's adapter file (e.g., `src/crawling/adapters/kr_major/chosun.py`)
5. Test the fix: `python3 main.py --mode crawl --sites chosun --date $(date +%Y-%m-%d)`

### Issue 5: Crawling Mistaken for DDoS Attack (R5)

**Symptoms**: IP banned across multiple sites, ISP warning.

**Resolution**:
1. Immediately stop all crawling: kill any running `main.py` processes
2. Increase `rate_limit_seconds` for affected sites (minimum 10s)
3. Ensure `Crawl-delay` from robots.txt is being respected
4. Use a transparent User-Agent (T1 tier includes Googlebot-compatible UA)
5. Consider reducing `MAX_REQUESTS_PER_HOUR` per site

### Issue 6: Analysis Results Quality Issues (R6)

**Symptoms**: Sentiment always neutral, wrong language detection, missing entities.

**Resolution**:
1. Check Stage 1 output: `python3 -c "import pyarrow.parquet as pq; t = pq.read_table('data/processed/articles.parquet'); print(t.schema); print(t.num_rows)"`
2. Verify language detection accuracy in logs
3. Ensure spaCy model is installed: `python3 -m spacy validate`
4. Check if SBERT model downloaded correctly: look for download errors in Stage 2 logs

### Issue 7: Disk Space Running Low (R9)

**Symptoms**: "Insufficient disk space" health check failure, pipeline aborts.

**Resolution**:
1. Check current usage: `du -sh data/*/`
2. Run archival immediately: `scripts/archive_old_data.sh`
3. If urgent, archive with shorter window: `scripts/archive_old_data.sh --days 14`
4. Manually remove old logs: `find data/logs/ -name "*.log" -mtime +30 -delete`
5. Check archive directory: `du -sh data/archive/`

### Issue 8: Python/Dependency Version Conflicts (R10)

**Symptoms**: ImportError, version mismatch warnings, "No module named X".

**Resolution**:
1. Verify Python version: `python3 --version` (must be 3.12+)
2. Verify virtual environment is active: `which python3` should point to `.venv/bin/python3`
3. Reinstall all dependencies: `pip install -r requirements.txt --force-reinstall`
4. Run health check: `python3 -m src.utils.self_recovery --health-check`
5. Check for specific failures: `python3 -c "import yaml; import pyarrow; import torch; print('OK')"`

### Issue 9: Concurrent Execution Conflicts (Lock Issues)

**Symptoms**: "Lock acquisition failed", two pipeline instances running simultaneously.

**Resolution**:
1. Check lock status: `python3 -m src.utils.self_recovery --check-lock daily`
2. If the lock is stale (process no longer running): `python3 -m src.utils.self_recovery --force-release-lock daily`
3. Stale lock threshold is 4 hours -- locks older than this are automatically detected
4. To check if a pipeline process is actually running: `ps aux | grep main.py`

### Issue 10: Pipeline Exceeding 4-Hour Timeout

**Symptoms**: "Pipeline timed out" in daily log, alerts generated.

**Resolution**:
1. Check which stage is slowest: review `data/logs/analysis.log` for stage timing
2. Reduce scope: crawl fewer groups with `--groups A,B,E` in `scripts/run_daily.sh`
3. Reduce batch sizes in `data/config/pipeline.yaml`
4. Skip non-essential stages by setting `enabled: false` in pipeline config
5. Increase timeout if needed: edit `PIPELINE_TIMEOUT=14400` in `scripts/run_daily.sh`
6. Use checkpoint resume: `python3 main.py --mode analyze --stage N` to resume from last completed stage

---

## Further Reading

| Document | Description |
|----------|-------------|
| [Operations Guide](operations-guide.md) | Daily monitoring, cron jobs, adding sites, handling failures |
| [Architecture Guide](architecture-guide.md) | System design, module interfaces, data flow, extension points |
| [E2E Test Report](../testing/e2e-test-report.md) | Latest structural validation results (13 checks, 44 adapters, 8 stages) |
| [Development Guide](../DEVELOPMENT.md) | Development setup, testing, debugging, contributing |

---

## License

MIT License. See `pyproject.toml` for details.
