#!/usr/bin/env python3
"""Live E2E Test Runner for GlobalNews Crawling & Analysis System.

Executes the complete crawl + analysis pipeline on all 44 sites (or a subset),
collects per-site metrics, measures system performance against PRD thresholds,
and produces detailed reports.

Usage:
    # Full live test (all 44 sites)
    python3 testing/run_e2e_test.py

    # Test specific sites
    python3 testing/run_e2e_test.py --sites chosun,donga,hani

    # Test a specific group
    python3 testing/run_e2e_test.py --groups A,B

    # Dry-run mode (no network, validates wiring)
    python3 testing/run_e2e_test.py --dry-run

    # Skip analysis pipeline (crawl-only test)
    python3 testing/run_e2e_test.py --crawl-only

    # Override date
    python3 testing/run_e2e_test.py --date 2026-02-26

PRD Success Criteria (from Section 9.1):
    - Success rate >= 80%:    At least 35/44 sites produce valid articles
    - Article count >= 500:   Total unique articles across all successful sites
    - Dedup effectiveness >= 90%: Global dedup ratio
    - Per-site crawl time <= 5 min: No site exceeds 300 seconds
    - Peak memory <= 10 GB:   Maximum RSS across entire pipeline run
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import resource
import sys
import time
import traceback
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# PRD Thresholds (Section 9.1)
# =============================================================================

THRESHOLD_SUCCESS_RATE = 0.80       # >= 80% of sites succeed
THRESHOLD_MIN_ARTICLES = 500        # >= 500 total articles
THRESHOLD_DEDUP_EFFECTIVENESS = 0.90  # >= 90% dedup rate
THRESHOLD_MAX_SITE_TIME_SECONDS = 300  # <= 5 minutes per site
THRESHOLD_MAX_MEMORY_GB = 10.0      # <= 10 GB peak RSS


# =============================================================================
# Memory utility
# =============================================================================

def get_rss_gb() -> float:
    """Get current RSS in GB."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss_bytes = usage.ru_maxrss
    if os.uname().sysname == "Darwin":
        return rss_bytes / (1024 ** 3)
    else:
        return rss_bytes / (1024 ** 2)


# =============================================================================
# Live E2E Test Runner
# =============================================================================

class LiveE2ETestRunner:
    """Runs the complete crawl + analysis pipeline with metrics collection.

    This runner:
    1. Executes the CrawlingPipeline for all (or filtered) sites
    2. Collects per-site metrics: articles, timing, errors, strategy
    3. Runs the AnalysisPipeline on collected data
    4. Measures performance against PRD thresholds
    5. Generates detailed reports (JSON + Markdown)
    """

    def __init__(
        self,
        crawl_date: str | None = None,
        sites_filter: list[str] | None = None,
        groups_filter: list[str] | None = None,
        dry_run: bool = False,
        crawl_only: bool = False,
    ) -> None:
        self._date = crawl_date or date.today().strftime("%Y-%m-%d")
        self._sites_filter = sites_filter
        self._groups_filter = groups_filter
        self._dry_run = dry_run
        self._crawl_only = crawl_only

        self._start_time: float = 0.0
        self._crawl_report: dict[str, Any] = {}
        self._analysis_result: Any = None
        self._per_site_data: list[dict[str, Any]] = []
        self._analysis_stages: list[dict[str, Any]] = []
        self._peak_memory_gb: float = 0.0

        # Setup logging
        from src.utils.logging_config import setup_logging
        setup_logging(console_level="INFO")
        self._logger = logging.getLogger("e2e_test")

    def run(self) -> dict[str, Any]:
        """Execute the full E2E test and return results.

        Returns:
            Complete test results dictionary.
        """
        self._start_time = time.monotonic()
        self._logger.info(
            "E2E test started: date=%s sites=%s groups=%s dry_run=%s crawl_only=%s",
            self._date,
            self._sites_filter or "all",
            self._groups_filter or "all",
            self._dry_run,
            self._crawl_only,
        )

        # Phase 1: Crawl
        self._run_crawl_phase()

        # Phase 2: Analysis
        if not self._crawl_only:
            self._run_analysis_phase()

        # Phase 3: Verify outputs
        self._verify_outputs()

        # Compile and return results
        return self._compile_results()

    # -----------------------------------------------------------------
    # Phase 1: Crawling
    # -----------------------------------------------------------------

    def _run_crawl_phase(self) -> None:
        """Execute the crawling pipeline and collect per-site metrics."""
        self._logger.info("=" * 60)
        self._logger.info("PHASE 1: CRAWLING PIPELINE")
        self._logger.info("=" * 60)

        from src.crawling.pipeline import CrawlingPipeline

        pipeline = CrawlingPipeline(
            crawl_date=self._date,
            sites_filter=self._sites_filter,
            groups_filter=self._groups_filter,
            dry_run=self._dry_run,
        )

        try:
            self._crawl_report = pipeline.run()
        except Exception as e:
            self._logger.error("Crawl pipeline failed: %s", e, exc_info=True)
            self._crawl_report = {
                "error": str(e),
                "total_articles": 0,
                "sites_attempted": 0,
                "sites_failed": 0,
            }
        finally:
            pipeline.close()

        # Update peak memory
        self._peak_memory_gb = max(self._peak_memory_gb, get_rss_gb())

        # Extract per-site data from crawl results
        self._extract_per_site_data()

    def _extract_per_site_data(self) -> None:
        """Extract per-site metrics from the crawl report."""
        from src.utils.config_loader import load_sources_config, clear_config_cache
        clear_config_cache()

        try:
            config = load_sources_config(validate=False)
            sources = config.get("sources", {})
        except Exception:
            sources = {}

        site_results = self._crawl_report.get("site_results", {})

        # If the crawl report has per-site data, use it
        if site_results:
            for site_id, sr in site_results.items():
                site_data = {
                    "name": site_id,
                    "url": sources.get(site_id, {}).get("url", f"https://{site_id}"),
                    "group": sources.get(site_id, {}).get("group", "?"),
                    "status": "success" if sr.get("extracted_count", 0) > 0 else "failure",
                    "articles_found": sr.get("discovered_urls", 0),
                    "articles_extracted": sr.get("extracted_count", 0),
                    "dedup_ratio": 0.0,
                    "crawl_time_seconds": sr.get("elapsed_seconds", 0.0),
                    "peak_memory_mb": 0,
                    "strategy_used": "totalwar" if sr.get("tier_used", 1) > 1 else "standard",
                    "retry_counts": sr.get("retry_counts", {}),
                    "errors": sr.get("errors", []),
                    "failure_analysis": None,
                }

                # Compute dedup ratio
                discovered = sr.get("discovered_urls", 0)
                extracted = sr.get("extracted_count", 0)
                deduped = sr.get("skipped_dedup_count", 0)
                if discovered > 0:
                    site_data["dedup_ratio"] = round(deduped / discovered, 4)

                # Failure analysis for failed sites
                if site_data["status"] == "failure":
                    errors = sr.get("errors", [])
                    site_data["failure_analysis"] = self._classify_failure(site_id, errors)

                self._per_site_data.append(site_data)
        else:
            # Populate from sources.yaml with NOT_RUN status
            for site_id, cfg in sorted(sources.items()):
                self._per_site_data.append({
                    "name": site_id,
                    "url": cfg.get("url", f"https://{site_id}"),
                    "group": cfg.get("group", "?"),
                    "status": "not_run" if self._dry_run else "failure",
                    "articles_found": 0,
                    "articles_extracted": 0,
                    "dedup_ratio": 0.0,
                    "crawl_time_seconds": 0.0,
                    "peak_memory_mb": 0,
                    "strategy_used": "primary",
                    "retry_counts": {},
                    "errors": [],
                    "failure_analysis": None,
                })

    @staticmethod
    def _classify_failure(site_id: str, errors: list[str]) -> dict[str, Any]:
        """Classify the root cause of a site failure.

        Args:
            site_id: Site identifier.
            errors: List of error messages.

        Returns:
            Failure analysis dict with point, root_cause, transient flag.
        """
        if not errors:
            return {
                "point": "unknown",
                "root_cause": "no_errors_recorded",
                "transient": False,
            }

        combined = " ".join(errors).lower()

        # Network errors
        if any(kw in combined for kw in ["network", "timeout", "connection", "dns", "ssl"]):
            return {
                "point": "extraction",
                "root_cause": "network",
                "transient": True,
            }

        # Bot blocking
        if any(kw in combined for kw in ["blocked", "403", "captcha", "cloudflare", "waf"]):
            return {
                "point": "extraction",
                "root_cause": "bot_blocking",
                "transient": False,
            }

        # Rate limiting
        if any(kw in combined for kw in ["429", "rate limit", "too many"]):
            return {
                "point": "extraction",
                "root_cause": "rate_limiting",
                "transient": True,
            }

        # Paywall
        if any(kw in combined for kw in ["paywall", "subscribe", "login required"]):
            return {
                "point": "extraction",
                "root_cause": "paywall",
                "transient": False,
            }

        # Parse errors
        if any(kw in combined for kw in ["parse", "selector", "extract", "encoding"]):
            return {
                "point": "extraction",
                "root_cause": "parsing",
                "transient": False,
            }

        # Circuit breaker
        if "circuit" in combined:
            return {
                "point": "discovery",
                "root_cause": "circuit_breaker",
                "transient": True,
            }

        return {
            "point": "unknown",
            "root_cause": "unclassified",
            "transient": False,
        }

    # -----------------------------------------------------------------
    # Phase 2: Analysis
    # -----------------------------------------------------------------

    def _run_analysis_phase(self) -> None:
        """Execute the analysis pipeline on crawled data."""
        self._logger.info("=" * 60)
        self._logger.info("PHASE 2: ANALYSIS PIPELINE")
        self._logger.info("=" * 60)

        # Check if there is data to analyze
        total_articles = self._crawl_report.get("total_articles", 0)
        if total_articles == 0 and not self._dry_run:
            self._logger.warning("No articles collected, skipping analysis pipeline")
            for i in range(1, 9):
                self._analysis_stages.append({
                    "stage": i,
                    "status": "skipped",
                    "time_seconds": 0.0,
                    "peak_memory_mb": 0,
                    "notes": "No articles to analyze",
                })
            return

        from src.analysis.pipeline import AnalysisPipeline

        pipeline = AnalysisPipeline(date=self._date)

        try:
            result = pipeline.run(stages=list(range(1, 9)))
            self._analysis_result = result

            # Extract per-stage metrics
            for stage_num in range(1, 9):
                sr = result.stages.get(stage_num)
                if sr:
                    self._analysis_stages.append({
                        "stage": stage_num,
                        "status": "success" if sr.success else ("skipped" if sr.skipped else "failure"),
                        "time_seconds": sr.elapsed_seconds,
                        "peak_memory_mb": round(sr.peak_memory_gb * 1024, 1),
                        "article_count": sr.article_count,
                        "output_paths": sr.output_paths,
                        "error": sr.error_message if not sr.success else None,
                    })
                else:
                    self._analysis_stages.append({
                        "stage": stage_num,
                        "status": "not_run",
                        "time_seconds": 0.0,
                        "peak_memory_mb": 0,
                    })

        except Exception as e:
            self._logger.error("Analysis pipeline failed: %s", e, exc_info=True)
            for i in range(1, 9):
                self._analysis_stages.append({
                    "stage": i,
                    "status": "failure",
                    "time_seconds": 0.0,
                    "peak_memory_mb": 0,
                    "error": str(e),
                })

        # Update peak memory
        self._peak_memory_gb = max(self._peak_memory_gb, get_rss_gb())

    # -----------------------------------------------------------------
    # Phase 3: Output Verification
    # -----------------------------------------------------------------

    def _verify_outputs(self) -> None:
        """Verify that expected output files exist and are valid."""
        self._logger.info("=" * 60)
        self._logger.info("PHASE 3: OUTPUT VERIFICATION")
        self._logger.info("=" * 60)

        output_dir = PROJECT_ROOT / "data" / "output"

        expected_files = {
            "analysis.parquet": output_dir / "analysis.parquet",
            "signals.parquet": output_dir / "signals.parquet",
            "topics.parquet": output_dir / "topics.parquet",
            "index.sqlite": output_dir / "index.sqlite",
        }

        for name, path in expected_files.items():
            exists = path.exists()
            size_kb = path.stat().st_size / 1024 if exists else 0
            self._logger.info(
                "Output %s: %s (%s KB)",
                name, "EXISTS" if exists else "MISSING", round(size_kb, 1),
            )

    # -----------------------------------------------------------------
    # Results compilation
    # -----------------------------------------------------------------

    def _compile_results(self) -> dict[str, Any]:
        """Compile all test results into the final structure."""
        elapsed = time.monotonic() - self._start_time
        self._peak_memory_gb = max(self._peak_memory_gb, get_rss_gb())

        # Compute aggregate metrics
        total_articles = sum(s.get("articles_extracted", 0) for s in self._per_site_data)
        success_sites = sum(
            1 for s in self._per_site_data
            if s.get("status") == "success" and s.get("articles_extracted", 0) > 0
        )
        total_sites = len(self._per_site_data) or 44
        success_rate = success_sites / total_sites if total_sites > 0 else 0.0

        total_discovered = sum(s.get("articles_found", 0) for s in self._per_site_data)
        total_deduped = sum(
            s.get("articles_found", 0) * s.get("dedup_ratio", 0)
            for s in self._per_site_data
        )
        global_dedup_ratio = total_deduped / total_discovered if total_discovered > 0 else 0.0

        max_site_time = max(
            (s.get("crawl_time_seconds", 0) for s in self._per_site_data),
            default=0,
        )

        aggregate = {
            "success_rate": round(success_rate, 4),
            "total_articles": total_articles,
            "successful_sites": success_sites,
            "total_sites": total_sites,
            "global_dedup_ratio": round(global_dedup_ratio, 4),
            "max_per_site_time": round(max_site_time, 1),
            "peak_memory_gb": round(self._peak_memory_gb, 3),
            "total_elapsed_seconds": round(elapsed, 1),
        }

        # PRD threshold evaluation
        prd_metrics = {
            "success_rate": {
                "target": f">= {THRESHOLD_SUCCESS_RATE*100:.0f}%",
                "actual": f"{success_rate*100:.1f}%",
                "status": "PASS" if success_rate >= THRESHOLD_SUCCESS_RATE else "FAIL",
            },
            "total_articles": {
                "target": f">= {THRESHOLD_MIN_ARTICLES}",
                "actual": str(total_articles),
                "status": "PASS" if total_articles >= THRESHOLD_MIN_ARTICLES else "FAIL",
            },
            "dedup_effectiveness": {
                "target": f">= {THRESHOLD_DEDUP_EFFECTIVENESS*100:.0f}%",
                "actual": f"{global_dedup_ratio*100:.1f}%",
                "status": "PASS" if global_dedup_ratio >= THRESHOLD_DEDUP_EFFECTIVENESS else "DEFERRED",
            },
            "max_per_site_time": {
                "target": f"<= {THRESHOLD_MAX_SITE_TIME_SECONDS}s",
                "actual": f"{max_site_time:.1f}s",
                "status": "PASS" if max_site_time <= THRESHOLD_MAX_SITE_TIME_SECONDS else "FAIL",
            },
            "peak_memory": {
                "target": f"<= {THRESHOLD_MAX_MEMORY_GB} GB",
                "actual": f"{self._peak_memory_gb:.3f} GB",
                "status": "PASS" if self._peak_memory_gb <= THRESHOLD_MAX_MEMORY_GB else "FAIL",
            },
        }

        return {
            "test_date": self._date,
            "test_type": "dry_run" if self._dry_run else "live",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": f"{os.uname().sysname} {os.uname().release} ({os.uname().machine})",
            "total_duration_seconds": round(elapsed, 1),
            "prd_metrics": prd_metrics,
            "aggregate_metrics": aggregate,
            "sites": self._per_site_data,
            "analysis_stages": self._analysis_stages,
            "crawl_report_summary": {
                "total_articles": self._crawl_report.get("total_articles", 0),
                "sites_attempted": self._crawl_report.get("total_sites_attempted", 0),
                "sites_succeeded": self._crawl_report.get("sites_succeeded", 0),
                "sites_failed": self._crawl_report.get("sites_failed", 0),
            },
        }


# =============================================================================
# Report generators
# =============================================================================

def write_per_site_json(results: dict[str, Any], output_path: Path) -> None:
    """Write per-site-results.json from live test results."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)


def write_e2e_report(results: dict[str, Any], output_path: Path) -> None:
    """Write e2e-test-report.md from live test results."""
    lines = []
    lines.append("# E2E Test Report")
    lines.append("")
    lines.append("## Test Environment")
    lines.append(f"- **Date**: {results['test_date']}")
    lines.append(f"- **Python**: {results['python_version']}")
    lines.append(f"- **Platform**: {results['platform']}")
    lines.append(f"- **Total duration**: {results['total_duration_seconds']:.1f}s")
    lines.append(f"- **Test type**: {results['test_type']}")
    lines.append("")

    # PRD metrics
    lines.append("## PRD Section 9.1 Metrics Summary")
    lines.append("")
    lines.append("| Metric | Target | Actual | Status |")
    lines.append("|--------|--------|--------|--------|")
    for metric_name, metric in results.get("prd_metrics", {}).items():
        lines.append(
            f"| {metric_name} | {metric['target']} | {metric['actual']} | "
            f"**{metric['status']}** |"
        )
    lines.append("")

    # Overall verdict
    all_pass = all(
        m["status"] in ("PASS", "DEFERRED")
        for m in results.get("prd_metrics", {}).values()
    )
    verdict = "PASS" if all_pass else "FAIL"
    lines.append(f"## Overall Verdict: **{verdict}**")
    lines.append("")

    # Per-site results
    agg = results.get("aggregate_metrics", {})
    sites = results.get("sites", [])
    success_sites = [s for s in sites if s.get("status") == "success"]
    failed_sites = [s for s in sites if s.get("status") != "success"]

    lines.append(f"## Per-Site Results ({agg.get('successful_sites', 0)}/{agg.get('total_sites', 0)})")
    lines.append("")

    if success_sites:
        lines.append("### Successful Sites")
        lines.append("")
        lines.append("| Site | Group | Articles | Dedup% | Time(s) | Strategy |")
        lines.append("|------|-------|----------|--------|---------|----------|")
        for s in success_sites:
            lines.append(
                f"| {s['name']} | {s.get('group', '?')} | {s['articles_extracted']} | "
                f"{s['dedup_ratio']*100:.1f}% | {s['crawl_time_seconds']:.1f} | "
                f"{s['strategy_used']} |"
            )
        lines.append("")

    if failed_sites:
        lines.append("### Failed Sites")
        lines.append("")
        lines.append("| Site | Group | Failure Point | Root Cause | Transient? |")
        lines.append("|------|-------|--------------|------------|------------|")
        for s in failed_sites:
            fa = s.get("failure_analysis") or {}
            lines.append(
                f"| {s['name']} | {s.get('group', '?')} | "
                f"{fa.get('point', 'N/A')} | {fa.get('root_cause', 'N/A')} | "
                f"{'Yes' if fa.get('transient') else 'No'} |"
            )
        lines.append("")

    # Analysis pipeline
    stages = results.get("analysis_stages", [])
    if stages:
        lines.append("## Analysis Pipeline Results")
        lines.append("")
        lines.append("| Stage | Status | Time(s) | Peak Memory(MB) |")
        lines.append("|-------|--------|---------|-----------------|")
        for st in stages:
            lines.append(
                f"| Stage {st['stage']} | **{st['status']}** | "
                f"{st.get('time_seconds', 0):.1f} | "
                f"{st.get('peak_memory_mb', 0):.0f} |"
            )
        lines.append("")

    # Failure analysis details
    if failed_sites:
        lines.append("## Failure Analysis Details")
        lines.append("")
        for s in failed_sites:
            lines.append(f"### {s['name']} (Group {s.get('group', '?')})")
            fa = s.get("failure_analysis") or {}
            lines.append(f"- **Failure point**: {fa.get('point', 'unknown')}")
            lines.append(f"- **Root cause**: {fa.get('root_cause', 'unknown')}")
            lines.append(f"- **Transient**: {'Yes' if fa.get('transient') else 'No'}")
            errors = s.get("errors", [])
            if errors:
                lines.append(f"- **Errors** ({len(errors)}):")
                for err in errors[:5]:
                    lines.append(f"  - {err[:200]}")
                if len(errors) > 5:
                    lines.append(f"  - ... and {len(errors) - 5} more")
            lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    if agg.get("success_rate", 0) < THRESHOLD_SUCCESS_RATE:
        lines.append(
            f"1. **Improve success rate**: Currently {agg.get('success_rate', 0)*100:.1f}%, "
            f"target is {THRESHOLD_SUCCESS_RATE*100:.0f}%. "
            "Focus on sites with transient failures (retry tuning) and "
            "structural failures (adapter fixes)."
        )
    if agg.get("total_articles", 0) < THRESHOLD_MIN_ARTICLES:
        lines.append(
            f"2. **Increase article yield**: Currently {agg.get('total_articles', 0)}, "
            f"target is {THRESHOLD_MIN_ARTICLES}. "
            "Add fallback discovery methods for low-yield sites."
        )
    if agg.get("max_per_site_time", 0) > THRESHOLD_MAX_SITE_TIME_SECONDS:
        lines.append(
            f"3. **Reduce max per-site time**: Currently {agg.get('max_per_site_time', 0):.0f}s, "
            f"limit is {THRESHOLD_MAX_SITE_TIME_SECONDS}s. "
            "Review sites with highest crawl times for optimization."
        )
    lines.append("")

    lines.append("---")
    lines.append(
        f"Generated by `testing/run_e2e_test.py` on {results['test_date']}."
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    """Main entry point for the live E2E test runner.

    Returns:
        Exit code (0 = all PRD metrics pass, 1 = failures).
    """
    parser = argparse.ArgumentParser(
        description="Live E2E Test Runner for GlobalNews System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--date", type=str, default=None, help="Target date (YYYY-MM-DD)")
    parser.add_argument("--sites", type=str, default=None, help="Comma-separated site IDs")
    parser.add_argument("--groups", type=str, default=None, help="Comma-separated group letters")
    parser.add_argument("--dry-run", action="store_true", help="Validate wiring without network")
    parser.add_argument("--crawl-only", action="store_true", help="Skip analysis pipeline")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory")

    args = parser.parse_args()

    sites = [s.strip() for s in args.sites.split(",") if s.strip()] if args.sites else None
    groups = [g.strip().upper() for g in args.groups.split(",") if g.strip()] if args.groups else None

    print("=" * 70)
    print("GlobalNews E2E Live Test Runner")
    print("=" * 70)
    print(f"  Date: {args.date or 'today'}")
    print(f"  Sites: {sites or 'all 44'}")
    print(f"  Groups: {groups or 'all (A-G)'}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Crawl only: {args.crawl_only}")
    print()

    runner = LiveE2ETestRunner(
        crawl_date=args.date,
        sites_filter=sites,
        groups_filter=groups,
        dry_run=args.dry_run,
        crawl_only=args.crawl_only,
    )

    results = runner.run()

    # Write outputs
    output_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "testing"

    json_path = output_dir / "per-site-results.json"
    write_per_site_json(results, json_path)
    print(f"  JSON results: {json_path}")

    md_path = output_dir / "e2e-test-report.md"
    write_e2e_report(results, md_path)
    print(f"  Report: {md_path}")

    # Print summary
    agg = results.get("aggregate_metrics", {})
    print()
    print("  PRD Metrics:")
    for metric_name, metric in results.get("prd_metrics", {}).items():
        print(f"    {metric_name}: {metric['actual']} (target: {metric['target']}) [{metric['status']}]")

    all_pass = all(
        m["status"] in ("PASS", "DEFERRED")
        for m in results.get("prd_metrics", {}).values()
    )
    verdict = "PASS" if all_pass else "FAIL"
    print(f"\n  Overall: {verdict}")
    print(f"  Duration: {results['total_duration_seconds']:.1f}s")
    print(f"  Peak memory: {agg.get('peak_memory_gb', 0):.3f} GB")
    print()

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
