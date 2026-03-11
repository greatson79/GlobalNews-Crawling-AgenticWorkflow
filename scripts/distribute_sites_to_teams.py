#!/usr/bin/env python3
"""Distribute 121 sites to 4 adapter-dev team members.

Usage: python3 scripts/distribute_sites_to_teams.py --project-dir .

Reads:
  - planning/crawling-strategies.md

Output:
  - planning/team-input/adapters-kr-major.json    (12 sites — Groups A+B+C)
  - planning/team-input/adapters-kr-tech.json     (10 sites — Group D)
  - planning/team-input/adapters-english.json     (22 sites — Group E)
  - planning/team-input/adapters-multilingual.json (77 sites — Groups F+G+H+I+J)

Parses the crawling strategies document, splits sites by group,
and includes per-site strategy metadata in each group file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Site group definitions (fallback when runtime SOT unavailable)
# ---------------------------------------------------------------------------

# Fallback site lists — used only when data/config/sources.yaml is missing.
# P1: Normal operation derives groups from runtime SOT programmatically
# via _derive_groups_from_sot(), preventing hardcoded list desync.
_FALLBACK_GROUPS: dict[str, list[dict[str, str]]] = {
    "kr-major": [
        # Group A — Korean Major Dailies (5)
        {"domain": "chosun.com", "name": "Chosun Ilbo"},
        {"domain": "donga.com", "name": "Dong-A Ilbo"},
        {"domain": "hani.co.kr", "name": "Hankyoreh"},
        {"domain": "joongang.co.kr", "name": "JoongAng Ilbo"},
        {"domain": "yna.co.kr", "name": "Yonhap News Agency"},
        # Group B — Korean Economy (4)
        {"domain": "fnnews.com", "name": "Financial News"},
        {"domain": "hankyung.com", "name": "Korea Economic Daily"},
        {"domain": "mk.co.kr", "name": "Maeil Business Newspaper"},
        {"domain": "mt.co.kr", "name": "Money Today"},
        # Group C — Korean Niche (3)
        {"domain": "kmib.co.kr", "name": "Kookmin Ilbo"},
        {"domain": "nocutnews.co.kr", "name": "NoCut News"},
        {"domain": "ohmynews.com", "name": "OhmyNews"},
    ],
    "kr-tech": [
        # Group D — Korean IT/Tech + Specialist (10)
        {"domain": "38north.org", "name": "38 North"},
        {"domain": "bloter.net", "name": "Bloter"},
        {"domain": "etnews.com", "name": "Electronic Times"},
        {"domain": "insight.co.kr", "name": "Insight Korea"},
        {"domain": "irobotnews.com", "name": "iRobot News"},
        {"domain": "sciencetimes.co.kr", "name": "Science Times"},
        {"domain": "stratechery.com", "name": "Stratechery"},
        {"domain": "techmeme.com", "name": "Techmeme"},
        {"domain": "techneedle.com", "name": "TechNeedle"},
        {"domain": "zdnet.co.kr", "name": "ZDNet Korea"},
    ],
    "english": [
        # Group E — English-language Global (22)
        {"domain": "afmedios.com", "name": "AF Medios"},
        {"domain": "bbc.com", "name": "BBC News"},
        {"domain": "bloomberg.com", "name": "Bloomberg"},
        {"domain": "buzzfeed.com", "name": "BuzzFeed"},
        {"domain": "edition.cnn.com", "name": "CNN"},
        {"domain": "euractiv.com", "name": "Euractiv"},
        {"domain": "ft.com", "name": "Financial Times"},
        {"domain": "huffpost.com", "name": "HuffPost"},
        {"domain": "investing.com", "name": "Investing.com"},
        {"domain": "latimes.com", "name": "Los Angeles Times"},
        {"domain": "marketwatch.com", "name": "MarketWatch"},
        {"domain": "nationalpost.com", "name": "National Post"},
        {"domain": "natureasia.com", "name": "Nature Asia"},
        {"domain": "nytimes.com", "name": "The New York Times"},
        {"domain": "politico.eu", "name": "Politico Europe"},
        {"domain": "qz.com", "name": "Quartz"},
        {"domain": "telegraph.co.uk", "name": "The Telegraph"},
        {"domain": "theguardian.com", "name": "The Guardian"},
        {"domain": "thetimes.com", "name": "The Times"},
        {"domain": "voakorea.com", "name": "VOA Korea"},
        {"domain": "wired.com", "name": "Wired"},
        {"domain": "wsj.com", "name": "Wall Street Journal"},
    ],
    "multilingual": [
        # Group F — Asia-Pacific (23)
        {"domain": "en.antaranews.com", "name": "Antara News", "language": "en"},
        {"domain": "asahi.com", "name": "Asahi Shimbun", "language": "ja"},
        {"domain": "economictimes.indiatimes.com", "name": "Economic Times India", "language": "en"},
        {"domain": "focustaiwan.tw", "name": "Focus Taiwan", "language": "en"},
        {"domain": "globaltimes.cn", "name": "Global Times", "language": "en"},
        {"domain": "hindustantimes.com", "name": "Hindustan Times", "language": "en"},
        {"domain": "indianexpress.com", "name": "Indian Express", "language": "en"},
        {"domain": "inquirer.net", "name": "Philippine Daily Inquirer", "language": "en"},
        {"domain": "thejakartapost.com", "name": "The Jakarta Post", "language": "en"},
        {"domain": "mainichi.jp", "name": "Mainichi Shimbun", "language": "en"},
        {"domain": "mb.com.ph", "name": "Manila Bulletin", "language": "en"},
        {"domain": "people.com.cn", "name": "People's Daily", "language": "zh"},
        {"domain": "philstar.com", "name": "PhilStar", "language": "en"},
        {"domain": "scmp.com", "name": "South China Morning Post", "language": "en"},
        {"domain": "taipeitimes.com", "name": "Taipei Times", "language": "en"},
        {"domain": "taiwannews.com.tw", "name": "Taiwan News", "language": "en"},
        {"domain": "en.tempo.co", "name": "Tempo Indonesia", "language": "en"},
        {"domain": "thehindu.com", "name": "The Hindu", "language": "en"},
        {"domain": "timesofindia.indiatimes.com", "name": "Times of India", "language": "en"},
        {"domain": "vietnamnews.vn", "name": "Vietnam News", "language": "en"},
        {"domain": "e.vnexpress.net", "name": "VnExpress International", "language": "en"},
        {"domain": "news.yahoo.co.jp", "name": "Yahoo Japan News", "language": "ja"},
        {"domain": "yomiuri.co.jp", "name": "Yomiuri Shimbun", "language": "ja"},
        # Group G — Europe + Middle East (38)
        {"domain": "abc.es", "name": "ABC Spain", "language": "es"},
        {"domain": "aftonbladet.se", "name": "Aftonbladet", "language": "sv"},
        {"domain": "aljazeera.com", "name": "Al Jazeera English", "language": "en"},
        {"domain": "al-monitor.com", "name": "Al-Monitor", "language": "en"},
        {"domain": "ansa.it", "name": "ANSA", "language": "it"},
        {"domain": "arabnews.com", "name": "Arab News", "language": "en"},
        {"domain": "balkaninsight.com", "name": "Balkan Insight (BIRN)", "language": "en"},
        {"domain": "bild.de", "name": "Bild", "language": "de"},
        {"domain": "centraleuropeantimes.com", "name": "Central European Times", "language": "en"},
        {"domain": "corriere.it", "name": "Corriere della Sera", "language": "it"},
        {"domain": "elmundo.es", "name": "El Mundo", "language": "es"},
        {"domain": "elpais.com", "name": "El Pais", "language": "es"},
        {"domain": "euronews.com", "name": "Euronews", "language": "en"},
        {"domain": "faz.net", "name": "Frankfurter Allgemeine", "language": "de"},
        {"domain": "france24.com", "name": "France 24", "language": "fr"},
        {"domain": "haaretz.com", "name": "Haaretz", "language": "en"},
        {"domain": "icelandmonitor.mbl.is", "name": "Iceland Monitor", "language": "en"},
        {"domain": "idnes.cz", "name": "iDNES", "language": "cs"},
        {"domain": "intellinews.com", "name": "Intellinews", "language": "en"},
        {"domain": "israelhayom.com", "name": "Israel Hayom", "language": "en"},
        {"domain": "jordantimes.com", "name": "Jordan Times", "language": "en"},
        {"domain": "jpost.com", "name": "Jerusalem Post", "language": "en"},
        {"domain": "lavanguardia.com", "name": "La Vanguardia", "language": "es"},
        {"domain": "lefigaro.fr", "name": "Le Figaro", "language": "fr"},
        {"domain": "lemonde.fr", "name": "Le Monde", "language": "fr"},
        {"domain": "liberation.fr", "name": "Liberation", "language": "fr"},
        {"domain": "middleeasteye.net", "name": "Middle East Eye", "language": "en"},
        {"domain": "ouest-france.fr", "name": "Ouest-France", "language": "fr"},
        {"domain": "pap.pl", "name": "Polish Press Agency", "language": "pl"},
        {"domain": "repubblica.it", "name": "La Repubblica", "language": "it"},
        {"domain": "spiegel.de", "name": "Der Spiegel", "language": "de"},
        {"domain": "sueddeutsche.de", "name": "Sueddeutsche Zeitung", "language": "de"},
        {"domain": "themoscowtimes.com", "name": "The Moscow Times", "language": "en"},
        {"domain": "thesun.co.uk", "name": "The Sun", "language": "en"},
        {"domain": "tv2.no", "name": "TV2 Norway", "language": "no"},
        {"domain": "welt.de", "name": "Die Welt", "language": "de"},
        {"domain": "wyborcza.pl", "name": "Gazeta Wyborcza", "language": "pl"},
        {"domain": "yle.fi", "name": "YLE News", "language": "en"},
        # Group H — Africa (4)
        {"domain": "africanews.com", "name": "Africanews", "language": "en"},
        {"domain": "allafrica.com", "name": "AllAfrica", "language": "en"},
        {"domain": "panapress.com", "name": "Panapress", "language": "en"},
        {"domain": "theafricareport.com", "name": "The Africa Report", "language": "en"},
        # Group I — Latin America (8)
        {"domain": "biobiochile.cl", "name": "BioBioChile", "language": "es"},
        {"domain": "clarin.com", "name": "Clarin", "language": "es"},
        {"domain": "elcomercio.pe", "name": "El Comercio Peru", "language": "es"},
        {"domain": "digital.elmercurio.com", "name": "El Mercurio", "language": "es"},
        {"domain": "eltiempo.com", "name": "El Tiempo", "language": "es"},
        {"domain": "folha.uol.com.br", "name": "Folha de S.Paulo", "language": "pt"},
        {"domain": "lanacion.com.ar", "name": "La Nacion Argentina", "language": "es"},
        {"domain": "oglobo.globo.com", "name": "O Globo", "language": "pt"},
        # Group J — Russia + Central Asia (4)
        {"domain": "mongolia.gogo.mn", "name": "GoGo Mongolia", "language": "mn"},
        {"domain": "rbc.ru", "name": "RBC", "language": "ru"},
        {"domain": "rg.ru", "name": "Rossiyskaya Gazeta", "language": "ru"},
        {"domain": "ria.ru", "name": "RIA Novosti", "language": "ru"},
    ],
}

# Backward compatibility — tests reference _DEFAULT_GROUPS
_DEFAULT_GROUPS = _FALLBACK_GROUPS


# ---------------------------------------------------------------------------
# P1: SOT-derived site groups (prevents hardcoded list desync)
# ---------------------------------------------------------------------------

# D-7 (11): Map Group letters (A-J) to team keys — sync with:
#   constants.py CRAWL_GROUPS (A-J definitions),
#   data/config/sources.yaml group field values
_GROUP_TO_TEAM = {
    "A": "kr-major", "B": "kr-major", "C": "kr-major",
    "D": "kr-tech",
    "E": "english",
    "F": "multilingual", "G": "multilingual",
    "H": "multilingual", "I": "multilingual", "J": "multilingual",
}


def _derive_groups_from_sot(project_dir: Path) -> dict[str, list[dict[str, str]]] | None:
    """Derive team groups from runtime SOT (data/config/sources.yaml).

    P1 Hallucination Prevention: Programmatic derivation ensures the team
    distribution always reflects the runtime SOT.

    Returns:
        Groups in _FALLBACK_GROUPS format, or None if SOT unavailable.
    """
    sot_path = project_dir / "data" / "config" / "sources.yaml"
    if not sot_path.is_file():
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        with open(sot_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        sources = data.get("sources", {})
        if not isinstance(sources, dict) or not sources:
            return None
        groups: dict[str, list[dict[str, str]]] = {
            "kr-major": [], "kr-tech": [], "english": [], "multilingual": [],
        }
        for _site_id, cfg in sorted(sources.items()):
            if not isinstance(cfg, dict):
                continue
            group_letter = cfg.get("group", "")
            team = _GROUP_TO_TEAM.get(group_letter)
            if not team:
                continue
            url = cfg.get("url", "")
            domain = url
            if "://" in domain:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower().removeprefix("www.")
            entry: dict[str, str] = {
                "domain": domain,
                "name": cfg.get("name", _site_id),
            }
            # Include language for multilingual team
            if team == "multilingual":
                entry["language"] = cfg.get("language", "en")
            groups[team].append(entry)
        # Validate: all teams must have at least 1 site
        if all(groups.values()):
            return groups
        return None
    except Exception:
        return None


def get_site_groups(project_dir: Path) -> dict[str, list[dict[str, str]]]:
    """Get canonical site groups — SOT-derived with hardcoded fallback.

    P1: In normal operation, derives from data/config/sources.yaml (runtime SOT).
    Falls back to _FALLBACK_GROUPS only when SOT is unavailable.
    """
    sot_groups = _derive_groups_from_sot(project_dir)
    if sot_groups is not None:
        return sot_groups
    return {k: list(v) for k, v in _FALLBACK_GROUPS.items()}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_SITE_LINE_RE = re.compile(
    r"[-*]\s+\*?\*?([^*\n:]+?)\*?\*?\s*"           # site name
    r"(?:\(([^)]+)\))?"                               # optional (domain)
    r"(?:\s*[-–:]\s*(.+))?$",                         # optional strategy note
    re.MULTILINE,
)

_TABLE_ROW_RE = re.compile(
    r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"            # | col1 | col2 |
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)", re.MULTILINE)


def _parse_sites_from_strategies(
    text: str,
    fallback_groups: dict[str, list[dict[str, str]]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Attempt to parse site groupings from the strategies markdown.

    Returns a dict mapping group-key -> list of site dicts.
    Falls back to fallback_groups (SOT-derived or hardcoded) if parsing yields too few sites.
    """
    groups: dict[str, list[dict[str, Any]]] = {
        "kr-major": [],
        "kr-tech": [],
        "english": [],
        "multilingual": [],
    }

    # Heuristic: find sections by heading keywords and collect sites
    group_keywords: dict[str, list[str]] = {
        "kr-major": ["korean major", "kr major", "korean mainstream", "주요 언론",
                      "major korean", "korean news"],
        "kr-tech": ["korean tech", "kr tech", "tech korean", "기술 매체",
                     "tech media", "it media"],
        "english": ["english", "global", "international", "영문",
                     "english-language"],
        "multilingual": ["multilingual", "multi-language", "다국어",
                         "other language", "non-english"],
    }

    headings = list(_HEADING_RE.finditer(text))

    for group_key, keywords in group_keywords.items():
        for idx, heading_match in enumerate(headings):
            title = heading_match.group(2).strip().lower()
            if not any(kw in title for kw in keywords):
                continue

            # Get section text
            start = heading_match.end()
            end = headings[idx + 1].start() if idx + 1 < len(headings) else len(text)
            section_text = text[start:end]

            # Try to parse sites from bullet lists
            for site_match in _SITE_LINE_RE.finditer(section_text):
                name = site_match.group(1).strip()
                domain = site_match.group(2) or ""
                strategy_note = site_match.group(3) or ""
                if name and len(name) < 80:
                    entry: dict[str, Any] = {"name": name}
                    if domain:
                        entry["domain"] = domain.strip()
                    if strategy_note:
                        entry["strategy"] = strategy_note.strip()
                    groups[group_key].append(entry)

            # Try to parse sites from tables
            for row_match in _TABLE_ROW_RE.finditer(section_text):
                col1 = row_match.group(1).strip()
                col2 = row_match.group(2).strip()
                # Skip table header separators
                if col1.startswith("-") or col1.startswith(":"):
                    continue
                if col1.lower() in ("site", "name", "domain", "source"):
                    continue
                if col1 and len(col1) < 80:
                    entry = {"name": col1}
                    if "." in col2:
                        entry["domain"] = col2
                    else:
                        entry["strategy"] = col2
                    groups[group_key].append(entry)

    # Check if we found enough sites
    total_parsed = sum(len(v) for v in groups.values())
    if total_parsed < 20:
        # Fall back to SOT-derived groups (or hardcoded fallback)
        enriched = _enrich_defaults_with_strategies(text, fallback_groups)
        return enriched

    return groups


def _enrich_defaults_with_strategies(
    text: str,
    base_groups: dict[str, list[dict[str, str]]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Use given groups (or fallback) and try to extract per-site strategy notes."""
    result: dict[str, list[dict[str, Any]]] = {}
    text_lower = text.lower()
    groups_to_use = base_groups if base_groups is not None else _FALLBACK_GROUPS

    for group_key, sites in groups_to_use.items():
        enriched_sites: list[dict[str, Any]] = []
        for site in sites:
            entry: dict[str, Any] = dict(site)

            # Try to find strategy note near domain mention
            domain = site.get("domain", "")
            name = site.get("name", "")

            strategy_note = _find_strategy_for_site(text, domain, name)
            if strategy_note:
                entry["strategy"] = strategy_note

            enriched_sites.append(entry)
        result[group_key] = enriched_sites

    return result


def _find_strategy_for_site(text: str, domain: str, name: str) -> str:
    """Find a strategy note for a specific site in the text."""
    # Search for lines mentioning the domain or name
    search_terms = [domain, name.lower()] if domain else [name.lower()]
    text_lower = text.lower()

    for term in search_terms:
        if not term:
            continue
        pos = text_lower.find(term.lower())
        if pos == -1:
            continue

        # Extract the surrounding line(s)
        line_start = text.rfind("\n", 0, pos) + 1
        line_end = text.find("\n", pos)
        if line_end == -1:
            line_end = len(text)

        line = text[line_start:line_end].strip()

        # Try to extract strategy part after a separator
        for sep in [":", "–", "—", "->"]:
            sep_pos = line.find(sep, line.lower().find(term.lower()) + len(term))
            if sep_pos != -1:
                note = line[sep_pos + len(sep):].strip()
                if note and len(note) > 5:
                    return note[:200]

    return ""


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def distribute_sites(project_dir: Path) -> dict:
    """Parse strategies and distribute sites to team group files.

    Returns a dict with 'valid', output paths, and diagnostics.
    """
    strategies_path = project_dir / "planning" / "crawling-strategies.md"
    output_dir = project_dir / "planning" / "team-input"

    warnings: list[str] = []

    # ------------------------------------------------------------------
    # Read strategies document
    # ------------------------------------------------------------------
    strategies_text = ""
    if strategies_path.is_file():
        strategies_text = strategies_path.read_text(encoding="utf-8")
    else:
        warnings.append(f"Strategies file not found: {strategies_path}; using defaults")

    # ------------------------------------------------------------------
    # P1: Derive site groups from runtime SOT (prevents desync)
    # ------------------------------------------------------------------
    sot_groups = get_site_groups(project_dir)

    # ------------------------------------------------------------------
    # Parse or use SOT-derived groups
    # ------------------------------------------------------------------
    if strategies_text:
        groups = _parse_sites_from_strategies(strategies_text, sot_groups)
    else:
        groups = _enrich_defaults_with_strategies("", sot_groups)

    # ------------------------------------------------------------------
    # Map group keys to output filenames
    # ------------------------------------------------------------------
    group_files = {
        "kr-major": "adapters-kr-major.json",
        "kr-tech": "adapters-kr-tech.json",
        "english": "adapters-english.json",
        "multilingual": "adapters-multilingual.json",
    }

    # ------------------------------------------------------------------
    # Write output files
    # ------------------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths: dict[str, str] = {}
    group_counts: dict[str, int] = {}
    total_sites = 0

    for group_key, filename in group_files.items():
        sites = groups.get(group_key, [])
        out_path = output_dir / filename

        payload = {
            "group": group_key,
            "total_sites": len(sites),
            "sites": sites,
        }

        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        output_paths[group_key] = str(out_path)
        group_counts[group_key] = len(sites)
        total_sites += len(sites)

    result = {
        "valid": True,
        "total_sites": total_sites,
        "group_counts": group_counts,
        "output_paths": output_paths,
        "warnings": warnings,
    }

    # Warn if total does not match expected 121
    if total_sites != 121:
        result["warnings"].append(
            f"Expected 121 total sites but distributed {total_sites}."
        )

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Distribute 121 sites to 4 adapter-dev team members."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Project root directory.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    result = distribute_sites(project_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if not result["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
