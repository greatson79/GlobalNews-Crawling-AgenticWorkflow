#!/usr/bin/env python3
"""Site Coverage Validator — P1 deterministic 44-site coverage check.

Verifies that a document mentions all 44 target news sites.
Used after Steps 1, 6, 11 to prevent "all 44 sites covered" hallucination.

Usage:
    python3 scripts/validate_site_coverage.py --file research/site-reconnaissance.md --project-dir .
    python3 scripts/validate_site_coverage.py --file planning/crawling-strategies.md --project-dir . --sources-yaml sources.yaml

JSON output to stdout. Exit code 0 always.
"""

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Default 44 site domains — from PRD
# If sources.yaml exists, extract from there instead
# ---------------------------------------------------------------------------
DEFAULT_SITES = [
    # Group A: Korean Major Dailies (5)
    "chosun.com", "joongang.co.kr", "donga.com", "hani.co.kr", "yna.co.kr",
    # Group B: Korean Economy (4)
    "mk.co.kr", "hankyung.com", "fnnews.com", "mt.co.kr",
    # Group C: Korean Niche (3)
    "nocutnews.co.kr", "kmib.co.kr", "ohmynews.com",
    # Group D: Korean IT/Science (7)
    "38north.org", "bloter.net", "etnews.com", "sciencetimes.co.kr",
    "zdnet.co.kr", "irobotnews.com", "techneedle.com",
    # Group E: US/English Major (12)
    "marketwatch.com", "voakorea.com", "huffingtonpost.com", "nytimes.com",
    "ft.com", "wsj.com", "latimes.com", "buzzfeed.com",
    "nationalpost.com", "edition.cnn.com", "bloomberg.com", "afmedios.com",
    # Group F: Asia-Pacific (6)
    "people.com.cn", "globaltimes.cn", "scmp.com", "taiwannews.com",
    "yomiuri.co.jp", "thehindu.com",
    # Group G: Europe/Middle East (7)
    "thesun.co.uk", "bild.de", "lemonde.fr", "themoscowtimes.com",
    "arabnews.com", "aljazeera.com", "israelhayom.com",
]


def _load_sites_from_yaml(yaml_path):
    """Extract site domains from sources.yaml."""
    if not os.path.exists(yaml_path):
        return None
    try:
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            sites = []
            # Try common structures
            for key in ("sites", "sources", "news_sites"):
                if isinstance(data.get(key), (list, dict)):
                    items = data[key]
                    if isinstance(items, dict):
                        items = list(items.values())
                    for item in items:
                        if isinstance(item, dict):
                            url = item.get("url", item.get("domain", ""))
                        elif isinstance(item, str):
                            url = item
                        else:
                            continue
                        # Extract domain from URL
                        domain = re.sub(r'^https?://(www\.)?', '', str(url)).rstrip('/').split('/')[0]
                        if domain:
                            sites.append(domain)
            return sites if sites else None
        return None
    except Exception:
        return None


def validate_coverage(project_dir, file_path, sources_yaml=None):
    """Check that file mentions all target sites."""
    result = {
        "valid": True,
        "file": file_path,
        "total_expected": 0,
        "found": 0,
        "missing": [],
        "duplicates": [],
        "warnings": [],
    }

    # Resolve file path
    full_path = os.path.join(project_dir, file_path) if not os.path.isabs(file_path) else file_path
    if not os.path.exists(full_path):
        result["valid"] = False
        result["warnings"].append(f"SC0: File not found: {file_path}")
        return result

    # Load expected sites
    sites = None
    if sources_yaml:
        yaml_path = os.path.join(project_dir, sources_yaml) if not os.path.isabs(sources_yaml) else sources_yaml
        sites = _load_sites_from_yaml(yaml_path)

    if not sites:
        sites = DEFAULT_SITES

    result["total_expected"] = len(sites)

    # Read document content
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read().lower()
    except Exception as e:
        result["valid"] = False
        result["warnings"].append(f"SC0: Cannot read file: {e}")
        return result

    # SC1-SC2: Check each site's presence
    found_sites = []
    missing_sites = []
    for site in sites:
        # Normalize domain for matching
        domain_core = site.lower().replace("www.", "")
        # Check for domain or partial match (e.g., "chosun" for chosun.com)
        domain_parts = domain_core.split(".")
        main_name = domain_parts[0]

        if domain_core in content or main_name in content:
            found_sites.append(site)
        else:
            missing_sites.append(site)

    result["found"] = len(found_sites)
    result["missing"] = missing_sites

    # SC3: Missing sites
    if missing_sites:
        result["valid"] = False
        result["warnings"].append(f"SC3: {len(missing_sites)} sites not found in document")

    # SC4: Duplicate detection
    seen = set()
    for site in sites:
        domain_core = site.lower()
        if domain_core in seen:
            result["duplicates"].append(site)
        seen.add(domain_core)

    if result["duplicates"]:
        result["warnings"].append(f"SC4: Duplicate domains: {result['duplicates']}")

    # Coverage percentage
    result["coverage_pct"] = round(result["found"] / result["total_expected"] * 100, 1) if result["total_expected"] else 0

    return result


def main():
    parser = argparse.ArgumentParser(description="Site Coverage Validator — P1")
    parser.add_argument("--file", required=True, help="Document file to check")
    parser.add_argument("--project-dir", required=True, help="Project root directory")
    parser.add_argument("--sources-yaml", help="Path to sources.yaml (optional)")
    args = parser.parse_args()

    result = validate_coverage(args.project_dir, args.file, args.sources_yaml)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
