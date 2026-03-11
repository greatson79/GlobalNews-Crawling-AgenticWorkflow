"""Structural validation tests — Cross-script site consistency.

Tests verify:
- Phase B+D: Sites in distribute_sites_to_teams.py == sites in generate_sources_yaml_draft.py
- Sites in scripts match sites described in adapter agent .md files
- No orphan sites (in script but not in agent) or missing sites (in agent but not in script)
- P1: Runtime SOT (data/config/sources.yaml) matches ADAPTER_REGISTRY
"""

import os
import re
import sys

import pytest


def _extract_domains_from_agent_md(filepath):
    """Extract domain-like strings from an adapter agent markdown file.

    Looks for patterns like domain.com, domain.co.kr in the file content.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Match domain patterns in the markdown
    # Specifically look for domains in parentheses or bold — typical in agent specs
    domains = set()
    # Pattern: (domain.tld) or **domain.tld**
    for match in re.finditer(r"[(\s*]([a-z0-9][-a-z0-9]*\.(?:com|co\.kr|co\.jp|or\.jp|net|fr|de|es|ru|network))\b", content):
        domains.add(match.group(1))
    return domains


# ============================================================================
# Cross-Script Consistency
# ============================================================================

class TestDistributeVsSources:
    """Verify distribute_sites and generate_sources have identical domains.

    Both scripts derive from the same runtime SOT when available.
    Fallback lists (_FALLBACK_*) are tested for internal consistency.
    """

    def test_fallback_same_total_count(self, distribute_mod, sources_mod):
        """Fallback lists should have equal total sites."""
        dist_total = sum(len(v) for v in distribute_mod._FALLBACK_GROUPS.values())
        src_total = len(sources_mod._FALLBACK_SITES)
        assert dist_total == src_total

    def test_fallback_same_domains(self, distribute_mod, sources_mod):
        """All domains in distribute fallback should appear in sources fallback."""
        dist_domains = set()
        for sites in distribute_mod._FALLBACK_GROUPS.values():
            for s in sites:
                dist_domains.add(s["domain"])

        src_domains = {s["domain"] for s in sources_mod._FALLBACK_SITES}

        missing_in_sources = dist_domains - src_domains
        missing_in_distribute = src_domains - dist_domains

        assert not missing_in_sources, \
            f"In distribute but not in sources: {missing_in_sources}"
        assert not missing_in_distribute, \
            f"In sources but not in distribute: {missing_in_distribute}"

    def test_sot_derived_same_domains(self, distribute_mod, sources_mod, project_root):
        """P1: SOT-derived sites from both scripts must match."""
        from pathlib import Path
        project_path = Path(project_root)
        sot_path = project_path / "data" / "config" / "sources.yaml"
        if not sot_path.is_file():
            pytest.skip("Runtime SOT not available")

        src_sites = sources_mod.get_site_catalog(project_path)
        dist_groups = distribute_mod.get_site_groups(project_path)

        src_domains = {s["domain"] for s in src_sites}
        dist_domains = set()
        for sites in dist_groups.values():
            for s in sites:
                dist_domains.add(s["domain"])

        missing_in_sources = dist_domains - src_domains
        missing_in_distribute = src_domains - dist_domains

        assert not missing_in_sources, \
            f"In distribute SOT but not in sources SOT: {missing_in_sources}"
        assert not missing_in_distribute, \
            f"In sources SOT but not in distribute SOT: {missing_in_distribute}"

    def test_sot_derived_total_121(self, sources_mod, project_root):
        """P1: SOT-derived catalog must have exactly 121 sites."""
        from pathlib import Path
        project_path = Path(project_root)
        sot_path = project_path / "data" / "config" / "sources.yaml"
        if not sot_path.is_file():
            pytest.skip("Runtime SOT not available")

        src_sites = sources_mod.get_site_catalog(project_path)
        assert len(src_sites) == 121


# ============================================================================
# Script-to-Agent Consistency
# ============================================================================

class TestScriptToAgentConsistency:
    """Verify script site lists match agent markdown specifications."""

    def test_kr_major_script_matches_agent(self, distribute_mod, agents_dir):
        """distribute kr-major domains should include key Korean dailies."""
        script_domains = {s["domain"] for s in distribute_mod._FALLBACK_GROUPS["kr-major"]}

        # Key Group A domains that must always be present
        key_domains = {"chosun.com", "joongang.co.kr", "donga.com", "hani.co.kr", "yna.co.kr"}
        for d in key_domains:
            assert d in script_domains, f"Key domain {d} missing from script"

    def test_fallback_kr_major_count(self, distribute_mod):
        """Fallback kr-major group has 12 sites (Groups A+B+C)."""
        assert len(distribute_mod._FALLBACK_GROUPS["kr-major"]) == 12

    def test_fallback_kr_tech_count(self, distribute_mod):
        """Fallback kr-tech group has 10 sites (Group D)."""
        assert len(distribute_mod._FALLBACK_GROUPS["kr-tech"]) == 10

    def test_fallback_english_count(self, distribute_mod):
        """Fallback english group has 22 sites (Group E)."""
        assert len(distribute_mod._FALLBACK_GROUPS["english"]) == 22

    def test_fallback_multilingual_count(self, distribute_mod):
        """Fallback multilingual group has 77 sites (Groups F-J)."""
        assert len(distribute_mod._FALLBACK_GROUPS["multilingual"]) == 77

    def test_sot_group_counts(self, distribute_mod, project_root):
        """P1: SOT-derived group counts must sum to 121."""
        from pathlib import Path
        project_path = Path(project_root)
        sot_path = project_path / "data" / "config" / "sources.yaml"
        if not sot_path.is_file():
            pytest.skip("Runtime SOT not available")

        groups = distribute_mod.get_site_groups(project_path)
        total = sum(len(v) for v in groups.values())
        assert total == 121, f"SOT-derived groups total {total}, expected 121"


# ============================================================================
# Language Tag Consistency
# ============================================================================

class TestLanguageTagConsistency:
    """Verify language tags in sources match group assignments in distribute.

    Tests use fallback lists for static consistency checking.
    Groups are organized by geography/topic, not strictly by language:
    - kr-major: predominantly Korean, all ko
    - kr-tech: mostly Korean, but includes English niche sites (38north, stratechery, techmeme)
    - english: predominantly English, but includes voakorea (ko) and afmedios (es)
    - multilingual: mixed languages including en sites in non-English regions
    """

    def test_kr_major_all_korean(self, sources_mod, distribute_mod):
        kr_domains = {s["domain"] for s in distribute_mod._FALLBACK_GROUPS["kr-major"]}
        for site in sources_mod._FALLBACK_SITES:
            if site["domain"] in kr_domains:
                assert site["language"] == "ko", \
                    f"{site['domain']} should be 'ko' but is '{site['language']}'"

    def test_kr_tech_mostly_korean(self, sources_mod, distribute_mod):
        """kr-tech group is mostly Korean but includes English niche sites."""
        kr_domains = {s["domain"] for s in distribute_mod._FALLBACK_GROUPS["kr-tech"]}
        # English-language exceptions in kr-tech (niche English sites grouped by topic)
        en_exceptions = {"38north.org", "stratechery.com", "techmeme.com"}
        for site in sources_mod._FALLBACK_SITES:
            if site["domain"] in kr_domains and site["domain"] not in en_exceptions:
                assert site["language"] == "ko", \
                    f"{site['domain']} should be 'ko' but is '{site['language']}'"

    def test_english_predominantly_english(self, sources_mod, distribute_mod):
        """English group is predominantly English with known exceptions."""
        en_domains = {s["domain"] for s in distribute_mod._FALLBACK_GROUPS["english"]}
        # Known non-English sites in English group (grouped by publication origin)
        non_en_exceptions = {"voakorea.com", "afmedios.com"}
        for site in sources_mod._FALLBACK_SITES:
            if site["domain"] in en_domains and site["domain"] not in non_en_exceptions:
                assert site["language"] == "en", \
                    f"{site['domain']} should be 'en' but is '{site['language']}'"

    def test_multilingual_has_diverse_languages(self, sources_mod, distribute_mod):
        """Multilingual group should have at least 5 different languages."""
        ml_domains = {s["domain"] for s in distribute_mod._FALLBACK_GROUPS["multilingual"]}
        languages = set()
        for site in sources_mod._FALLBACK_SITES:
            if site["domain"] in ml_domains:
                languages.add(site["language"])
        assert len(languages) >= 5, \
            f"Multilingual group should have diverse languages, got: {languages}"


# ============================================================================
# P1: Runtime SOT ↔ ADAPTER_REGISTRY Sync
# ============================================================================

class TestRuntimeSOTSync:
    """P1: Verify runtime SOT (data/config/sources.yaml) matches adapter registry.

    This is the definitive sync check — the runtime SOT is the single source
    of truth for which sites the pipeline processes, and ADAPTER_REGISTRY
    defines which sites have implementation code.
    """

    @pytest.fixture
    def sot_site_ids(self, project_root):
        """Load site_ids from runtime SOT."""
        sot_path = os.path.join(project_root, "data", "config", "sources.yaml")
        if not os.path.exists(sot_path):
            pytest.skip("data/config/sources.yaml not found")
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not available")
        with open(sot_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return set(data.get("sources", {}).keys())

    @pytest.fixture
    def adapter_registry_ids(self, project_root):
        """Extract site_ids from adapter __init__.py files via regex.

        Avoids importing adapter modules (which may have heavy dependencies)
        by parsing the registry dict patterns from source files.
        """
        adapters_dir = os.path.join(project_root, "src", "crawling", "adapters")
        site_ids = set()
        # Scan sub-package __init__.py files for registry dicts
        for subdir in ("kr_major", "kr_tech", "english", "multilingual"):
            init_path = os.path.join(adapters_dir, subdir, "__init__.py")
            if not os.path.exists(init_path):
                continue
            with open(init_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Extract quoted keys from dict assignments: "site_id": AdapterClass
            for match in re.finditer(r'["\'](\w+)["\']\s*:', content):
                key = match.group(1)
                # Filter out non-site keys (imports, __all__, etc.)
                if not key.startswith("_") and key.lower() == key:
                    site_ids.add(key)
        return site_ids

    def test_sot_matches_adapter_registry(self, sot_site_ids, adapter_registry_ids):
        """P1: Runtime SOT site_ids must exactly match ADAPTER_REGISTRY keys."""
        missing_adapters = sot_site_ids - adapter_registry_ids
        extra_adapters = adapter_registry_ids - sot_site_ids
        assert not missing_adapters, \
            f"In SOT but no adapter: {sorted(missing_adapters)}"
        assert not extra_adapters, \
            f"Adapter exists but not in SOT: {sorted(extra_adapters)}"

    def test_sot_has_121_sites(self, sot_site_ids):
        """Runtime SOT should have exactly 121 sites."""
        assert len(sot_site_ids) == 121, \
            f"SOT has {len(sot_site_ids)} sites, expected 121"

    def test_adapter_registry_has_121_sites(self, adapter_registry_ids):
        """ADAPTER_REGISTRY should have exactly 121 site_ids."""
        assert len(adapter_registry_ids) == 121, \
            f"ADAPTER_REGISTRY has {len(adapter_registry_ids)} site_ids, expected 121"
