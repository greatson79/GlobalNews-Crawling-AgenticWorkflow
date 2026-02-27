"""GlobalNews Crawling & Analysis System -- Main Entry Point.

A staged monolith that crawls 44 international news sites through
an 8-stage NLP analysis pipeline, producing Parquet/SQLite output
for social trend research.

Usage:
    python main.py --mode crawl --date 2026-02-25
    python main.py --mode analyze --stage 1
    python main.py --mode full --dry-run
    python main.py --help
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config.constants import (
    PROJECT_ROOT,
    SOURCES_YAML_PATH,
    PIPELINE_YAML_PATH,
    DATA_RAW_DIR,
    CRAWL_GROUPS,
)
from src.utils.logging_config import setup_logging, get_logger


def _validate_date(date_str: str) -> date:
    """Parse and validate a YYYY-MM-DD date string.

    Args:
        date_str: Date string in YYYY-MM-DD format.

    Returns:
        Parsed date object.

    Raises:
        argparse.ArgumentTypeError: If the date string is invalid.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD."
        )


def _validate_stage(stage_str: str) -> int:
    """Parse and validate a stage number (1-8).

    Args:
        stage_str: Stage number as string.

    Returns:
        Validated stage number.

    Raises:
        argparse.ArgumentTypeError: If the stage number is invalid.
    """
    try:
        stage = int(stage_str)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Stage must be an integer, got: '{stage_str}'")
    if stage < 1 or stage > 8:
        raise argparse.ArgumentTypeError(f"Stage must be 1-8, got: {stage}")
    return stage


def cmd_crawl(args: argparse.Namespace) -> int:
    """Execute the crawling pipeline for configured news sources.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    logger = get_logger("main.crawl")
    logger.info(
        "Crawl started: date=%s sites=%s groups=%s dry_run=%s",
        args.date, args.sites or "all", args.groups or "all", args.dry_run,
    )

    if args.dry_run:
        logger.info("DRY RUN: Would crawl sites. No actual requests will be made.")
        # Load config to validate it exists and is valid
        from src.utils.config_loader import load_sources_config, get_enabled_sites
        config = load_sources_config()
        enabled = get_enabled_sites()
        logger.info("Would crawl %d enabled sites", len(enabled))
        for sid in sorted(enabled):
            site_cfg = config["sources"][sid]
            logger.info(
                "  %s: %s (group %s, ~%s articles/day)",
                sid, site_cfg['crawl']['primary_method'],
                site_cfg['group'], site_cfg['meta']['daily_article_estimate'],
            )
        return 0

    # Dispatch to the full crawling pipeline (Step 12)
    from src.crawling.pipeline import run_crawl_pipeline

    crawl_date_str = args.date.strftime("%Y-%m-%d") if args.date else None
    try:
        report = run_crawl_pipeline(
            crawl_date=crawl_date_str,
            sites=args.sites,
            groups=args.groups,
            dry_run=False,
        )
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.error("Crawl pipeline failed: %s", e, exc_info=True)
        return 1

    # Exit code: 0 if any articles collected, 1 if total failure
    total = report.get("total_articles", 0)
    failed = report.get("sites_failed", 0)
    attempted = report.get("total_sites_attempted", 0)
    if attempted > 0 and failed == attempted:
        logger.error("All %s sites failed.", attempted)
        return 1
    logger.info("Crawl complete: %s articles from %s sites.", total, attempted - failed)
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Execute the analysis pipeline on crawled articles.

    Dispatches to AnalysisPipeline for the 8-stage NLP pipeline.
    Supports running all stages, a single stage (checkpoint resume),
    or a dry-run configuration check.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    logger = get_logger("main.analyze")
    stages_to_run = list(range(1, 9)) if args.all_stages else ([args.stage] if args.stage else [])

    if not stages_to_run:
        logger.error("Specify --stage N (1-8) or --all-stages")
        return 1

    logger.info(
        "Analysis started: stages=%s date=%s dry_run=%s",
        stages_to_run, args.date or "latest", args.dry_run,
    )

    if args.dry_run:
        logger.info("DRY RUN: Would run analysis stages.")
        from src.analysis.pipeline import AnalysisPipeline, STAGE_NAMES
        analyze_date = args.date.strftime("%Y-%m-%d") if args.date else None
        pipeline = AnalysisPipeline(date=analyze_date)
        for stage_num in stages_to_run:
            name = STAGE_NAMES.get(stage_num, f"Stage {stage_num}")
            missing = pipeline._check_dependencies(stage_num)
            if missing:
                deps_str = ", ".join(f"{p.name}=MISSING" for p in missing)
            else:
                deps_str = "all OK"
            logger.info(f"  Stage {stage_num}: {name} | deps: [{deps_str}]")
        return 0

    # Dispatch to the analysis pipeline (Step 15)
    from src.analysis.pipeline import run_analysis_pipeline

    analyze_date_str = args.date.strftime("%Y-%m-%d") if args.date else None
    try:
        result = run_analysis_pipeline(
            date=analyze_date_str,
            stages=stages_to_run,
        )
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.error("Analysis pipeline failed: %s", e, exc_info=True)
        return 1

    # Print summary
    logger.info(
        "Analysis complete: success=%s completed=%s failed=%s "
        "skipped=%s elapsed=%.1fs peak_memory=%.2f_GB",
        result.success, result.stages_completed, result.stages_failed,
        result.stages_skipped, result.total_elapsed_seconds,
        result.peak_memory_gb,
    )

    # Print per-stage summary
    for stage_num in sorted(result.stages):
        sr = result.stages[stage_num]
        if sr.skipped:
            logger.info("  Stage %s (%s): SKIPPED -- %s", stage_num, sr.stage_name, sr.skip_reason)
        elif sr.success:
            logger.info(
                "  Stage %s (%s): OK (%.1fs, %s articles, %.2f GB)",
                stage_num, sr.stage_name, sr.elapsed_seconds,
                sr.article_count, sr.peak_memory_gb,
            )
        else:
            logger.info(
                "  Stage %s (%s): FAILED -- %s: %s",
                stage_num, sr.stage_name, sr.error_type, sr.error_message[:200],
            )

    # Print final outputs
    if result.final_output_paths:
        logger.info("Final outputs:")
        for name, path in result.final_output_paths.items():
            logger.info("  %s: %s", name, path)

    return 0 if result.success else 1


def cmd_full(args: argparse.Namespace) -> int:
    """Execute the full pipeline: crawl + all 8 analysis stages.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    logger = get_logger("main.full")
    logger.info("Full pipeline started: date=%s dry_run=%s", args.date, args.dry_run)

    # Phase 1: Crawl
    crawl_result = cmd_crawl(args)
    if crawl_result != 0:
        logger.error("Crawling phase failed, aborting analysis.")
        return crawl_result

    # Phase 2: Analyze (all stages)
    args.all_stages = True
    args.stage = None
    return cmd_analyze(args)


def cmd_status(args: argparse.Namespace) -> int:
    """Show pipeline status: configuration summary and data inventory.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 = success).
    """
    logger = get_logger("main.status")

    print("=" * 60)
    print("GlobalNews Crawling & Analysis System -- Status")
    print("=" * 60)

    # Check config files
    print(f"\nConfiguration Files:")
    print(f"  sources.yaml:  {'FOUND' if SOURCES_YAML_PATH.exists() else 'MISSING'} ({SOURCES_YAML_PATH})")
    print(f"  pipeline.yaml: {'FOUND' if PIPELINE_YAML_PATH.exists() else 'MISSING'} ({PIPELINE_YAML_PATH})")

    # Load and summarize sources config
    if SOURCES_YAML_PATH.exists():
        try:
            from src.utils.config_loader import load_sources_config
            config = load_sources_config(validate=False)
            sources = config.get("sources", {})
            enabled = sum(1 for s in sources.values() if s.get("meta", {}).get("enabled", False))
            total_articles = sum(s.get("meta", {}).get("daily_article_estimate", 0) for s in sources.values())
            groups = {}
            for sid, cfg in sources.items():
                g = cfg.get("group", "?")
                groups[g] = groups.get(g, 0) + 1
            print(f"\n  Sites: {len(sources)} total, {enabled} enabled")
            print(f"  Daily article estimate: ~{total_articles}")
            print(f"  Groups: {', '.join(f'{g}({c})' for g, c in sorted(groups.items()))}")
        except Exception as e:
            print(f"  Error loading sources.yaml: {e}")

    # Check data directories
    print(f"\nData Directories:")
    for name, path in [
        ("raw", DATA_RAW_DIR),
        ("processed", PROJECT_ROOT / "data" / "processed"),
        ("features", PROJECT_ROOT / "data" / "features"),
        ("analysis", PROJECT_ROOT / "data" / "analysis"),
        ("output", PROJECT_ROOT / "data" / "output"),
    ]:
        exists = path.exists()
        file_count = len(list(path.glob("*"))) if exists else 0
        print(f"  data/{name}/: {'EXISTS' if exists else 'MISSING'} ({file_count} files)")

    print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="GlobalNews Crawling & Analysis System -- "
                    "Crawl 44 news sites, analyze through 8-stage NLP pipeline, "
                    "produce Parquet/SQLite output for social trend research.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python main.py --mode crawl --date 2026-02-25 --dry-run
  python main.py --mode analyze --all-stages
  python main.py --mode full --date 2026-02-25
  python main.py --mode status

Architecture: Staged Monolith (Python 3.12)
Runtime: MacBook M2 Pro 16GB, 10GB memory budget
Sites: 44 international news sources across 7 groups (A-G)
Pipeline: 8 stages, 56 analysis techniques
""",
    )

    parser.add_argument(
        "--version", action="version", version="GlobalNews 0.1.0",
    )

    parser.add_argument(
        "--mode",
        choices=["crawl", "analyze", "full", "status"],
        required=True,
        help="Execution mode: crawl (URL discovery + extraction), "
             "analyze (8-stage NLP pipeline), full (crawl + analyze), "
             "status (show pipeline status)",
    )

    parser.add_argument(
        "--date",
        type=_validate_date,
        default=None,
        help="Target date in YYYY-MM-DD format (default: today)",
    )

    parser.add_argument(
        "--sites",
        type=str,
        default=None,
        help="Comma-separated site IDs to crawl (e.g., chosun,donga,yna). "
             "Default: all enabled sites.",
    )

    parser.add_argument(
        "--groups",
        type=str,
        default=None,
        help="Comma-separated group letters to crawl (e.g., A,B,E). "
             "Default: all groups.",
    )

    parser.add_argument(
        "--stage",
        type=_validate_stage,
        default=None,
        help="Specific analysis stage to run (1-8). Use with --mode analyze.",
    )

    parser.add_argument(
        "--all-stages",
        action="store_true",
        default=False,
        help="Run all 8 analysis stages sequentially.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate configuration and show plan without executing.",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Console log level (default: INFO).",
    )

    return parser


def main() -> int:
    """Main entry point for the GlobalNews CLI.

    Returns:
        Exit code (0 = success, non-zero = failure).
    """
    parser = build_parser()
    args = parser.parse_args()

    # Set default date to today if not specified
    if args.date is None:
        args.date = date.today()

    # Initialize logging
    setup_logging(console_level=args.log_level)

    # Parse comma-separated sites/groups into lists
    if args.sites:
        args.sites = [s.strip() for s in args.sites.split(",") if s.strip()]
    if args.groups:
        args.groups = [g.strip().upper() for g in args.groups.split(",") if g.strip()]

    # Dispatch to appropriate command handler
    handlers = {
        "crawl": cmd_crawl,
        "analyze": cmd_analyze,
        "full": cmd_full,
        "status": cmd_status,
    }

    handler = handlers.get(args.mode)
    if handler is None:
        parser.error(f"Unknown mode: {args.mode}")
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as e:
        logger = get_logger("main")
        logger.error(f"Unhandled error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
