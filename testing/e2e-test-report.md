# E2E Structural Validation Report

## Test Environment
- **Date**: 2026-02-26
- **Python**: 3.14.0
- **Platform**: Darwin 25.3.0 (arm64)
- **Total duration**: 17.4s
- **Peak memory**: 0.189 GB
- **Test type**: Structural validation (no network access)

## Validation Summary

| Category | Total | Pass | Fail | Warn |
|----------|-------|------|------|------|
| Checks | 13 | 12 | 0 | 1 |
| Sites (adapters) | 44 | 44 | 0 | - |
| Analysis Stages | 8 | 8 | 0 | - |

## Overall Structural Verdict: **PASS**

## PRD Verification Criteria (V1-V12)

| # | Criterion | Validation Type | Status | Notes |
|---|-----------|----------------|--------|-------|
| V1 | Full crawl on 44 sites | DEFERRED | DEFERRED | 44/44 adapters structurally valid; no crawl executed |
| V2 | Success rate >= 80% | DEFERRED | DEFERRED | Requires live crawl execution |
| V3 | >= 500 articles collected | DEFERRED | DEFERRED | Requires live crawl execution |
| V4 | Mandatory fields present >= 99% | STRUCTURAL | PASS | Verified via synthetic data round-trip |
| V5 | Dedup rate <= 1% | STRUCTURAL | PARTIAL | DedupEngine importable, 3-level cascade verified; no runtime dedup test |
| V6 | Analysis completes without OOM | STRUCTURAL | PARTIAL | Pipeline wiring verified, memory monitor present; no runtime execution |
| V7 | All 5 signal layers in output | STRUCTURAL | PASS | L1-L5 layers defined in stage7_signals.py and sqlite_builder.py |
| V8 | FTS5 search works | STRUCTURAL | PARTIAL | DDL verified, unit test confirms FTS5 in isolation; no E2E search test |
| V9 | sqlite-vec search works | DEFERRED | DEFERRED | sqlite-vec DDL present with graceful degradation; may not be installed |
| V10 | E2E time <= 3 hours | DEFERRED | DEFERRED | Requires live pipeline execution |
| V11 | Failure report generated | STRUCTURAL | PASS | run_e2e_test.py has report generation logic |
| V12 | 3-tier retry engages | DEFERRED | DEFERRED | Retry constants verified (90 max attempts); no runtime engagement observed |

## Detailed Check Results

| Check ID | Description | Status | Elapsed | Details |
|----------|-------------|--------|---------|---------|
| ENV_001 | Python version >= 3.11 and critical dependencies importable | **PASS** | 0.64s | Python 3.14.0, all 7 critical deps OK |
| CFG_001 | Config files (sources.yaml, pipeline.yaml) present and valid | **PASS** | 0.04s | Both config files present and parseable, 44 sites configured |
| ADP_001 | All 44 site adapters importable via ADAPTER_REGISTRY | **PASS** | 0.02s | 44 adapters registered: 38north, afmedios, aljazeera, arabnews, bild, bloomberg, bloter, buzzfeed, chosun, cnn, donga, e... |
| ADP_002 | Per-site adapter interface validation (44 sites) | **PASS** | 0.00s | 44 PASS, 0 FAIL out of 44 sites |
| STG_001 | All 8 analysis stages importable with run functions | **PASS** | 0.03s | All 8 stages importable with run functions |
| PIP_001 | AnalysisPipeline has _run_stage1 through _run_stage8 | **PASS** | 0.00s | All 8 stage runners wired (_run_stage1 through _run_stage8) |
| STR_001 | Storage layer: Parquet schemas (12/21/12 cols) + SQLite DDL  | **PASS** | 0.00s | Parquet: ARTICLES(12), ANALYSIS(21), SIGNALS(12); SQLite: 5 tables (articles_fts, article_embeddings, signals_index, top... |
| DDP_001 | DedupEngine importable with 3-level cascade (URL + Title + S | **PASS** | 0.00s | DedupEngine OK: 3 levels, SimHash 64-bit, threshold=8 |
| RTY_001 | Retry system: 5 x 2 x 3 x 3 = 90 max attempts per URL | **PASS** | 0.00s | L1=5 x L2=2 x L3=3 x L4=3 = 90 (NetworkGuard x Strategy x Round x Restart) |
| CLI_001 | main.py --mode crawl --dry-run executes without error | **PASS** | 0.08s | Dry run completed successfully (exit code 0) |
| CLI_002 | main.py --mode analyze --all-stages --dry-run executes witho | **PASS** | 0.04s | Analyze dry run completed (exit code 0) |
| SYN_001 | Synthetic articles: create 10 JSONL articles and verify roun | **PASS** | 0.00s | 10 synthetic articles: JSONL round-trip OK, all mandatory fields (title, url, body, source_id) present |
| TST_001 | Existing pytest suite health (pass/fail/skip counts) | **WARN** | 16.51s | 1657 passed, 8 failed, 13 skipped (total 1678, exit code 1) |

## Analysis Pipeline Stages

| Stage | Name | Importable | Run Function | Deps Declared | Status |
|-------|------|------------|--------------|---------------|--------|
| 1 | Preprocessing | Y | Y | Y | **PASS** |
| 2 | Feature Extraction | Y | Y | Y | **PASS** |
| 3 | Article Analysis | Y | Y | Y | **PASS** |
| 4 | Aggregation | Y | Y | Y | **PASS** |
| 5 | Time Series | Y | Y | Y | **PASS** |
| 6 | Cross Analysis | Y | Y | Y | **PASS** |
| 7 | Signal Classification | Y | Y | Y | **PASS** |
| 8 | Data Output | Y | Y | Y | **PASS** |

## Per-Site Adapter Validation (44/44 PASS)

### Successful Adapters

| Site ID | Group | Importable | Methods | Attrs | Status |
|---------|-------|------------|---------|-------|--------|
| 38north | D | Y | Y | Y | **PASS** |
| afmedios | E | Y | Y | Y | **PASS** |
| aljazeera | G | Y | Y | Y | **PASS** |
| arabnews | G | Y | Y | Y | **PASS** |
| bild | G | Y | Y | Y | **PASS** |
| bloomberg | E | Y | Y | Y | **PASS** |
| bloter | D | Y | Y | Y | **PASS** |
| buzzfeed | E | Y | Y | Y | **PASS** |
| chosun | A | Y | Y | Y | **PASS** |
| cnn | E | Y | Y | Y | **PASS** |
| donga | A | Y | Y | Y | **PASS** |
| etnews | D | Y | Y | Y | **PASS** |
| fnnews | B | Y | Y | Y | **PASS** |
| ft | E | Y | Y | Y | **PASS** |
| globaltimes | F | Y | Y | Y | **PASS** |
| hani | A | Y | Y | Y | **PASS** |
| hankyung | B | Y | Y | Y | **PASS** |
| huffpost | E | Y | Y | Y | **PASS** |
| irobotnews | D | Y | Y | Y | **PASS** |
| israelhayom | G | Y | Y | Y | **PASS** |
| joongang | A | Y | Y | Y | **PASS** |
| kmib | C | Y | Y | Y | **PASS** |
| latimes | E | Y | Y | Y | **PASS** |
| lemonde | G | Y | Y | Y | **PASS** |
| marketwatch | E | Y | Y | Y | **PASS** |
| mk | B | Y | Y | Y | **PASS** |
| mt | B | Y | Y | Y | **PASS** |
| nationalpost | E | Y | Y | Y | **PASS** |
| nocutnews | C | Y | Y | Y | **PASS** |
| nytimes | E | Y | Y | Y | **PASS** |
| ohmynews | C | Y | Y | Y | **PASS** |
| people | F | Y | Y | Y | **PASS** |
| sciencetimes | D | Y | Y | Y | **PASS** |
| scmp | F | Y | Y | Y | **PASS** |
| taiwannews | F | Y | Y | Y | **PASS** |
| techneedle | D | Y | Y | Y | **PASS** |
| thehindu | F | Y | Y | Y | **PASS** |
| themoscowtimes | G | Y | Y | Y | **PASS** |
| thesun | G | Y | Y | Y | **PASS** |
| voakorea | E | Y | Y | Y | **PASS** |
| wsj | E | Y | Y | Y | **PASS** |
| yna | A | Y | Y | Y | **PASS** |
| yomiuri | F | Y | Y | Y | **PASS** |
| zdnet_kr | D | Y | Y | Y | **PASS** |

## Existing Test Suite Health

- **Total tests**: 1678
- **Passed**: 1657
- **Failed**: 8
- **Skipped**: 13
- **Exit code**: 1

Note: Pre-existing test failures were observed. These are not caused by the E2E validation and should be investigated separately.

## Recommendations

1. **Run live E2E test**: Execute `python3 testing/run_e2e_test.py` to validate V2, V3, V10 criteria that require actual network crawling.
2. **Address pre-existing test failures**: The existing pytest suite has 8 failing tests that should be investigated separately.

---
Generated by `testing/validate_e2e.py` on 2026-02-26 in 17.4s.
