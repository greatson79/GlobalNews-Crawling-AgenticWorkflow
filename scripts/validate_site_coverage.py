#!/usr/bin/env python3
"""Site Coverage Validator — P1 deterministic 121-site coverage check.

Verifies that a document mentions all 121 target news sites.
Used after Steps 1, 6, 11 to prevent "all 121 sites covered" hallucination.

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
# Fallback 121 site domains (used only when runtime SOT unavailable)
# P1: Normal operation derives sites from data/config/sources.yaml
# via _load_sites_from_runtime_sot(), preventing hardcoded list desync.
# ---------------------------------------------------------------------------
_FALLBACK_SITES = [
    # Group A: Korean Major Dailies (5)
    "www.chosun.com", "www.joongang.co.kr", "www.donga.com", "www.hani.co.kr", "www.yna.co.kr",
    # Group B: Korean Economy (4)
    "www.mk.co.kr", "www.hankyung.com", "www.fnnews.com", "www.mt.co.kr",
    # Group C: Korean Niche (3)
    "www.nocutnews.co.kr", "www.kmib.co.kr", "www.ohmynews.com",
    # Group D: Korean IT/Science (10)
    "www.38north.org", "www.bloter.net", "www.etnews.com", "www.sciencetimes.co.kr",
    "www.zdnet.co.kr", "www.irobotnews.com", "www.techneedle.com", "insight.co.kr",
    "stratechery.com", "www.techmeme.com",
    # Group E: English (22)
    "www.marketwatch.com", "www.voakorea.com", "www.huffpost.com", "www.nytimes.com",
    "www.ft.com", "www.wsj.com", "www.latimes.com", "www.buzzfeed.com",
    "nationalpost.com", "edition.cnn.com", "www.bloomberg.com", "afmedios.com",
    "www.wired.com", "www.investing.com", "qz.com", "www.bbc.com",
    "www.theguardian.com", "www.thetimes.com", "www.telegraph.co.uk", "www.politico.eu",
    "www.euractiv.com", "www.natureasia.com",
    # Group F: Asia-Pacific (23)
    "www.people.com.cn", "www.globaltimes.cn", "www.scmp.com", "www.taiwannews.com.tw",
    "www.yomiuri.co.jp", "www.thehindu.com", "mainichi.jp", "www.asahi.com",
    "news.yahoo.co.jp", "timesofindia.indiatimes.com", "www.hindustantimes.com",
    "economictimes.indiatimes.com", "indianexpress.com", "www.philstar.com",
    "mb.com.ph", "www.inquirer.net", "www.thejakartapost.com", "en.antaranews.com",
    "en.tempo.co", "focustaiwan.tw", "www.taipeitimes.com", "e.vnexpress.net",
    "vietnamnews.vn",
    # Group G: Europe/ME (38)
    "www.thesun.co.uk", "www.bild.de", "www.lemonde.fr", "www.themoscowtimes.com",
    "www.arabnews.com", "www.aljazeera.com", "www.israelhayom.com", "www.euronews.com",
    "www.spiegel.de", "www.sueddeutsche.de", "www.welt.de", "www.faz.net",
    "www.corriere.it", "www.repubblica.it", "www.ansa.it", "elpais.com",
    "www.elmundo.es", "www.abc.es", "www.lavanguardia.com", "www.lefigaro.fr",
    "www.liberation.fr", "www.france24.com", "www.ouest-france.fr", "wyborcza.pl",
    "www.pap.pl", "www.idnes.cz", "www.intellinews.com", "balkaninsight.com",
    "centraleuropeantimes.com", "www.aftonbladet.se", "www.tv2.no", "yle.fi",
    "icelandmonitor.mbl.is", "www.middleeasteye.net", "www.al-monitor.com",
    "www.haaretz.com", "www.jpost.com", "jordantimes.com",
    # Group H: Africa (4)
    "allafrica.com", "www.africanews.com", "www.theafricareport.com", "www.panapress.com",
    # Group I: Latin America (8)
    "www.clarin.com", "www.lanacion.com.ar", "www.folha.uol.com.br", "oglobo.globo.com",
    "digital.elmercurio.com", "www.biobiochile.cl", "www.eltiempo.com", "elcomercio.pe",
    # Group J: Russia/Central Asia (4)
    "mongolia.gogo.mn", "ria.ru", "rg.ru", "www.rbc.ru",
]

# Backward compatibility
DEFAULT_SITES = _FALLBACK_SITES


def _load_sites_from_runtime_sot(project_dir):
    """P1: Load site domains from runtime SOT (data/config/sources.yaml).

    Programmatic derivation prevents hardcoded domain list desync.
    Returns list of domain strings, or None if SOT unavailable.
    """
    sot_path = os.path.join(project_dir, "data", "config", "sources.yaml")
    if not os.path.exists(sot_path):
        return None
    try:
        import yaml
        with open(sot_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        sources = data.get("sources", {})
        if isinstance(sources, dict) and sources:
            domains = []
            for _sid, cfg in sources.items():
                if isinstance(cfg, dict):
                    url = cfg.get("url", "")
                    domain = re.sub(r'^https?://(www\.)?', '', str(url)).rstrip('/').split('/')[0]
                    if domain:
                        domains.append(domain)
            return domains if domains else None
    except Exception:
        pass
    return None


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

    # Load expected sites — explicit arg > runtime SOT > hardcoded fallback
    sites = None
    sot_derived = False
    if sources_yaml:
        yaml_path = os.path.join(project_dir, sources_yaml) if not os.path.isabs(sources_yaml) else sources_yaml
        sites = _load_sites_from_yaml(yaml_path)
        if sites:
            sot_derived = True

    if not sites:
        sites = _load_sites_from_runtime_sot(project_dir)
        if sites:
            sot_derived = True

    if not sites:
        sites = _FALLBACK_SITES
        sot_derived = False

    result["total_expected"] = len(sites)
    result["sot_derived"] = sot_derived
    if not sot_derived:
        result["warnings"].append(
            "SC-SOT: Using hardcoded fallback list — runtime SOT (sources.yaml) "
            "not available. Fallback may be stale."
        )

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
    parser.add_argument(
        "--require-sot", action="store_true",
        help="Fail if runtime SOT (sources.yaml) is not available"
    )
    args = parser.parse_args()

    result = validate_coverage(args.project_dir, args.file, args.sources_yaml)

    # --require-sot: fail if using fallback
    if args.require_sot and not result.get("sot_derived", False):
        result["valid"] = False
        result["warnings"].append(
            "SC-REQUIRE-SOT: --require-sot specified but runtime SOT not available"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
