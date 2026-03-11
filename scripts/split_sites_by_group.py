#!/usr/bin/env python3
"""Split sites into 4 groups for parallel strategy design.

Usage:
    python3 scripts/split_sites_by_group.py --project-dir .

Output: 4 JSON files in planning/team-input/
    - group-kr-major.json   (Groups A+B+C = 12 Korean major/economy/niche sites)
    - group-kr-tech.json    (Group D = 10 Korean IT/Science sites)
    - group-english.json    (Group E = 22 US/English major sites)
    - group-multilingual.json (Groups F-J = 77 Asia-Pacific + Europe/ME + Africa + LatAm + Russia sites)

This is a P1 pre-processing script: deterministic extraction, no LLM inference.
It divides the 121 target sites into 4 balanced groups for the crawl-strategy-team
(Step 6). Each group file includes per-site metadata and, if available, the
reconnaissance data from Step 1.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any


def _emit(result: dict[str, Any]) -> None:
    """Print JSON result to stdout and exit."""
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    sys.exit(0 if result.get("valid") else 1)


# -- Canonical site registry (same as extract_site_urls.py) ------------------
_SITES: list[dict[str, Any]] = [
    # Group A — Korean Major Dailies (5)
    {"domain": "chosun.com", "language": "ko", "group": "A", "label": "Korean Major Dailies", "notes": "Infinite scroll, dynamic loading"},
    {"domain": "joongang.co.kr", "language": "ko", "group": "A", "label": "Korean Major Dailies", "notes": "Pagination"},
    {"domain": "donga.com", "language": "ko", "group": "A", "label": "Korean Major Dailies", "notes": ""},
    {"domain": "hani.co.kr", "language": "ko", "group": "A", "label": "Korean Major Dailies", "notes": "Structural HTML, low difficulty"},
    {"domain": "yna.co.kr", "language": "ko", "group": "A", "label": "Korean Major Dailies", "notes": "Rich sitemap, low difficulty"},
    # Group B — Korean Economy (4)
    {"domain": "mk.co.kr", "language": "ko", "group": "B", "label": "Korean Economy", "notes": ""},
    {"domain": "hankyung.com", "language": "ko", "group": "B", "label": "Korean Economy", "notes": "Paywall, dynamic loading"},
    {"domain": "fnnews.com", "language": "ko", "group": "B", "label": "Korean Economy", "notes": ""},
    {"domain": "mt.co.kr", "language": "ko", "group": "B", "label": "Korean Economy", "notes": ""},
    # Group C — Korean Niche (3)
    {"domain": "nocutnews.co.kr", "language": "ko", "group": "C", "label": "Korean Niche", "notes": ""},
    {"domain": "kmib.co.kr", "language": "ko", "group": "C", "label": "Korean Niche", "notes": ""},
    {"domain": "ohmynews.com", "language": "ko", "group": "C", "label": "Korean Niche", "notes": ""},
    # Group D — Korean IT/Science (10)
    {"domain": "38north.org", "language": "en", "group": "D", "label": "Korean IT/Science", "notes": "English-language analysis site"},
    {"domain": "bloter.net", "language": "ko", "group": "D", "label": "Korean IT/Science", "notes": ""},
    {"domain": "etnews.com", "language": "ko", "group": "D", "label": "Korean IT/Science", "notes": ""},
    {"domain": "sciencetimes.co.kr", "language": "ko", "group": "D", "label": "Korean IT/Science", "notes": ""},
    {"domain": "zdnet.co.kr", "language": "ko", "group": "D", "label": "Korean IT/Science", "notes": ""},
    {"domain": "irobotnews.com", "language": "ko", "group": "D", "label": "Korean IT/Science", "notes": ""},
    {"domain": "techneedle.com", "language": "ko", "group": "D", "label": "Korean IT/Science", "notes": ""},
    {"domain": "insight.co.kr", "language": "ko", "group": "D", "label": "Korean IT/Science", "notes": ""},
    {"domain": "stratechery.com", "language": "en", "group": "D", "label": "Korean IT/Science", "notes": "English-language tech analysis"},
    {"domain": "techmeme.com", "language": "en", "group": "D", "label": "Korean IT/Science", "notes": "English-language tech aggregator"},
    # Group E — US/English Major (22)
    {"domain": "marketwatch.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "voakorea.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "huffingtonpost.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "nytimes.com", "language": "en", "group": "E", "label": "US/English Major", "notes": "Paywall"},
    {"domain": "ft.com", "language": "en", "group": "E", "label": "US/English Major", "notes": "Paywall"},
    {"domain": "wsj.com", "language": "en", "group": "E", "label": "US/English Major", "notes": "Paywall"},
    {"domain": "latimes.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "buzzfeed.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "nationalpost.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "edition.cnn.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "bloomberg.com", "language": "en", "group": "E", "label": "US/English Major", "notes": "Paywall"},
    {"domain": "afmedios.com", "language": "es", "group": "E", "label": "US/English Major", "notes": "Spanish-language"},
    {"domain": "wired.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "investing.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "qz.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "bbc.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "theguardian.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "thetimes.com", "language": "en", "group": "E", "label": "US/English Major", "notes": "Paywall"},
    {"domain": "telegraph.co.uk", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "politico.eu", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "euractiv.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    {"domain": "natureasia.com", "language": "en", "group": "E", "label": "US/English Major", "notes": ""},
    # Group F — Asia-Pacific (23)
    {"domain": "people.com.cn", "language": "zh", "group": "F", "label": "Asia-Pacific", "notes": "Chinese encoding (GB2312/UTF-8)"},
    {"domain": "globaltimes.cn", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Chinese state media, English edition"},
    {"domain": "scmp.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "South China Morning Post"},
    {"domain": "taiwannews.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": ""},
    {"domain": "yomiuri.co.jp", "language": "ja", "group": "F", "label": "Asia-Pacific", "notes": "Japanese encoding"},
    {"domain": "thehindu.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": ""},
    {"domain": "mainichi.jp", "language": "ja", "group": "F", "label": "Asia-Pacific", "notes": "Japanese"},
    {"domain": "asahi.com", "language": "ja", "group": "F", "label": "Asia-Pacific", "notes": "Japanese"},
    {"domain": "yahoo.co.jp", "language": "ja", "group": "F", "label": "Asia-Pacific", "notes": "Japanese news portal"},
    {"domain": "timesofindia.indiatimes.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Indian English"},
    {"domain": "hindustantimes.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Indian English"},
    {"domain": "economictimes.indiatimes.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Indian business"},
    {"domain": "indianexpress.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Indian English"},
    {"domain": "philstar.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Philippines"},
    {"domain": "mb.com.ph", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Philippines Manila Bulletin"},
    {"domain": "inquirer.net", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Philippines"},
    {"domain": "thejakartapost.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Indonesia"},
    {"domain": "antaranews.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Indonesia Antara"},
    {"domain": "tempo.co", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Indonesia"},
    {"domain": "focustaiwan.tw", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Taiwan CNA"},
    {"domain": "taipeitimes.com", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Taiwan"},
    {"domain": "vnexpress.net", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Vietnam English edition"},
    {"domain": "vietnamnews.vn", "language": "en", "group": "F", "label": "Asia-Pacific", "notes": "Vietnam"},
    # Group G — Europe/Middle East (38)
    {"domain": "thesun.co.uk", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "UK tabloid"},
    {"domain": "bild.de", "language": "de", "group": "G", "label": "Europe/Middle East", "notes": "German"},
    {"domain": "lemonde.fr", "language": "fr", "group": "G", "label": "Europe/Middle East", "notes": "French"},
    {"domain": "themoscowtimes.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": ""},
    {"domain": "arabnews.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Arabic+English, potential RTL"},
    {"domain": "aljazeera.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Arabic+English"},
    {"domain": "israelhayom.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Hebrew+English, potential RTL"},
    {"domain": "euronews.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Multilingual"},
    {"domain": "spiegel.de", "language": "de", "group": "G", "label": "Europe/Middle East", "notes": "German"},
    {"domain": "sueddeutsche.de", "language": "de", "group": "G", "label": "Europe/Middle East", "notes": "German"},
    {"domain": "welt.de", "language": "de", "group": "G", "label": "Europe/Middle East", "notes": "German"},
    {"domain": "faz.net", "language": "de", "group": "G", "label": "Europe/Middle East", "notes": "German"},
    {"domain": "corriere.it", "language": "it", "group": "G", "label": "Europe/Middle East", "notes": "Italian"},
    {"domain": "repubblica.it", "language": "it", "group": "G", "label": "Europe/Middle East", "notes": "Italian"},
    {"domain": "ansa.it", "language": "it", "group": "G", "label": "Europe/Middle East", "notes": "Italian wire service"},
    {"domain": "elpais.com", "language": "es", "group": "G", "label": "Europe/Middle East", "notes": "Spanish"},
    {"domain": "elmundo.es", "language": "es", "group": "G", "label": "Europe/Middle East", "notes": "Spanish"},
    {"domain": "abc.es", "language": "es", "group": "G", "label": "Europe/Middle East", "notes": "Spanish"},
    {"domain": "lavanguardia.com", "language": "es", "group": "G", "label": "Europe/Middle East", "notes": "Spanish"},
    {"domain": "lefigaro.fr", "language": "fr", "group": "G", "label": "Europe/Middle East", "notes": "French"},
    {"domain": "liberation.fr", "language": "fr", "group": "G", "label": "Europe/Middle East", "notes": "French"},
    {"domain": "france24.com", "language": "fr", "group": "G", "label": "Europe/Middle East", "notes": "French multilingual"},
    {"domain": "ouest-france.fr", "language": "fr", "group": "G", "label": "Europe/Middle East", "notes": "French regional"},
    {"domain": "wyborcza.pl", "language": "pl", "group": "G", "label": "Europe/Middle East", "notes": "Polish"},
    {"domain": "pap.pl", "language": "pl", "group": "G", "label": "Europe/Middle East", "notes": "Polish wire service"},
    {"domain": "idnes.cz", "language": "cs", "group": "G", "label": "Europe/Middle East", "notes": "Czech"},
    {"domain": "intellinews.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Eastern Europe focus"},
    {"domain": "balkaninsight.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Balkans focus"},
    {"domain": "centraleuropeantimes.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Central Europe"},
    {"domain": "aftonbladet.se", "language": "sv", "group": "G", "label": "Europe/Middle East", "notes": "Swedish"},
    {"domain": "tv2.no", "language": "no", "group": "G", "label": "Europe/Middle East", "notes": "Norwegian"},
    {"domain": "yle.fi", "language": "fi", "group": "G", "label": "Europe/Middle East", "notes": "Finnish"},
    {"domain": "icelandmonitor.mbl.is", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Icelandic English"},
    {"domain": "middleeasteye.net", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Middle East focus"},
    {"domain": "al-monitor.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Middle East focus"},
    {"domain": "haaretz.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Israeli English"},
    {"domain": "jpost.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Israeli English"},
    {"domain": "jordantimes.com", "language": "en", "group": "G", "label": "Europe/Middle East", "notes": "Jordanian English"},
    # Group H — Africa (4)
    {"domain": "allafrica.com", "language": "en", "group": "H", "label": "Africa", "notes": "Pan-African aggregator"},
    {"domain": "africanews.com", "language": "en", "group": "H", "label": "Africa", "notes": "Euronews Africa"},
    {"domain": "theafricareport.com", "language": "en", "group": "H", "label": "Africa", "notes": ""},
    {"domain": "panapress.com", "language": "en", "group": "H", "label": "Africa", "notes": "Pan-African wire"},
    # Group I — Latin America (8)
    {"domain": "clarin.com", "language": "es", "group": "I", "label": "Latin America", "notes": "Argentine Spanish"},
    {"domain": "lanacion.com.ar", "language": "es", "group": "I", "label": "Latin America", "notes": "Argentine Spanish"},
    {"domain": "folha.uol.com.br", "language": "pt", "group": "I", "label": "Latin America", "notes": "Brazilian Portuguese"},
    {"domain": "oglobo.globo.com", "language": "pt", "group": "I", "label": "Latin America", "notes": "Brazilian Portuguese"},
    {"domain": "elmercurio.com", "language": "es", "group": "I", "label": "Latin America", "notes": "Chilean Spanish"},
    {"domain": "biobiochile.cl", "language": "es", "group": "I", "label": "Latin America", "notes": "Chilean Spanish"},
    {"domain": "eltiempo.com", "language": "es", "group": "I", "label": "Latin America", "notes": "Colombian Spanish"},
    {"domain": "elcomercio.pe", "language": "es", "group": "I", "label": "Latin America", "notes": "Peruvian Spanish"},
    # Group J — Russia/Central Asia (4)
    {"domain": "gogo.mn", "language": "mn", "group": "J", "label": "Russia/Central Asia", "notes": "Mongolian"},
    {"domain": "ria.ru", "language": "ru", "group": "J", "label": "Russia/Central Asia", "notes": "Russian state media"},
    {"domain": "rg.ru", "language": "ru", "group": "J", "label": "Russia/Central Asia", "notes": "Russian government"},
    {"domain": "rbc.ru", "language": "ru", "group": "J", "label": "Russia/Central Asia", "notes": "Russian business"},
]

# Strategy group definitions:
# These map to the 4 crawl-strategy-team members in workflow.md Step 6.
_STRATEGY_GROUPS: dict[str, dict[str, Any]] = {
    "kr-major": {
        "filename": "group-kr-major.json",
        "source_groups": ["A", "B", "C"],
        "description": "Korean major dailies, economy, and niche sites",
        "agent": "@crawl-strategist-kr",
        "focus": "Korean language, section navigation, dynamic loading, paywall (hankyung)",
    },
    "kr-tech": {
        "filename": "group-kr-tech.json",
        "source_groups": ["D"],
        "description": "Korean IT/Science specialty sites",
        "agent": "@crawl-strategist-kr",
        "focus": "Simpler structures, tech-focused content, mixed Korean/English",
    },
    "english": {
        "filename": "group-english.json",
        "source_groups": ["E"],
        "description": "US/English major news sites",
        "agent": "@crawl-strategist-en",
        "focus": "Fundus/Trafilatura compatibility, paywall handling (nytimes/ft/wsj/bloomberg)",
    },
    "multilingual": {
        "filename": "group-multilingual.json",
        "source_groups": ["F", "G", "H", "I", "J"],
        "description": "Asia-Pacific + Europe/ME + Africa + Latin America + Russia/Central Asia multilingual sites",
        "agent": "@crawl-strategist-asia + @crawl-strategist-global",
        "focus": "Character encoding, RTL text, geo-blocking, multi-language sections, Spanish/Portuguese/Russian",
    },
}


def _try_enrich_from_recon(
    project_dir: str,
    sites: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Try to enrich site entries with Step 1 reconnaissance data.

    Reads research/site-reconnaissance.md and attempts to extract per-site
    data (RSS availability, sitemap, blocking level, etc.) from markdown tables.
    If the file does not exist or parsing fails, returns sites unchanged.
    """
    recon_path = os.path.join(project_dir, "research", "site-reconnaissance.md")
    if not os.path.isfile(recon_path):
        return sites

    with open(recon_path, encoding="utf-8") as f:
        recon_content = f.read()

    # Build a simple per-domain lookup from table rows
    # Look for rows containing known domains
    domain_data: dict[str, str] = {}
    for line in recon_content.splitlines():
        if "|" not in line:
            continue
        for site in sites:
            domain = site["domain"]
            # Check if this table row mentions this domain
            if domain in line or domain.split(".")[0] in line.lower():
                domain_data[domain] = line.strip()

    # Attach raw recon row to each site for the agent to parse
    for site in sites:
        row = domain_data.get(site["domain"])
        if row:
            site["recon_row"] = row

    return sites


def _try_enrich_from_sources_yaml(
    project_dir: str,
    sites: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Try to enrich from sources.yaml if it exists."""
    sources_path = os.path.join(project_dir, "data", "config", "sources.yaml")
    if not os.path.isfile(sources_path):
        return sites

    try:
        import yaml
    except ImportError:
        return sites

    with open(sources_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return sites

    sources_list = data.get("sites") or data.get("sources") or []
    if not isinstance(sources_list, list):
        return sites

    # Build domain -> config mapping
    config_map: dict[str, dict[str, Any]] = {}
    for entry in sources_list:
        if not isinstance(entry, dict):
            continue
        domain = entry.get("url") or entry.get("domain") or ""
        domain = re.sub(r"^https?://", "", domain).rstrip("/")
        if domain:
            config_map[domain] = entry

    for site in sites:
        cfg = config_map.get(site["domain"])
        if cfg:
            # Merge selected fields
            for key in ("rss_urls", "sitemap_url", "sections", "difficulty_tier",
                        "rate_limit_seconds", "anti_block_tier", "selectors"):
                if key in cfg:
                    site[key] = cfg[key]

    return sites


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split 121 sites into 4 balanced groups for crawl-strategy-team."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Root directory of the project.",
    )
    parser.add_argument(
        "--output-dir",
        default="planning/team-input",
        help="Output directory relative to project-dir.",
    )
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    if not os.path.isdir(project_dir):
        _emit({"valid": False, "error": f"Project directory not found: {project_dir}"})

    output_dir = os.path.join(project_dir, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Enrich sites with any available reconnaissance / sources.yaml data
    sites = list(_SITES)  # shallow copy
    sites = _try_enrich_from_recon(project_dir, sites)
    sites = _try_enrich_from_sources_yaml(project_dir, sites)

    # Split into strategy groups
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output_files: dict[str, str] = {}
    group_summary: dict[str, int] = {}

    for sg_key, sg_meta in _STRATEGY_GROUPS.items():
        source_groups = sg_meta["source_groups"]
        group_sites = [s for s in sites if s["group"] in source_groups]
        group_summary[sg_key] = len(group_sites)

        group_doc = {
            "generated": now,
            "strategy_group": sg_key,
            "description": sg_meta["description"],
            "assigned_agent": sg_meta["agent"],
            "focus_areas": sg_meta["focus"],
            "site_count": len(group_sites),
            "sites": group_sites,
        }

        filename = sg_meta["filename"]
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(group_doc, f, ensure_ascii=False, indent=2)
            f.write("\n")
        output_files[sg_key] = filepath

    total = sum(group_summary.values())

    _emit({
        "valid": True,
        "total_sites": total,
        "group_counts": group_summary,
        "output_files": output_files,
        "output_dir": output_dir,
    })


if __name__ == "__main__":
    main()
