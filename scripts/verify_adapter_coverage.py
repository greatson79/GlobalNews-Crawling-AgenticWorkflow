#!/usr/bin/env python3
"""Verify adapter coverage against sources.yaml.

Usage: python3 scripts/verify_adapter_coverage.py --project-dir .

Reads:
  - config/sources.yaml
  - src/crawling/adapters/  (adapter files)

Output:
  - JSON to stdout

Reads sources.yaml for 44 site domains, scans src/crawling/adapters/
for adapter files, checks adapter registry (__init__.py) for domain
mappings, and reports covered/missing/extra domains.
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
# Helpers
# ---------------------------------------------------------------------------

_DOMAIN_RE = re.compile(r"""['"]([a-z0-9][-a-z0-9]*\.[a-z.]+)['"]""", re.IGNORECASE)
_CLASS_RE = re.compile(r"class\s+(\w+Adapter)\b", re.IGNORECASE)
_REGISTRY_RE = re.compile(
    r"""['"]([a-z0-9][-a-z0-9]*\.[a-z.]+)['"]"""
    r"""\s*:\s*(\w+)""",
    re.IGNORECASE,
)


def _load_sources_yaml(path: Path) -> dict[str, str]:
    """Load source site_ids and domains from sources.yaml.

    Returns a dict of site_id -> domain string.
    Supports two formats:
      - dict-of-dicts: {sources: {site_id: {url: ...}}}
      - list-of-dicts: {sources: [{domain: ..., ...}]}
    """
    if not path.is_file():
        return {}

    text = path.read_text(encoding="utf-8")

    if _HAS_YAML:
        try:
            doc = yaml.safe_load(text)
            if isinstance(doc, dict) and "sources" in doc:
                sources = doc["sources"]
                # Dict-of-dicts format: {site_id: {url: "https://..."}}
                if isinstance(sources, dict):
                    result = {}
                    for site_id, cfg in sources.items():
                        if isinstance(cfg, dict):
                            url = cfg.get("url", "")
                            if url:
                                from urllib.parse import urlparse
                                domain = urlparse(url).netloc.lower()
                                domain = domain.removeprefix("www.")
                                result[site_id] = domain
                    return result
                # List-of-dicts format: [{domain: ...}]
                if isinstance(sources, list):
                    result = {}
                    for entry in sources:
                        if isinstance(entry, dict) and "domain" in entry:
                            d = entry["domain"].strip().lower()
                            sid = entry.get("id", d.split(".")[0])
                            result[sid] = d
                    return result
        except yaml.YAMLError:
            pass

    # Fallback: regex extraction
    result: dict[str, str] = {}
    for match in re.finditer(r"url:\s*(\S+)", text):
        url = match.group(1).strip().strip("'\"")
        if "://" in url:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower().removeprefix("www.")
            sid = domain.split(".")[0]
            result[sid] = domain

    return result


def _scan_adapter_files(adapters_dir: Path) -> dict[str, dict[str, Any]]:
    """Scan adapter directory (including subdirs) for .py files and extract domain/site_id mappings.

    Returns a dict of relative_path -> {classes, domains, site_ids}.
    """
    adapters: dict[str, dict[str, Any]] = {}

    if not adapters_dir.is_dir():
        return adapters

    # Scan all .py files in adapters/ and subdirectories
    for py_file in sorted(adapters_dir.rglob("*.py")):
        if py_file.name.startswith("__") or py_file.name.startswith("_"):
            continue

        text = py_file.read_text(encoding="utf-8")

        # Extract adapter classes
        classes = _CLASS_RE.findall(text)

        # Extract domain references
        domains = []
        for m in _DOMAIN_RE.finditer(text):
            d = m.group(1).lower()
            if "." in d and len(d) > 3:
                domains.append(d)

        # Extract SITE_ID from class attributes
        site_ids = []
        for m in re.finditer(r'SITE_ID\s*[:=]\s*["\'](\w+)["\']', text):
            site_ids.append(m.group(1).lower())

        rel_path = str(py_file.relative_to(adapters_dir))

        adapters[rel_path] = {
            "classes": classes,
            "domains": list(set(domains)),
            "site_ids": site_ids,
            "stem": py_file.stem,
        }

    return adapters


def _parse_registry(init_path: Path) -> dict[str, str]:
    """Parse __init__.py for domain -> adapter class mappings."""
    registry: dict[str, str] = {}

    if not init_path.is_file():
        return registry

    text = init_path.read_text(encoding="utf-8")

    # Look for registry dict patterns
    for m in _REGISTRY_RE.finditer(text):
        domain = m.group(1).lower()
        adapter_class = m.group(2)
        registry[domain] = adapter_class

    return registry


# ---------------------------------------------------------------------------
# SS4: Config sync check (config/ ↔ data/config/)
# ---------------------------------------------------------------------------

def _check_config_sync(project_dir: Path) -> dict[str, Any]:
    """SS4: Verify config/sources.yaml domains match data/config/sources.yaml.

    P1: Detects desync between the Planning Phase draft (config/) and the
    Implementation Phase runtime SOT (data/config/). The draft is generated
    by generate_sources_yaml_draft.py and should derive from the SOT.
    """
    draft_path = project_dir / "config" / "sources.yaml"
    sot_path = project_dir / "data" / "config" / "sources.yaml"

    result: dict[str, Any] = {"check": "SS4_config_sync", "valid": True, "warnings": []}

    if not draft_path.is_file():
        result["warnings"].append(
            "SS4: config/sources.yaml not found "
            "(regenerate: python3 scripts/generate_sources_yaml_draft.py --project-dir .)"
        )
        result["valid"] = False
        return result

    if not sot_path.is_file():
        result["warnings"].append("SS4: data/config/sources.yaml (runtime SOT) not found")
        result["valid"] = False
        return result

    draft_id_to_domain = _load_sources_yaml(draft_path)
    sot_id_to_domain = _load_sources_yaml(sot_path)

    draft_domains = set(draft_id_to_domain.values()) if draft_id_to_domain else set()
    sot_domains = set(sot_id_to_domain.values()) if sot_id_to_domain else set()

    if not draft_domains:
        result["warnings"].append("SS4: No domains extracted from config/sources.yaml")
        result["valid"] = False
        return result

    if not sot_domains:
        result["warnings"].append("SS4: No domains extracted from data/config/sources.yaml")
        result["valid"] = False
        return result

    in_draft_only = draft_domains - sot_domains
    in_sot_only = sot_domains - draft_domains

    if in_draft_only or in_sot_only:
        result["valid"] = False
        if in_draft_only:
            result["warnings"].append(
                f"SS4: {len(in_draft_only)} domains in config/ but not in data/config/: "
                f"{sorted(in_draft_only)}"
            )
        if in_sot_only:
            result["warnings"].append(
                f"SS4: {len(in_sot_only)} domains in data/config/ but not in config/: "
                f"{sorted(in_sot_only)}"
            )

    result["draft_count"] = len(draft_domains)
    result["sot_count"] = len(sot_domains)

    return result


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def verify_coverage(project_dir: Path) -> dict:
    """Cross-check adapter files against sources.yaml.

    Returns a dict with coverage analysis.
    """
    # Try data/config/sources.yaml first, fallback to config/sources.yaml
    sources_path = project_dir / "data" / "config" / "sources.yaml"
    if not sources_path.is_file():
        sources_path = project_dir / "config" / "sources.yaml"
    adapters_dir = project_dir / "src" / "crawling" / "adapters"
    init_path = adapters_dir / "__init__.py"

    warnings: list[str] = []
    errors: list[str] = []

    # ------------------------------------------------------------------
    # Load expected site_ids and domains from sources.yaml
    # ------------------------------------------------------------------
    site_id_to_domain = _load_sources_yaml(sources_path)
    if not site_id_to_domain:
        errors.append(f"No sites found in {sources_path}")

    expected_site_ids = set(site_id_to_domain.keys())
    expected_domains = set(site_id_to_domain.values())

    # ------------------------------------------------------------------
    # Scan adapter files (including subdirectories)
    # ------------------------------------------------------------------
    adapter_files = _scan_adapter_files(adapters_dir)
    if not adapter_files and adapters_dir.is_dir():
        warnings.append("No adapter .py files found")
    elif not adapters_dir.is_dir():
        warnings.append(f"Adapters directory not found: {adapters_dir}")

    # Collect all site_ids and domains covered by adapter files
    covered_site_ids: set[str] = set()
    covered_domains: set[str] = set()
    for info in adapter_files.values():
        covered_site_ids.update(info.get("site_ids", []))
        covered_domains.update(info["domains"])

    # ------------------------------------------------------------------
    # Parse registry from __init__.py files (top-level + subdirectories)
    # ------------------------------------------------------------------
    registry = _parse_registry(init_path)
    # Also parse subdirectory registries
    for subdir in adapters_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith("_"):
            sub_init = subdir / "__init__.py"
            if sub_init.is_file():
                sub_reg = _parse_registry(sub_init)
                registry.update(sub_reg)

    registered_domains = set(registry.keys())

    # ------------------------------------------------------------------
    # Compute coverage (by site_id — primary matching)
    # ------------------------------------------------------------------
    covered_ids = expected_site_ids & covered_site_ids
    missing_ids = expected_site_ids - covered_site_ids

    # Also check by domain (secondary matching for sites matched by domain in file)
    for sid in list(missing_ids):
        domain = site_id_to_domain.get(sid, "")
        if domain in covered_domains or domain in registered_domains:
            covered_ids.add(sid)
            missing_ids.discard(sid)

    # Also match by filename stem
    adapter_stems = {info["stem"] for info in adapter_files.values()}
    for sid in list(missing_ids):
        # Check various name patterns
        if sid in adapter_stems or sid.replace("_", "") in adapter_stems:
            covered_ids.add(sid)
            missing_ids.discard(sid)

    total_expected = len(expected_site_ids)
    total_covered = len(covered_ids)
    coverage_pct = (total_covered / total_expected * 100) if total_expected > 0 else 0.0

    # ------------------------------------------------------------------
    # SS4: Check config/sources.yaml ↔ data/config/sources.yaml sync
    # ------------------------------------------------------------------
    ss4_result = _check_config_sync(project_dir)
    if ss4_result["warnings"]:
        warnings.extend(ss4_result["warnings"])

    result = {
        "valid": len(errors) == 0 and len(missing_ids) == 0,
        "summary": {
            "expected_sites": total_expected,
            "covered_sites": total_covered,
            "missing_sites": len(missing_ids),
            "coverage_percent": round(coverage_pct, 1),
        },
        "covered": sorted(covered_ids),
        "missing": sorted(missing_ids),
        "adapter_files": {
            name: {
                "classes": info["classes"],
                "site_ids": info.get("site_ids", []),
                "domains": info["domains"],
            }
            for name, info in adapter_files.items()
        },
        "adapter_count": len(adapter_files),
        "registry_entries": len(registry),
        "ss4_config_sync": ss4_result,
        "warnings": warnings,
        "errors": errors,
    }

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify adapter coverage against sources.yaml."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Project root directory.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    result = verify_coverage(project_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Exit with error if no domains found at all
    if not result["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
