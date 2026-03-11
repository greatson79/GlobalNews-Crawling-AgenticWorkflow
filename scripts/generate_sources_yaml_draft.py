#!/usr/bin/env python3
"""Generate sources.yaml draft from site reconnaissance.

Usage: python3 scripts/generate_sources_yaml_draft.py --project-dir .

Reads:
  - research/site-reconnaissance.md  (Step 1 output)

Output:
  - config/sources.yaml (draft)

Parses the site reconnaissance output and generates a YAML config per
site with: domain, name, language, crawl_method, rss_url, sitemap_url,
rate_limit, ua_rotation, anti_block_tier.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# PyYAML import (graceful fallback)
# ---------------------------------------------------------------------------

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# ---------------------------------------------------------------------------
# Constants — fallback site catalog (used when runtime SOT unavailable)
# ---------------------------------------------------------------------------

# Fallback catalog — used only when data/config/sources.yaml is missing.
# P1: Normal operation derives sites from runtime SOT programmatically
# via _derive_sites_from_sot(), preventing hardcoded list desync.
_FALLBACK_SITES: list[dict[str, Any]] = [
    # Group A: Korean Major Dailies (5)
    {"domain": "chosun.com", "name": "Chosun Ilbo", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "joongang.co.kr", "name": "JoongAng Ilbo", "language": "ko", "crawl_method": "dom+sitemap", "anti_block_tier": 3},
    {"domain": "donga.com", "name": "Dong-A Ilbo", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "hani.co.kr", "name": "Hankyoreh", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "yna.co.kr", "name": "Yonhap News Agency", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    # Group B: Korean Economy (4)
    {"domain": "mk.co.kr", "name": "Maeil Business Newspaper", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "hankyung.com", "name": "Korea Economic Daily", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "fnnews.com", "name": "Financial News", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "mt.co.kr", "name": "Money Today", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    # Group C: Korean Niche (3)
    {"domain": "nocutnews.co.kr", "name": "NoCut News", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "kmib.co.kr", "name": "Kookmin Ilbo", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "ohmynews.com", "name": "OhmyNews", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    # Group D: Korean Tech & Niche English (10)
    {"domain": "38north.org", "name": "38 North", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "bloter.net", "name": "Bloter", "language": "ko", "crawl_method": "playwright+rss", "anti_block_tier": 3},
    {"domain": "etnews.com", "name": "Electronic Times", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "sciencetimes.co.kr", "name": "Science Times", "language": "ko", "crawl_method": "sitemap+rss", "anti_block_tier": 3},
    {"domain": "zdnet.co.kr", "name": "ZDNet Korea", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "irobotnews.com", "name": "iRobot News", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "techneedle.com", "name": "TechNeedle", "language": "ko", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "insight.co.kr", "name": "Insight Korea", "language": "ko", "crawl_method": "rss+dom", "anti_block_tier": 2},
    {"domain": "stratechery.com", "name": "Stratechery", "language": "en", "crawl_method": "rss+dom", "anti_block_tier": 1},
    {"domain": "techmeme.com", "name": "Techmeme", "language": "en", "crawl_method": "rss+dom", "anti_block_tier": 1},
    # Group E: English Major & Western (22)
    {"domain": "marketwatch.com", "name": "MarketWatch", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "voakorea.com", "name": "VOA Korea", "language": "ko", "crawl_method": "api+sitemap", "anti_block_tier": 1},
    {"domain": "huffpost.com", "name": "HuffPost", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 2},
    {"domain": "nytimes.com", "name": "The New York Times", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 3},
    {"domain": "ft.com", "name": "Financial Times", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 3},
    {"domain": "wsj.com", "name": "Wall Street Journal", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 3},
    {"domain": "latimes.com", "name": "Los Angeles Times", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "buzzfeed.com", "name": "BuzzFeed", "language": "en", "crawl_method": "playwright+sitemap", "anti_block_tier": 3},
    {"domain": "nationalpost.com", "name": "National Post", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "edition.cnn.com", "name": "CNN", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 2},
    {"domain": "bloomberg.com", "name": "Bloomberg", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 3},
    {"domain": "afmedios.com", "name": "AF Medios", "language": "es", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "wired.com", "name": "Wired", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "investing.com", "name": "Investing.com", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "qz.com", "name": "Quartz", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "bbc.com", "name": "BBC News", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "theguardian.com", "name": "The Guardian", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "thetimes.com", "name": "The Times", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 3},
    {"domain": "telegraph.co.uk", "name": "The Telegraph", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 3},
    {"domain": "politico.eu", "name": "Politico Europe", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "euractiv.com", "name": "Euractiv", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "natureasia.com", "name": "Nature Asia", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    # Group F: Asia-Pacific (23)
    {"domain": "people.com.cn", "name": "People's Daily", "language": "zh", "crawl_method": "sitemap+dom", "anti_block_tier": 2},
    {"domain": "globaltimes.cn", "name": "Global Times", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 1},
    {"domain": "scmp.com", "name": "South China Morning Post", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "taiwannews.com.tw", "name": "Taiwan News", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 1},
    {"domain": "yomiuri.co.jp", "name": "Yomiuri Shimbun", "language": "ja", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "thehindu.com", "name": "The Hindu", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "mainichi.jp", "name": "Mainichi Shimbun", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "asahi.com", "name": "Asahi Shimbun", "language": "ja", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "news.yahoo.co.jp", "name": "Yahoo Japan News", "language": "ja", "crawl_method": "rss+dom", "anti_block_tier": 3},
    {"domain": "timesofindia.indiatimes.com", "name": "Times of India", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "hindustantimes.com", "name": "Hindustan Times", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "economictimes.indiatimes.com", "name": "Economic Times India", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "indianexpress.com", "name": "Indian Express", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "philstar.com", "name": "PhilStar", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "mb.com.ph", "name": "Manila Bulletin", "language": "en", "crawl_method": "rss+dom", "anti_block_tier": 3},
    {"domain": "inquirer.net", "name": "Philippine Daily Inquirer", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "thejakartapost.com", "name": "The Jakarta Post", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "en.antaranews.com", "name": "Antara News", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "en.tempo.co", "name": "Tempo Indonesia", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "focustaiwan.tw", "name": "Focus Taiwan", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "taipeitimes.com", "name": "Taipei Times", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "e.vnexpress.net", "name": "VnExpress International", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "vietnamnews.vn", "name": "Vietnam News", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    # Group G: Europe, Middle East & Multilingual (38)
    {"domain": "thesun.co.uk", "name": "The Sun", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "bild.de", "name": "Bild", "language": "de", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "lemonde.fr", "name": "Le Monde", "language": "fr", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "themoscowtimes.com", "name": "The Moscow Times", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "arabnews.com", "name": "Arab News", "language": "en", "crawl_method": "sitemap+dom", "anti_block_tier": 2},
    {"domain": "aljazeera.com", "name": "Al Jazeera English", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "israelhayom.com", "name": "Israel Hayom", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "euronews.com", "name": "Euronews", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "spiegel.de", "name": "Der Spiegel", "language": "de", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "sueddeutsche.de", "name": "Sueddeutsche Zeitung", "language": "de", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "welt.de", "name": "Die Welt", "language": "de", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "faz.net", "name": "Frankfurter Allgemeine", "language": "de", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "corriere.it", "name": "Corriere della Sera", "language": "it", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "repubblica.it", "name": "La Repubblica", "language": "it", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "ansa.it", "name": "ANSA", "language": "it", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "elpais.com", "name": "El Pais", "language": "es", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "elmundo.es", "name": "El Mundo", "language": "es", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "abc.es", "name": "ABC Spain", "language": "es", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "lavanguardia.com", "name": "La Vanguardia", "language": "es", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "lefigaro.fr", "name": "Le Figaro", "language": "fr", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "liberation.fr", "name": "Liberation", "language": "fr", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "france24.com", "name": "France 24", "language": "fr", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "ouest-france.fr", "name": "Ouest-France", "language": "fr", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "wyborcza.pl", "name": "Gazeta Wyborcza", "language": "pl", "crawl_method": "rss+dom", "anti_block_tier": 2},
    {"domain": "pap.pl", "name": "Polish Press Agency", "language": "pl", "crawl_method": "rss+dom", "anti_block_tier": 1},
    {"domain": "idnes.cz", "name": "iDNES", "language": "cs", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "intellinews.com", "name": "Intellinews", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "balkaninsight.com", "name": "Balkan Insight (BIRN)", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "centraleuropeantimes.com", "name": "Central European Times", "language": "en", "crawl_method": "rss+dom", "anti_block_tier": 1},
    {"domain": "aftonbladet.se", "name": "Aftonbladet", "language": "sv", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "tv2.no", "name": "TV2 Norway", "language": "no", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "yle.fi", "name": "YLE News", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "icelandmonitor.mbl.is", "name": "Iceland Monitor", "language": "en", "crawl_method": "rss+dom", "anti_block_tier": 1},
    {"domain": "middleeasteye.net", "name": "Middle East Eye", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "al-monitor.com", "name": "Al-Monitor", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "haaretz.com", "name": "Haaretz", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 3},
    {"domain": "jpost.com", "name": "Jerusalem Post", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "jordantimes.com", "name": "Jordan Times", "language": "en", "crawl_method": "rss+dom", "anti_block_tier": 1},
    # Group H: Africa (4)
    {"domain": "allafrica.com", "name": "AllAfrica", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "africanews.com", "name": "Africanews", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "theafricareport.com", "name": "The Africa Report", "language": "en", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "panapress.com", "name": "Panapress", "language": "en", "crawl_method": "rss+dom", "anti_block_tier": 1},
    # Group I: Latin America (8)
    {"domain": "clarin.com", "name": "Clarin", "language": "es", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "lanacion.com.ar", "name": "La Nacion Argentina", "language": "es", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "folha.uol.com.br", "name": "Folha de S.Paulo", "language": "pt", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "oglobo.globo.com", "name": "O Globo", "language": "pt", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "digital.elmercurio.com", "name": "El Mercurio", "language": "es", "crawl_method": "dom+sitemap", "anti_block_tier": 3},
    {"domain": "biobiochile.cl", "name": "BioBioChile", "language": "es", "crawl_method": "rss+sitemap", "anti_block_tier": 1},
    {"domain": "eltiempo.com", "name": "El Tiempo", "language": "es", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "elcomercio.pe", "name": "El Comercio Peru", "language": "es", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    # Group J: Russia, Central Asia & Others (4)
    {"domain": "mongolia.gogo.mn", "name": "GoGo Mongolia", "language": "mn", "crawl_method": "rss+dom", "anti_block_tier": 1},
    {"domain": "ria.ru", "name": "RIA Novosti", "language": "ru", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "rg.ru", "name": "Rossiyskaya Gazeta", "language": "ru", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
    {"domain": "rbc.ru", "name": "RBC", "language": "ru", "crawl_method": "rss+sitemap", "anti_block_tier": 2},
]

# Backward compatibility — tests reference _DEFAULT_SITES
_DEFAULT_SITES = _FALLBACK_SITES


# ---------------------------------------------------------------------------
# P1: SOT-derived site catalog (prevents hardcoded list desync)
# ---------------------------------------------------------------------------

def _derive_sites_from_sot(project_dir: Path) -> list[dict[str, Any]] | None:
    """Derive site catalog from runtime SOT (data/config/sources.yaml).

    P1 Hallucination Prevention: Programmatic derivation ensures the draft
    config/sources.yaml always reflects the runtime SOT, eliminating manual
    sync errors that caused the original Camp A/Camp B desync.

    Returns:
        Sites in _FALLBACK_SITES format, or None if SOT unavailable.
    """
    sot_path = project_dir / "data" / "config" / "sources.yaml"
    if not sot_path.is_file():
        return None
    if not _HAS_YAML:
        return None
    try:
        with open(sot_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        sources = data.get("sources", {})
        if not isinstance(sources, dict) or not sources:
            return None
        sites: list[dict[str, Any]] = []
        for _site_id, cfg in sorted(sources.items()):
            if not isinstance(cfg, dict):
                continue
            url = cfg.get("url", "")
            domain = url
            if "://" in domain:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower().removeprefix("www.")
            crawl = cfg.get("crawl", {})
            primary = crawl.get("primary_method", "rss")
            fallbacks = crawl.get("fallback_methods", [])
            if fallbacks and isinstance(fallbacks, list):
                crawl_method = f"{primary}+{fallbacks[0]}"
            else:
                crawl_method = primary
            sites.append({
                "domain": domain,
                "name": cfg.get("name", _site_id),
                "language": cfg.get("language", "en"),
                "crawl_method": crawl_method,
                "anti_block_tier": cfg.get("anti_block", {}).get("ua_tier", 1),
            })
        return sites if sites else None
    except Exception:
        return None


def get_site_catalog(project_dir: Path) -> list[dict[str, Any]]:
    """Get canonical site catalog — SOT-derived with hardcoded fallback.

    P1: In normal operation, derives from data/config/sources.yaml (runtime SOT).
    Falls back to _FALLBACK_SITES only when SOT is unavailable.
    """
    sot_sites = _derive_sites_from_sot(project_dir)
    if sot_sites is not None:
        return sot_sites
    return list(_FALLBACK_SITES)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)", re.MULTILINE)
_URL_RE = re.compile(r"https?://[^\s)\"'>]+")
_DOMAIN_RE = re.compile(r"(?:https?://)?(?:www\.)?([a-z0-9][-a-z0-9]*\.[a-z.]+)", re.IGNORECASE)


def _parse_reconnaissance(text: str, site_catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attempt to parse site data from reconnaissance markdown.

    Tries to extract per-site blocks and enrich the given site catalog.
    """
    if not text.strip():
        return site_catalog

    # Build a lookup from the site catalog
    defaults_by_domain = {s["domain"]: dict(s) for s in site_catalog}
    enriched: dict[str, dict[str, Any]] = {}

    # Strategy: find domain mentions and extract nearby metadata
    for domain, site_defaults in defaults_by_domain.items():
        entry = dict(site_defaults)

        # Search for domain in text
        domain_pattern = re.escape(domain)
        matches = list(re.finditer(domain_pattern, text, re.IGNORECASE))
        if not matches:
            enriched[domain] = entry
            continue

        # Use the first mention's surrounding context (500 chars each way)
        pos = matches[0].start()
        context_start = max(0, pos - 500)
        context_end = min(len(text), pos + 500)
        context = text[context_start:context_end]
        context_lower = context.lower()

        # Extract RSS URL
        rss_match = re.search(r"rss[:\s]*\*?\*?\s*(https?://[^\s)\"'>]+)", context, re.IGNORECASE)
        if rss_match:
            entry["rss_url"] = rss_match.group(1).strip()

        # Extract sitemap URL
        sitemap_match = re.search(r"sitemap[:\s]*\*?\*?\s*(https?://[^\s)\"'>]+)", context, re.IGNORECASE)
        if sitemap_match:
            entry["sitemap_url"] = sitemap_match.group(1).strip()

        # Extract rate limit
        rate_match = re.search(r"rate[_\s-]*limit[:\s]*(\d+(?:\.\d+)?)\s*(?:req(?:uest)?s?)?/?\s*(?:s|sec|second|min|minute)?", context, re.IGNORECASE)
        if rate_match:
            entry["rate_limit"] = f"{rate_match.group(1)}/s"

        # Detect crawl method overrides
        if "api" in context_lower and ("endpoint" in context_lower or "json" in context_lower):
            if "rss" in context_lower:
                entry["crawl_method"] = "rss+api"
            else:
                entry["crawl_method"] = "api"
        elif "headless" in context_lower or "javascript" in context_lower or "spa" in context_lower:
            entry["crawl_method"] = "headless"
        elif "sitemap" in context_lower and "rss" not in context_lower:
            entry["crawl_method"] = "sitemap+html"

        # Detect UA rotation need
        if any(kw in context_lower for kw in ["user-agent", "ua rotation", "bot detection", "cloudflare"]):
            entry["ua_rotation"] = True
        else:
            entry["ua_rotation"] = False

        # Detect anti-block tier from context clues
        if any(kw in context_lower for kw in ["cloudflare", "captcha", "paywall", "403", "rate limit aggressive"]):
            entry["anti_block_tier"] = max(entry.get("anti_block_tier", 1), 3)
        elif any(kw in context_lower for kw in ["moderate protection", "cookie required", "session"]):
            entry["anti_block_tier"] = max(entry.get("anti_block_tier", 1), 2)

        enriched[domain] = entry

    # Add any defaults not found
    for domain, site_defaults in defaults_by_domain.items():
        if domain not in enriched:
            enriched[domain] = site_defaults

    return list(enriched.values())


def _build_yaml_string(sites: list[dict[str, Any]]) -> str:
    """Build a YAML string from sites list.

    Uses PyYAML if available; otherwise constructs YAML manually for
    deterministic output without external dependencies.
    """
    if _HAS_YAML:
        doc = {
            "_meta": {
                "version": "1.0.0-draft",
                "generated_by": "generate_sources_yaml_draft.py",
                "description": "News sources configuration — auto-generated draft from site reconnaissance",
                "total_sites": len(sites),
            },
            "sources": sites,
        }
        return yaml.dump(doc, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Manual YAML construction
    lines: list[str] = []
    lines.append("# News Sources Configuration (Draft)")
    lines.append("# Auto-generated by generate_sources_yaml_draft.py")
    lines.append(f"# Total sites: {len(sites)}")
    lines.append("")
    lines.append("_meta:")
    lines.append("  version: 1.0.0-draft")
    lines.append("  generated_by: generate_sources_yaml_draft.py")
    lines.append("  description: News sources configuration — auto-generated draft from site reconnaissance")
    lines.append(f"  total_sites: {len(sites)}")
    lines.append("")
    lines.append("sources:")

    for site in sites:
        lines.append(f"  - domain: {site['domain']}")
        lines.append(f"    name: \"{site['name']}\"")
        lines.append(f"    language: {site.get('language', 'en')}")
        lines.append(f"    crawl_method: {site.get('crawl_method', 'rss+html')}")

        if "rss_url" in site:
            lines.append(f"    rss_url: {site['rss_url']}")
        if "sitemap_url" in site:
            lines.append(f"    sitemap_url: {site['sitemap_url']}")

        rate_limit = site.get("rate_limit", "1/s")
        lines.append(f"    rate_limit: \"{rate_limit}\"")

        ua_rotation = site.get("ua_rotation", False)
        lines.append(f"    ua_rotation: {'true' if ua_rotation else 'false'}")

        anti_block_tier = site.get("anti_block_tier", 1)
        lines.append(f"    anti_block_tier: {anti_block_tier}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def generate_sources_yaml(project_dir: Path) -> dict:
    """Generate sources.yaml draft from reconnaissance data.

    Returns a dict with 'valid', 'output_path', and diagnostics.
    """
    recon_path = project_dir / "research" / "site-reconnaissance.md"
    output_dir = project_dir / "config"
    output_path = output_dir / "sources.yaml"

    warnings: list[str] = []

    # ------------------------------------------------------------------
    # Read reconnaissance
    # ------------------------------------------------------------------
    recon_text = ""
    if recon_path.is_file():
        recon_text = recon_path.read_text(encoding="utf-8")
    else:
        warnings.append(f"Reconnaissance not found: {recon_path}; using default catalog")

    # ------------------------------------------------------------------
    # P1: Derive site catalog from runtime SOT (prevents desync)
    # ------------------------------------------------------------------
    site_catalog = get_site_catalog(project_dir)

    # ------------------------------------------------------------------
    # Parse and enrich sites
    # ------------------------------------------------------------------
    sites = _parse_reconnaissance(recon_text, site_catalog)

    # ------------------------------------------------------------------
    # Generate YAML
    # ------------------------------------------------------------------
    yaml_content = _build_yaml_string(sites)

    # ------------------------------------------------------------------
    # Write output
    # ------------------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml_content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Compute stats
    # ------------------------------------------------------------------
    languages = {}
    methods = {}
    tiers = {1: 0, 2: 0, 3: 0}

    for site in sites:
        lang = site.get("language", "unknown")
        languages[lang] = languages.get(lang, 0) + 1

        method = site.get("crawl_method", "unknown")
        methods[method] = methods.get(method, 0) + 1

        tier = site.get("anti_block_tier", 1)
        if tier in tiers:
            tiers[tier] += 1

    result = {
        "valid": True,
        "output_path": str(output_path),
        "total_sites": len(sites),
        "languages": languages,
        "crawl_methods": methods,
        "anti_block_tiers": tiers,
        "output_size_bytes": len(yaml_content.encode("utf-8")),
        "has_yaml_lib": _HAS_YAML,
        "warnings": warnings,
    }

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate sources.yaml draft from site reconnaissance."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Project root directory.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    result = generate_sources_yaml(project_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if not result["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
