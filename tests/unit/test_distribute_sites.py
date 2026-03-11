"""Unit tests for distribute_sites_to_teams.py — Phase B: Site Distribution.

Tests verify:
- Site count per group matches adapter agent definitions
- Canonical domains are present in each group
- No duplicate domains across groups
- Total sites = 121
- Distribution output format
"""

import json
import os

import pytest


# ============================================================================
# Site Count Tests
# ============================================================================

class TestSiteGroupCounts:
    """Verify each group has the exact count matching adapter agents."""

    def test_kr_major_count_is_12(self, distribute_mod):
        assert len(distribute_mod._FALLBACK_GROUPS["kr-major"]) == 12

    def test_kr_tech_count_is_10(self, distribute_mod):
        assert len(distribute_mod._FALLBACK_GROUPS["kr-tech"]) == 10

    def test_english_count_is_22(self, distribute_mod):
        assert len(distribute_mod._FALLBACK_GROUPS["english"]) == 22

    def test_multilingual_count_is_77(self, distribute_mod):
        assert len(distribute_mod._FALLBACK_GROUPS["multilingual"]) == 77

    def test_total_sites_is_121(self, distribute_mod):
        total = sum(
            len(sites) for sites in distribute_mod._FALLBACK_GROUPS.values()
        )
        assert total == 121


# ============================================================================
# Canonical Domain Tests
# ============================================================================

class TestCanonicalDomains:
    """Verify each group contains the correct domains per adapter agent spec."""

    def _domains(self, mod, group_key):
        return {s["domain"] for s in mod._FALLBACK_GROUPS[group_key]}

    def test_kr_major_group_a_dailies(self, distribute_mod):
        """Group A — Korean Major Dailies (5)."""
        domains = self._domains(distribute_mod, "kr-major")
        expected_a = {"chosun.com", "joongang.co.kr", "donga.com", "hani.co.kr", "yna.co.kr"}
        assert expected_a.issubset(domains)

    def test_kr_major_group_b_economy(self, distribute_mod):
        """Group B — Korean Economy (4)."""
        domains = self._domains(distribute_mod, "kr-major")
        expected_b = {"mk.co.kr", "hankyung.com", "fnnews.com", "mt.co.kr"}
        assert expected_b.issubset(domains)

    def test_kr_major_group_c_niche(self, distribute_mod):
        """Group C — Korean Niche (3)."""
        domains = self._domains(distribute_mod, "kr-major")
        expected_c = {"nocutnews.co.kr", "kmib.co.kr", "ohmynews.com"}
        assert expected_c.issubset(domains)

    def test_kr_tech_domains(self, distribute_mod):
        """Group D — Korean IT/Tech (10) per kr_tech adapter registry."""
        domains = self._domains(distribute_mod, "kr-tech")
        expected = {
            "38north.org", "bloter.net", "etnews.com", "sciencetimes.co.kr",
            "zdnet.co.kr", "irobotnews.com", "techneedle.com",
            "insight.co.kr", "stratechery.com", "techmeme.com",
        }
        assert expected.issubset(domains)

    def test_english_key_sites(self, distribute_mod):
        """English key sites: NYT, WSJ, FT, CNN, Bloomberg."""
        domains = self._domains(distribute_mod, "english")
        expected = {"nytimes.com", "wsj.com", "ft.com", "bloomberg.com"}
        assert expected.issubset(domains)

    def test_english_new_sites(self, distribute_mod):
        """Newly added English sites: BBC, Guardian, Wired, etc."""
        domains = self._domains(distribute_mod, "english")
        expected = {"bbc.com", "theguardian.com", "wired.com", "politico.eu"}
        assert expected.issubset(domains)

    def test_multilingual_japanese(self, distribute_mod):
        """Asia-Pacific Japanese sites."""
        domains = self._domains(distribute_mod, "multilingual")
        expected = {"yomiuri.co.jp", "asahi.com", "mainichi.jp"}
        assert expected.issubset(domains)

    def test_multilingual_chinese(self, distribute_mod):
        """Asia-Pacific Chinese sites."""
        domains = self._domains(distribute_mod, "multilingual")
        expected = {"people.com.cn", "scmp.com", "globaltimes.cn"}
        assert expected.issubset(domains)

    def test_multilingual_german(self, distribute_mod):
        """European German-language sites."""
        domains = self._domains(distribute_mod, "multilingual")
        expected = {"bild.de", "spiegel.de", "sueddeutsche.de", "welt.de", "faz.net"}
        assert expected.issubset(domains)

    def test_multilingual_european(self, distribute_mod):
        """European non-German sites."""
        domains = self._domains(distribute_mod, "multilingual")
        expected = {"lemonde.fr", "elpais.com", "corriere.it", "repubblica.it"}
        assert expected.issubset(domains)

    def test_multilingual_africa(self, distribute_mod):
        """Group H — Africa (4)."""
        domains = self._domains(distribute_mod, "multilingual")
        expected = {"allafrica.com", "africanews.com", "theafricareport.com", "panapress.com"}
        assert expected.issubset(domains)

    def test_multilingual_latam(self, distribute_mod):
        """Group I — Latin America (8)."""
        domains = self._domains(distribute_mod, "multilingual")
        expected = {"clarin.com", "folha.uol.com.br", "eltiempo.com"}
        assert expected.issubset(domains)

    def test_multilingual_russia(self, distribute_mod):
        """Group J — Russia/Central Asia (4)."""
        domains = self._domains(distribute_mod, "multilingual")
        expected = {"ria.ru", "rg.ru", "rbc.ru"}
        assert expected.issubset(domains)


# ============================================================================
# Duplicate Detection
# ============================================================================

class TestNoDuplicates:
    """Verify no domain appears in multiple groups."""

    def test_no_duplicate_domains_across_groups(self, distribute_mod):
        all_domains = []
        for group_key, sites in distribute_mod._FALLBACK_GROUPS.items():
            for site in sites:
                all_domains.append((site["domain"], group_key))

        domain_only = [d for d, _ in all_domains]
        duplicates = [d for d in domain_only if domain_only.count(d) > 1]
        assert len(duplicates) == 0, f"Duplicate domains: {set(duplicates)}"

    def test_no_duplicate_domains_within_group(self, distribute_mod):
        for group_key, sites in distribute_mod._FALLBACK_GROUPS.items():
            domains = [s["domain"] for s in sites]
            assert len(domains) == len(set(domains)), \
                f"Duplicates within {group_key}: {[d for d in domains if domains.count(d) > 1]}"


# ============================================================================
# Distribution Output Format
# ============================================================================

class TestDistributeOutput:
    """Test the distribute_sites function output."""

    def test_distribute_creates_output_files(self, distribute_mod, tmp_path):
        """Distribution should create 4 JSON files."""
        from pathlib import Path
        result = distribute_mod.distribute_sites(Path(tmp_path))
        assert result["valid"] is True
        assert result["total_sites"] == 121

        for group in ["kr-major", "kr-tech", "english", "multilingual"]:
            assert group in result["output_paths"]
            assert os.path.exists(result["output_paths"][group])

    def test_output_json_format(self, distribute_mod, tmp_path):
        """Each output file should be valid JSON with group/sites structure."""
        from pathlib import Path
        result = distribute_mod.distribute_sites(Path(tmp_path))

        for group, path in result["output_paths"].items():
            with open(path) as f:
                data = json.load(f)
            assert "group" in data
            assert "total_sites" in data
            assert "sites" in data
            assert data["group"] == group

    def test_all_sites_have_domain_and_name(self, distribute_mod):
        """Every site entry must have domain and name fields."""
        for group_key, sites in distribute_mod._FALLBACK_GROUPS.items():
            for site in sites:
                assert "domain" in site, f"Missing domain in {group_key}: {site}"
                assert "name" in site, f"Missing name in {group_key}: {site}"
                assert len(site["domain"]) > 0
                assert len(site["name"]) > 0
