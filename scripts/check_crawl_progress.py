#!/usr/bin/env python3
"""Check crawl progress from background task output and data files.

Tracks: sites with articles, sites with 0 articles, deadline yields
(fairness pauses), sites currently in progress, freshness/dedup skips,
bypass discovery attempts, and never-abandon retry cap status.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path for src.* imports
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _get_total_sites() -> int:
    """Get enabled site count from SOT (config_loader).

    P1: Reuses config_loader.get_enabled_sites() — no logic duplication.
    It uses constants.py ENABLED_DEFAULT (D-7 #13) and the correct YAML key.
    Lazy import: script stays functional even if src package is unavailable.
    """
    try:
        from src.utils.config_loader import get_enabled_sites
        return len(get_enabled_sites())
    except Exception:
        return 0


def _get_multi_pass_max() -> int:
    """Get MULTI_PASS_MAX_EXTRA from SOT (constants.py).

    Lazy import with hardcoded fallback — monitoring script must not crash.
    """
    try:
        from src.config.constants import MULTI_PASS_MAX_EXTRA
        return MULTI_PASS_MAX_EXTRA
    except Exception:
        return 10  # fallback — matches constants.py default


def main():
    project = Path(__file__).resolve().parent.parent
    output_file = sys.argv[1] if len(sys.argv) > 1 else None
    date_str = datetime.now().strftime("%Y-%m-%d")
    total_sites = _get_total_sites()
    multi_pass_max = _get_multi_pass_max()

    print(f"=== CRAWL PROGRESS {datetime.now().strftime('%H:%M:%S')} ===\n")

    # 1. Check confirmed articles in JSONL (finalized on disk)
    jsonl = project / "data" / "raw" / date_str / "all_articles.jsonl"
    article_count = 0
    sources: dict[str, int] = {}
    if jsonl.exists():
        with open(jsonl) as f:
            for line in f:
                article_count += 1
                try:
                    d = json.loads(line)
                    sid = d.get("source_id", "unknown")
                    sources[sid] = sources.get(sid, 0) + 1
                except json.JSONDecodeError:
                    pass

    # 1b. Detect active temp files (crawl still writing)
    tmp_files = list((project / "data" / "raw" / date_str).glob("*.jsonl.tmp")) if (project / "data" / "raw" / date_str).exists() else []

    # 2. Parse background task output for site completions
    completed_with_articles: dict[str, int] = {}
    completed_zero: list[str] = []
    started_sites: set[str] = set()
    skipped_sites: set[str] = set()
    deadline_yields: dict[str, int] = {}  # site -> yield count
    pass_count = 0  # never-abandon pass count

    # Log-based counters (primary metrics during active crawl)
    log_article_counts: dict[str, int] = {}  # site -> articles from log
    freshness_skips: dict[str, int] = {}  # site -> articles filtered by 24h window
    dedup_skips: dict[str, int] = {}  # site -> articles deduped
    bypass_attempts: dict[str, int] = {}  # site -> bypass discovery attempts
    bypass_successes: set[str] = set()
    cap_reached_sites: set[str] = set()  # sites that hit never-abandon cap

    if output_file and Path(output_file).exists():
        with open(output_file) as f:
            for line in f:
                # crawl_site_complete — check yielded flag
                m = re.search(r'crawl_site_complete\s+site=(\S+)\s+articles=(\d+)', line)
                if m:
                    site, count = m.group(1), int(m.group(2))
                    log_article_counts[site] = max(log_article_counts.get(site, 0), count)
                    yielded = 'yielded=True' in line
                    if yielded:
                        deadline_yields[site] = deadline_yields.get(site, 0) + 1
                    elif count > 0:
                        completed_with_articles[site] = max(
                            completed_with_articles.get(site, 0), count
                        )
                    else:
                        if site not in completed_zero:
                            completed_zero.append(site)
                    continue
                # site_already_complete
                m = re.search(r'site_already_complete\s+site_id=(\S+)', line)
                if m:
                    site = m.group(1)
                    skipped_sites.add(site)
                    cnt = sources.get(site, 0)
                    if cnt > 0:
                        completed_with_articles[site] = cnt
                    continue
                # deadline yield (fairness pause — site will be retried)
                if 'site_deadline_yield' in line:
                    m = re.search(r'site_id=(\S+)', line)
                    if m:
                        site = m.group(1)
                        deadline_yields[site] = deadline_yields.get(site, 0) + 1
                    continue
                # never-abandon pass
                if 'crawl_never_abandon_pass' in line:
                    m = re.search(r'pass=(\d+)', line)
                    if m:
                        pass_count = max(pass_count, int(m.group(1)))
                    continue
                # never-abandon cap reached
                if 'never_abandon_cap_reached' in line:
                    m = re.search(r'site_id=(\S+)', line)
                    if m:
                        cap_reached_sites.add(m.group(1))
                    continue
                # freshness filter (article outside 24h window)
                if 'article_outside_24h' in line:
                    m = re.search(r'site_id=(\S+)', line)
                    if not m:
                        m = re.search(r'site=(\S+)', line)
                    if m:
                        site = m.group(1)
                        freshness_skips[site] = freshness_skips.get(site, 0) + 1
                    continue
                # dedup filter
                if 'article_deduped' in line:
                    m = re.search(r'site_id=(\S+)', line)
                    if not m:
                        m = re.search(r'site=(\S+)', line)
                    if m:
                        site = m.group(1)
                        dedup_skips[site] = dedup_skips.get(site, 0) + 1
                    continue
                # bypass discovery attempt
                if 'bypass_discovery' in line:
                    m = re.search(r'site_id=(\S+)', line)
                    if not m:
                        m = re.search(r'site=(\S+)', line)
                    if m:
                        site = m.group(1)
                        bypass_attempts[site] = bypass_attempts.get(site, 0) + 1
                        if 'success' in line.lower() or 'urls_found' in line:
                            bypass_successes.add(site)
                    continue
                # crawl_site_start
                m = re.search(r'crawl_site_start\s+site=(\S+)', line)
                if m:
                    started_sites.add(m.group(1))

    all_done = set(completed_with_articles) | set(completed_zero) | skipped_sites
    in_progress = started_sites - all_done

    success_count = len(completed_with_articles)
    zero_count = len([s for s in completed_zero if s not in completed_with_articles])

    # Primary metric: log-based article count (real-time during crawl)
    log_total = sum(log_article_counts.values())

    site_label = str(total_sites) if total_sites > 0 else "?"
    print(f"Sites with articles:    {success_count} / {site_label}")
    print(f"Sites with 0 articles:  {zero_count}")
    print(f"Sites in progress:      {len(in_progress)}")
    print(f"Deadline yields:        {len(deadline_yields)} sites paused for fairness")
    if pass_count > 0:
        print(f"Never-abandon passes:   {pass_count} / {multi_pass_max}")
    if cap_reached_sites:
        print(f"Retry cap reached:      {len(cap_reached_sites)} sites exhausted")
    print(f"Articles (log):         {log_total} (real-time from crawl logs)")
    print(f"Articles (JSONL):       {article_count} (confirmed on disk)")
    if tmp_files:
        print(f"Temp files active:      {len(tmp_files)} (crawl still writing)")

    # Freshness/dedup summary
    total_freshness = sum(freshness_skips.values())
    total_dedup = sum(dedup_skips.values())
    if total_freshness or total_dedup:
        print()
        print("── Filtering ──")
        if total_freshness:
            print(f"  Freshness filtered:   {total_freshness} articles outside 24h window")
        if total_dedup:
            print(f"  Dedup filtered:       {total_dedup} duplicate articles skipped")
    print()

    # Top sites by articles
    if sources:
        print("Top sites by articles:")
        for sid, cnt in sorted(sources.items(), key=lambda x: -x[1])[:15]:
            print(f"  {sid:25s} {cnt:4d} articles")
        print()

    # In progress
    if in_progress:
        print(f"Currently crawling ({len(in_progress)}):")
        for s in sorted(in_progress)[:10]:
            yields = deadline_yields.get(s, 0)
            suffix = f" (yielded {yields}x)" if yields else ""
            print(f"  {s}{suffix}")
        if len(in_progress) > 10:
            print(f"  ... and {len(in_progress) - 10} more")
        print()

    # Bypass discovery results
    if bypass_attempts:
        print(f"── Bypass Discovery ({len(bypass_attempts)} sites) ──")
        for site, count in sorted(bypass_attempts.items(), key=lambda x: -x[1])[:10]:
            status = "OK" if site in bypass_successes else "BLOCKED"
            print(f"  {site:25s} {count:3d} attempts  [{status}]")
        if len(bypass_attempts) > 10:
            print(f"  ... and {len(bypass_attempts) - 10} more")
        print()

    # Sites that hit retry cap (will appear in failure report)
    if cap_reached_sites:
        print(f"── Retry Cap Exhausted ({len(cap_reached_sites)}) ──")
        print("  These sites will be in crawl_exhausted_sites.json:")
        for site in sorted(cap_reached_sites):
            print(f"  - {site}")
        print()

    # Deadline yields detail
    if deadline_yields:
        active_yields = {s: c for s, c in deadline_yields.items() if s not in all_done}
        done_yields = {s: c for s, c in deadline_yields.items() if s in all_done}
        if active_yields:
            print(f"Sites awaiting retry after yield ({len(active_yields)}):")
            for site, count in sorted(active_yields.items(), key=lambda x: -x[1])[:10]:
                print(f"  {site:25s} {count:3d} yields")
            if len(active_yields) > 10:
                print(f"  ... and {len(active_yields) - 10} more")
            print()
        if done_yields:
            print(f"Sites completed after yield ({len(done_yields)}):")
            for site, count in sorted(done_yields.items(), key=lambda x: -x[1])[:5]:
                articles = completed_with_articles.get(site, 0)
                print(f"  {site:25s} {count:3d} yields → {articles} articles")
            print()

    # Freshness/dedup detail per site (top offenders)
    if freshness_skips:
        print("Top sites by freshness-filtered articles:")
        for sid, cnt in sorted(freshness_skips.items(), key=lambda x: -x[1])[:5]:
            print(f"  {sid:25s} {cnt:4d} outside 24h")
        print()

    # Elapsed
    if output_file and Path(output_file).exists():
        stat = Path(output_file).stat()
        elapsed = datetime.now().timestamp() - stat.st_birthtime
        print(f"Elapsed: {elapsed/60:.1f} minutes")

    # Post-crawl failure report check
    report = project / "data" / "raw" / date_str / "crawl_exhausted_sites.json"
    if report.exists():
        print()
        print(f"⚠ Failure report generated: {report}")
        try:
            data = json.loads(report.read_text())
            sites = data.get("exhausted_sites", [])
            print(f"  {len(sites)} sites exhausted after max retries")
            for entry in sites[:5]:
                sid = entry.get("site_id", "?")
                cat = entry.get("failure_category", "unknown")
                print(f"  - {sid}: {cat}")
            if len(sites) > 5:
                print(f"  ... and {len(sites) - 5} more")
        except (json.JSONDecodeError, OSError):
            pass


if __name__ == "__main__":
    main()
