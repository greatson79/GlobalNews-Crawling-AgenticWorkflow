#!/usr/bin/env python3
"""Deterministic crawl failure diagnosis — P1 hallucination prevention.

Reads crawl task output (log lines) and classifies each site's failure
mode using regex-based FAILURE_TAXONOMY. Produces a structured JSON
report at data/raw/YYYY-MM-DD/crawl_diagnosis.json.

This script replaces LLM-based log interpretation with repeatable,
deterministic classification. Same input → same output, always.

Usage:
    python scripts/diagnose_crawl_failures.py <task_output_file> [--date YYYY-MM-DD]
    python scripts/diagnose_crawl_failures.py --log-dir data/raw/2026-03-13/ [--date 2026-03-13]
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# P1 Failure Taxonomy — deterministic regex classification
# ---------------------------------------------------------------------------
# Each pattern maps to a failure category. Order matters: first match wins
# within a site's event stream. Counts are aggregated per site.

FAILURE_TAXONOMY: list[tuple[str, re.Pattern[str]]] = [
    ("discovery_blocked",   re.compile(r"(?:rss|sitemap|dom)_discovery_failed.*(?:403|BlockDetected|access.denied)", re.IGNORECASE)),
    ("discovery_blocked",   re.compile(r"article_blocked.*block_type=", re.IGNORECASE)),
    ("discovery_empty",     re.compile(r"no_urls_discovered")),
    ("extraction_parse",    re.compile(r"extraction_parse_error")),
    ("extraction_network",  re.compile(r"article_fetch_failed|article_extraction_failed")),
    ("extraction_blocked",  re.compile(r"article_blocked")),
    ("freshness_filtered",  re.compile(r"article_outside_24h")),
    ("dedup_filtered",      re.compile(r"article_deduped")),
    ("timeout_yielded",     re.compile(r"site_deadline_yield")),
    ("sitemap_full_scan",   re.compile(r"sitemap_child_page.*(?:outside_date_range|skipping.*old)")),
    ("never_abandon_cycle", re.compile(r"never_abandon_cycle\s")),
    ("never_abandon_cap",   re.compile(r"never_abandon_safety_cap_reached")),
    ("bypass_success",      re.compile(r"never_abandon_bypass_SUCCESS")),
    ("bypass_fail",         re.compile(r"never_abandon_cycle_failed")),
]

# Site extraction from log lines
_SITE_ID_RE = re.compile(r"(?:site_id|site|source_id)=(\S+)")

# Completion detection
_COMPLETE_RE = re.compile(
    r"crawl_site_complete\s+site=(\S+)\s+articles=(\d+)\s+"
    r"discovered=(\d+)\s+failed=(\d+)\s+elapsed=(\S+)s\s+yielded=(\S+)"
)

# Block type extraction
_BLOCK_TYPE_RE = re.compile(r"block_type=(\S+)")

# Discovery failure with error type
_DISCOVERY_FAIL_RE = re.compile(
    r"(?:rss|sitemap|dom)_discovery_failed\s+source_id=(\S+)\s+error=(.*?)(?:\s+error_type=(\S+))?"
)

# ---------------------------------------------------------------------------
# Recommended actions per failure type — deterministic mapping
# ---------------------------------------------------------------------------

RECOMMENDED_ACTIONS: dict[str, str] = {
    "discovery_blocked": (
        "Enable DynamicBypassEngine at URL discovery level. "
        "Try T1 (curl_cffi TLS mimicry) first, escalate to T2 (browser) if needed."
    ),
    "discovery_empty": (
        "Verify RSS/sitemap URLs in sources.yaml are current. "
        "Check if site changed feed URL or disabled RSS."
    ),
    "extraction_parse": (
        "Review ArticleExtractor CSS selectors for this site. "
        "Site may have changed HTML structure."
    ),
    "extraction_network": (
        "Transient network errors. Will likely resolve on next crawl. "
        "If persistent, check rate_limit_seconds in sources.yaml."
    ),
    "extraction_blocked": (
        "Enable DynamicBypassEngine for article extraction. "
        "Already supported via Never-Abandon loop."
    ),
    "freshness_filtered": (
        "Normal operation — site's articles are older than 24h lookback. "
        "No action needed unless timezone mismatch suspected."
    ),
    "dedup_filtered": (
        "Normal operation — articles already collected in previous crawl. "
        "No action needed."
    ),
    "timeout_yielded": (
        "Site was slow and yielded its worker slot. "
        "Will be retried in next Never-Abandon pass. "
        "Consider increasing per-site timeout if persistent."
    ),
    "sitemap_full_scan": (
        "Sitemap date inference failed — scanning full archive. "
        "Check _infer_date_from_sitemap_url() for this site's URL pattern."
    ),
}


def _extract_site_id(line: str) -> str | None:
    """Extract site_id from a log line."""
    m = _SITE_ID_RE.search(line)
    return m.group(1) if m else None


def _classify_line(line: str) -> list[tuple[str, str | None]]:
    """Classify a log line into failure categories.

    Returns list of (category, site_id) tuples. A line can match
    multiple categories (e.g., both extraction_blocked and discovery_blocked).
    """
    results = []
    site_id = _extract_site_id(line)

    for category, pattern in FAILURE_TAXONOMY:
        if pattern.search(line):
            results.append((category, site_id))

    return results


def diagnose(log_lines: list[str]) -> dict[str, Any]:
    """Run deterministic diagnosis on crawl log lines.

    Args:
        log_lines: Raw log lines from crawl task output.

    Returns:
        Structured diagnosis report.
    """
    # Per-site event counters
    site_events: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # Per-site completion info
    site_completions: dict[str, dict[str, Any]] = {}
    # Per-site block types detected
    site_block_types: dict[str, list[str]] = defaultdict(list)
    # Global counters
    global_events: dict[str, int] = defaultdict(int)

    for line in log_lines:
        # Check for completion
        m = _COMPLETE_RE.search(line)
        if m:
            site_id = m.group(1)
            site_completions[site_id] = {
                "articles": int(m.group(2)),
                "discovered": int(m.group(3)),
                "failed": int(m.group(4)),
                "elapsed_s": float(m.group(5)),
                "yielded": m.group(6) == "True",
            }
            continue

        # Extract block type if present
        site_id = _extract_site_id(line)
        if site_id:
            bt_m = _BLOCK_TYPE_RE.search(line)
            if bt_m:
                bt = bt_m.group(1)
                if bt not in site_block_types[site_id]:
                    site_block_types[site_id].append(bt)

        # Classify
        classifications = _classify_line(line)
        for category, sid in classifications:
            global_events[category] += 1
            if sid:
                site_events[sid][category] += 1

    # Determine primary failure type per site
    site_details: dict[str, dict[str, Any]] = {}
    for site_id in sorted(set(site_events) | set(site_completions)):
        events = dict(site_events.get(site_id, {}))
        completion = site_completions.get(site_id)

        # Determine primary failure type by priority
        primary_failure = _determine_primary_failure(events, completion)

        detail: dict[str, Any] = {
            "failure_type": primary_failure,
            "events": events,
        }

        if completion:
            detail["completion"] = completion

        if site_id in site_block_types:
            detail["block_types"] = site_block_types[site_id]

        if primary_failure and primary_failure in RECOMMENDED_ACTIONS:
            detail["recommended_action"] = RECOMMENDED_ACTIONS[primary_failure]

        site_details[site_id] = detail

    # Categorize sites
    categories: dict[str, list[str]] = defaultdict(list)
    for site_id, detail in site_details.items():
        completion = detail.get("completion")
        ft = detail["failure_type"]

        if completion and completion["articles"] > 0 and not completion["yielded"]:
            categories["success"].append(site_id)
        elif ft:
            categories[ft].append(site_id)
        else:
            categories["unknown"].append(site_id)

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
        "total_sites_in_log": len(set(site_events) | set(site_completions)),
        "summary": {
            category: len(sites)
            for category, sites in sorted(categories.items())
        },
        "categories": {k: sorted(v) for k, v in sorted(categories.items())},
        "global_events": dict(sorted(global_events.items())),
        "site_details": site_details,
    }


def _determine_primary_failure(
    events: dict[str, int],
    completion: dict[str, Any] | None,
) -> str | None:
    """Determine the primary failure type for a site.

    Priority order (highest first):
    1. discovery_blocked — can't even find URLs
    2. sitemap_full_scan — scanning full archive (performance)
    3. extraction_blocked — found URLs but blocked during extraction
    4. extraction_parse — extraction code bug
    5. extraction_network — transient network issue
    6. freshness_filtered — normal operation (articles too old)
    7. dedup_filtered — normal operation (already seen)
    8. timeout_yielded — slow site
    9. never_abandon_cap — exhausted all retries
    """
    if not events:
        if completion and completion["articles"] > 0:
            return None  # Success
        return None  # No data

    priority = [
        "discovery_blocked",
        "sitemap_full_scan",
        "extraction_blocked",
        "extraction_parse",
        "extraction_network",
        "freshness_filtered",
        "dedup_filtered",
        "timeout_yielded",
        "never_abandon_cap",
    ]

    for category in priority:
        if events.get(category, 0) > 0:
            return category

    # If only positive events (bypass_success, etc.), not a failure
    positive = {"bypass_success", "never_abandon_cycle"}
    if all(k in positive for k in events):
        return None

    # Fallback: highest count event
    return max(events, key=lambda k: events[k])


def print_summary(report: dict[str, Any]) -> None:
    """Print human-readable summary to stdout."""
    print(f"\n{'=' * 60}")
    print(f"CRAWL DIAGNOSIS REPORT — {report['date']}")
    print(f"{'=' * 60}\n")

    summary = report["summary"]
    total = report["total_sites_in_log"]

    print(f"Total sites in log: {total}\n")

    # Category summary
    print("Failure categories:")
    for category, count in sorted(summary.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        marker = "✓" if category == "success" else "✗"
        print(f"  {marker} {category:25s} {count:3d} ({pct:5.1f}%)")

    # Actionable sites
    print(f"\n{'─' * 60}")
    print("ACTIONABLE SITES (require intervention):\n")

    actionable_types = {
        "discovery_blocked", "sitemap_full_scan",
        "extraction_blocked", "extraction_parse",
    }

    for site_id, detail in sorted(report["site_details"].items()):
        ft = detail.get("failure_type")
        if ft in actionable_types:
            block_types = detail.get("block_types", [])
            bt_str = f" [{', '.join(block_types)}]" if block_types else ""
            action = detail.get("recommended_action", "")
            print(f"  {site_id:25s} → {ft}{bt_str}")
            if action:
                print(f"    Action: {action}")
            print()

    # Normal operation sites
    normal_types = {"freshness_filtered", "dedup_filtered"}
    normal_sites = [
        sid for sid, d in report["site_details"].items()
        if d.get("failure_type") in normal_types
    ]
    if normal_sites:
        print(f"Normal operation (no action needed): {len(normal_sites)} sites")
        for sid in sorted(normal_sites)[:5]:
            ft = report["site_details"][sid]["failure_type"]
            print(f"  {sid:25s} → {ft}")
        if len(normal_sites) > 5:
            print(f"  ... and {len(normal_sites) - 5} more")


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Deterministic crawl failure diagnosis (P1)"
    )
    parser.add_argument(
        "task_output",
        nargs="?",
        help="Path to background task output file (crawl log lines)",
    )
    parser.add_argument(
        "--log-dir",
        help="Directory containing crawl logs (alternative to task_output)",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Crawl date (YYYY-MM-DD), default: today",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON only (no human summary)",
    )

    args = parser.parse_args()

    # Read log lines
    log_lines: list[str] = []

    if args.task_output:
        path = Path(args.task_output)
        if path.exists():
            with open(path, encoding="utf-8", errors="replace") as f:
                log_lines = f.readlines()
        else:
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
    elif args.log_dir:
        log_dir = Path(args.log_dir)
        # Read all log-like files in directory
        for log_file in sorted(log_dir.glob("*.log")) + sorted(log_dir.glob("*.output")):
            with open(log_file, encoding="utf-8", errors="replace") as f:
                log_lines.extend(f.readlines())
    else:
        # Try reading from stdin
        if not sys.stdin.isatty():
            log_lines = sys.stdin.readlines()
        else:
            parser.print_help()
            sys.exit(1)

    if not log_lines:
        print("Warning: no log lines to diagnose", file=sys.stderr)
        sys.exit(0)

    # Run diagnosis
    report = diagnose(log_lines)
    report["date"] = args.date

    # Write JSON report
    project_root = Path(__file__).resolve().parent.parent
    output_dir = project_root / "data" / "raw" / args.date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "crawl_diagnosis.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_summary(report)
        print(f"\nFull report: {output_path}")


if __name__ == "__main__":
    main()
