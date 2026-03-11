#!/usr/bin/env python3
"""Extract site URLs from PRD or sources.yaml for agent context injection.

Usage:
    python3 scripts/extract_site_urls.py --project-dir .
    python3 scripts/extract_site_urls.py --project-dir . --prd coding-resource/PRD.md
    python3 scripts/extract_site_urls.py --project-dir . --sources data/config/sources.yaml

Output: JSON with structured site list (domain, language, group) to stdout.

This is a P1 pre-processing script: deterministic extraction, no LLM inference.
It extracts the 121 news site URLs from either the PRD document (parsing the
Target Sites table in workflow.md or the data source tables in PRD.md) or from
a sources.yaml configuration file if it exists.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

# -- Canonical site registry -------------------------------------------------
# Derived from workflow.md Target Sites table (the authoritative 121-site list).
# Each entry: (domain, language, group_code, group_label)
_CANONICAL_SITES: list[tuple[str, str, str, str]] = [
    # Group A — Korean Major Dailies (5)
    ("chosun.com", "ko", "A", "Korean Major Dailies"),
    ("joongang.co.kr", "ko", "A", "Korean Major Dailies"),
    ("donga.com", "ko", "A", "Korean Major Dailies"),
    ("hani.co.kr", "ko", "A", "Korean Major Dailies"),
    ("yna.co.kr", "ko", "A", "Korean Major Dailies"),
    # Group B — Korean Economy (4)
    ("mk.co.kr", "ko", "B", "Korean Economy"),
    ("hankyung.com", "ko", "B", "Korean Economy"),
    ("fnnews.com", "ko", "B", "Korean Economy"),
    ("mt.co.kr", "ko", "B", "Korean Economy"),
    # Group C — Korean Niche (3)
    ("nocutnews.co.kr", "ko", "C", "Korean Niche"),
    ("kmib.co.kr", "ko", "C", "Korean Niche"),
    ("ohmynews.com", "ko", "C", "Korean Niche"),
    # Group D — Korean IT/Science (10)
    ("38north.org", "en", "D", "Korean IT/Science"),
    ("bloter.net", "ko", "D", "Korean IT/Science"),
    ("etnews.com", "ko", "D", "Korean IT/Science"),
    ("sciencetimes.co.kr", "ko", "D", "Korean IT/Science"),
    ("zdnet.co.kr", "ko", "D", "Korean IT/Science"),
    ("irobotnews.com", "ko", "D", "Korean IT/Science"),
    ("techneedle.com", "ko", "D", "Korean IT/Science"),
    ("insight.co.kr", "ko", "D", "Korean IT/Science"),
    ("stratechery.com", "en", "D", "Korean IT/Science"),
    ("techmeme.com", "en", "D", "Korean IT/Science"),
    # Group E — US/English Major (22)
    ("marketwatch.com", "en", "E", "US/English Major"),
    ("voakorea.com", "en", "E", "US/English Major"),
    ("huffingtonpost.com", "en", "E", "US/English Major"),
    ("nytimes.com", "en", "E", "US/English Major"),
    ("ft.com", "en", "E", "US/English Major"),
    ("wsj.com", "en", "E", "US/English Major"),
    ("latimes.com", "en", "E", "US/English Major"),
    ("buzzfeed.com", "en", "E", "US/English Major"),
    ("nationalpost.com", "en", "E", "US/English Major"),
    ("edition.cnn.com", "en", "E", "US/English Major"),
    ("bloomberg.com", "en", "E", "US/English Major"),
    ("afmedios.com", "es", "E", "US/English Major"),
    ("wired.com", "en", "E", "US/English Major"),
    ("investing.com", "en", "E", "US/English Major"),
    ("qz.com", "en", "E", "US/English Major"),
    ("bbc.com", "en", "E", "US/English Major"),
    ("theguardian.com", "en", "E", "US/English Major"),
    ("thetimes.com", "en", "E", "US/English Major"),
    ("telegraph.co.uk", "en", "E", "US/English Major"),
    ("politico.eu", "en", "E", "US/English Major"),
    ("euractiv.com", "en", "E", "US/English Major"),
    ("natureasia.com", "en", "E", "US/English Major"),
    # Group F — Asia-Pacific (23)
    ("people.com.cn", "zh", "F", "Asia-Pacific"),
    ("globaltimes.cn", "en", "F", "Asia-Pacific"),
    ("scmp.com", "en", "F", "Asia-Pacific"),
    ("taiwannews.com", "en", "F", "Asia-Pacific"),
    ("yomiuri.co.jp", "ja", "F", "Asia-Pacific"),
    ("thehindu.com", "en", "F", "Asia-Pacific"),
    ("mainichi.jp", "ja", "F", "Asia-Pacific"),
    ("asahi.com", "ja", "F", "Asia-Pacific"),
    ("yahoo.co.jp", "ja", "F", "Asia-Pacific"),
    ("timesofindia.indiatimes.com", "en", "F", "Asia-Pacific"),
    ("hindustantimes.com", "en", "F", "Asia-Pacific"),
    ("economictimes.indiatimes.com", "en", "F", "Asia-Pacific"),
    ("indianexpress.com", "en", "F", "Asia-Pacific"),
    ("philstar.com", "en", "F", "Asia-Pacific"),
    ("mb.com.ph", "en", "F", "Asia-Pacific"),
    ("inquirer.net", "en", "F", "Asia-Pacific"),
    ("thejakartapost.com", "en", "F", "Asia-Pacific"),
    ("antaranews.com", "en", "F", "Asia-Pacific"),
    ("tempo.co", "en", "F", "Asia-Pacific"),
    ("focustaiwan.tw", "en", "F", "Asia-Pacific"),
    ("taipeitimes.com", "en", "F", "Asia-Pacific"),
    ("vnexpress.net", "en", "F", "Asia-Pacific"),
    ("vietnamnews.vn", "en", "F", "Asia-Pacific"),
    # Group G — Europe/Middle East (38)
    ("thesun.co.uk", "en", "G", "Europe/Middle East"),
    ("bild.de", "de", "G", "Europe/Middle East"),
    ("lemonde.fr", "fr", "G", "Europe/Middle East"),
    ("themoscowtimes.com", "en", "G", "Europe/Middle East"),
    ("arabnews.com", "en", "G", "Europe/Middle East"),
    ("aljazeera.com", "en", "G", "Europe/Middle East"),
    ("israelhayom.com", "en", "G", "Europe/Middle East"),
    ("euronews.com", "en", "G", "Europe/Middle East"),
    ("spiegel.de", "de", "G", "Europe/Middle East"),
    ("sueddeutsche.de", "de", "G", "Europe/Middle East"),
    ("welt.de", "de", "G", "Europe/Middle East"),
    ("faz.net", "de", "G", "Europe/Middle East"),
    ("corriere.it", "it", "G", "Europe/Middle East"),
    ("repubblica.it", "it", "G", "Europe/Middle East"),
    ("ansa.it", "it", "G", "Europe/Middle East"),
    ("elpais.com", "es", "G", "Europe/Middle East"),
    ("elmundo.es", "es", "G", "Europe/Middle East"),
    ("abc.es", "es", "G", "Europe/Middle East"),
    ("lavanguardia.com", "es", "G", "Europe/Middle East"),
    ("lefigaro.fr", "fr", "G", "Europe/Middle East"),
    ("liberation.fr", "fr", "G", "Europe/Middle East"),
    ("france24.com", "fr", "G", "Europe/Middle East"),
    ("ouest-france.fr", "fr", "G", "Europe/Middle East"),
    ("wyborcza.pl", "pl", "G", "Europe/Middle East"),
    ("pap.pl", "pl", "G", "Europe/Middle East"),
    ("idnes.cz", "cs", "G", "Europe/Middle East"),
    ("intellinews.com", "en", "G", "Europe/Middle East"),
    ("balkaninsight.com", "en", "G", "Europe/Middle East"),
    ("centraleuropeantimes.com", "en", "G", "Europe/Middle East"),
    ("aftonbladet.se", "sv", "G", "Europe/Middle East"),
    ("tv2.no", "no", "G", "Europe/Middle East"),
    ("yle.fi", "fi", "G", "Europe/Middle East"),
    ("icelandmonitor.mbl.is", "en", "G", "Europe/Middle East"),
    ("middleeasteye.net", "en", "G", "Europe/Middle East"),
    ("al-monitor.com", "en", "G", "Europe/Middle East"),
    ("haaretz.com", "en", "G", "Europe/Middle East"),
    ("jpost.com", "en", "G", "Europe/Middle East"),
    ("jordantimes.com", "en", "G", "Europe/Middle East"),
    # Group H — Africa (4)
    ("allafrica.com", "en", "H", "Africa"),
    ("africanews.com", "en", "H", "Africa"),
    ("theafricareport.com", "en", "H", "Africa"),
    ("panapress.com", "en", "H", "Africa"),
    # Group I — Latin America (8)
    ("clarin.com", "es", "I", "Latin America"),
    ("lanacion.com.ar", "es", "I", "Latin America"),
    ("folha.uol.com.br", "pt", "I", "Latin America"),
    ("oglobo.globo.com", "pt", "I", "Latin America"),
    ("elmercurio.com", "es", "I", "Latin America"),
    ("biobiochile.cl", "es", "I", "Latin America"),
    ("eltiempo.com", "es", "I", "Latin America"),
    ("elcomercio.pe", "es", "I", "Latin America"),
    # Group J — Russia/Central Asia (4)
    ("gogo.mn", "mn", "J", "Russia/Central Asia"),
    ("ria.ru", "ru", "J", "Russia/Central Asia"),
    ("rg.ru", "ru", "J", "Russia/Central Asia"),
    ("rbc.ru", "ru", "J", "Russia/Central Asia"),
]

# Group-level metadata for the split_sites_by_group workflow classification
_GROUP_META: dict[str, dict[str, str]] = {
    "A": {"strategy_group": "kr-major", "description": "Korean Major Dailies"},
    "B": {"strategy_group": "kr-major", "description": "Korean Economy"},
    "C": {"strategy_group": "kr-major", "description": "Korean Niche"},
    "D": {"strategy_group": "kr-tech", "description": "Korean IT/Science"},
    "E": {"strategy_group": "english", "description": "US/English Major"},
    "F": {"strategy_group": "asia-pacific", "description": "Asia-Pacific"},
    "G": {"strategy_group": "europe-me", "description": "Europe/Middle East"},
    "H": {"strategy_group": "multilingual", "description": "Africa"},
    "I": {"strategy_group": "multilingual", "description": "Latin America"},
    "J": {"strategy_group": "multilingual", "description": "Russia/Central Asia"},
}


def _emit(result: dict[str, Any]) -> None:
    """Print JSON result to stdout and exit."""
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()  # trailing newline
    sys.exit(0 if result.get("valid") else 1)


def _try_load_yaml(path: str) -> list[dict[str, Any]] | None:
    """Attempt to load sites from a sources.yaml file. Returns None on failure."""
    if not os.path.isfile(path):
        return None
    try:
        import yaml  # noqa: F401 — PyYAML is an optional dependency
    except ImportError:
        return None
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return None
    sites_raw = data.get("sites") or data.get("sources") or []
    if not isinstance(sites_raw, list) or len(sites_raw) == 0:
        return None
    sites: list[dict[str, Any]] = []
    for entry in sites_raw:
        if not isinstance(entry, dict):
            continue
        domain = entry.get("url") or entry.get("domain") or ""
        # Strip protocol prefix to normalize
        domain = re.sub(r"^https?://", "", domain).rstrip("/")
        if not domain:
            continue
        sites.append({
            "domain": domain,
            "language": entry.get("language", "unknown"),
            "group": entry.get("group", "unknown"),
            "group_label": entry.get("group_label", ""),
            "strategy_group": entry.get("strategy_group", ""),
            "source": "sources.yaml",
        })
    return sites if sites else None


def _extract_from_prd(prd_path: str) -> list[dict[str, Any]] | None:
    """Extract site URLs from PRD markdown tables (sections 4.1 and 4.2).

    Looks for table rows containing domain patterns like `xxx.yyy` inside
    bold markers or parentheses.
    """
    if not os.path.isfile(prd_path):
        return None
    with open(prd_path, encoding="utf-8") as f:
        content = f.read()

    # Regex to find domains in PRD table rows — matches patterns like
    # (chosun.com), **chosun.com**, or bare domain in table cells.
    domain_re = re.compile(
        r"(?:\*\*|\()?"
        r"((?:www\d?\.)?[a-z0-9][-a-z0-9]*\.[a-z]{2,}(?:\.[a-z]{2,})?(?:/[a-z]+)?)"
        r"(?:\*\*|\))?"
    )

    # We only want domains from sections 4.1 and 4.2 (data sources)
    section_4 = ""
    in_section = False
    for line in content.splitlines():
        if re.match(r"^##\s+4\.\s", line):
            in_section = True
        elif re.match(r"^##\s+5\.\s", line):
            in_section = False
        if in_section:
            section_4 += line + "\n"

    found_domains: list[str] = []
    for line in section_4.splitlines():
        if "|" not in line:
            continue
        for m in domain_re.finditer(line):
            d = m.group(1).lower()
            # Filter out obvious non-news domains
            if d in ("sitemap.xml", "rss.xml"):
                continue
            if d not in found_domains:
                found_domains.append(d)

    if not found_domains:
        return None

    # Map found PRD domains to group info via canonical registry
    canonical_map = {s[0]: s for s in _CANONICAL_SITES}
    sites: list[dict[str, Any]] = []
    for domain in found_domains:
        if domain in canonical_map:
            _, lang, group, group_label = canonical_map[domain]
            meta = _GROUP_META.get(group, {})
            sites.append({
                "domain": domain,
                "language": lang,
                "group": group,
                "group_label": group_label,
                "strategy_group": meta.get("strategy_group", ""),
                "source": "prd",
            })
        else:
            sites.append({
                "domain": domain,
                "language": "unknown",
                "group": "unknown",
                "group_label": "",
                "strategy_group": "",
                "source": "prd",
            })

    return sites if sites else None


def _build_canonical_sites() -> list[dict[str, Any]]:
    """Build the full 121-site list from the hardcoded canonical registry."""
    sites: list[dict[str, Any]] = []
    for domain, lang, group, group_label in _CANONICAL_SITES:
        meta = _GROUP_META.get(group, {})
        sites.append({
            "domain": domain,
            "language": lang,
            "group": group,
            "group_label": group_label,
            "strategy_group": meta.get("strategy_group", ""),
            "source": "canonical",
        })
    return sites


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract site URLs from PRD or sources.yaml for agent context injection."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Root directory of the project.",
    )
    parser.add_argument(
        "--prd",
        default=None,
        help="Path to PRD.md relative to project-dir (default: coding-resource/PRD.md).",
    )
    parser.add_argument(
        "--sources",
        default=None,
        help="Path to sources.yaml relative to project-dir (default: data/config/sources.yaml).",
    )
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    if not os.path.isdir(project_dir):
        _emit({"valid": False, "error": f"Project directory not found: {project_dir}"})

    # Priority 1: sources.yaml (if it exists and has content)
    sources_path = os.path.join(
        project_dir, args.sources if args.sources else "data/config/sources.yaml"
    )
    sites = _try_load_yaml(sources_path)
    data_source = "sources.yaml"

    # Priority 2: Canonical list (authoritative 121-site set from workflow.md),
    # enriched with PRD cross-reference data.
    # The PRD sections 4.1/4.2 only list ~14 sites as initial proposals, while
    # the full 121-site target is defined in workflow.md. The canonical registry
    # is therefore the primary source, and the PRD provides supplementary info.
    if sites is None:
        prd_path = os.path.join(
            project_dir, args.prd if args.prd else "coding-resource/PRD.md"
        )
        prd_sites = _extract_from_prd(prd_path)
        prd_domains = {s["domain"] for s in prd_sites} if prd_sites else set()

        sites = _build_canonical_sites()
        # Mark which canonical sites were also found in the PRD
        for site in sites:
            if site["domain"] in prd_domains:
                site["in_prd"] = True
            else:
                site["in_prd"] = False

        data_source = "canonical" if not prd_domains else "canonical+prd"

    # Build group summary
    group_counts: dict[str, int] = {}
    strategy_counts: dict[str, int] = {}
    for site in sites:
        g = site.get("group", "unknown")
        sg = site.get("strategy_group", "unknown")
        group_counts[g] = group_counts.get(g, 0) + 1
        strategy_counts[sg] = strategy_counts.get(sg, 0) + 1

    _emit({
        "valid": True,
        "data_source": data_source,
        "total_sites": len(sites),
        "group_counts": group_counts,
        "strategy_group_counts": strategy_counts,
        "sites": sites,
    })


if __name__ == "__main__":
    main()
