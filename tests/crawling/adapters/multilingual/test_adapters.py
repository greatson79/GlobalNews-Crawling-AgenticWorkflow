"""Tests for multilingual site adapters (Groups F-J, 77 sites).

Validates:
    - All 77 adapters import and instantiate correctly.
    - Each adapter implements the complete BaseSiteAdapter interface.
    - Site metadata (SITE_ID, LANGUAGE, GROUP) matches specification.
    - Rate limits and anti-block configuration match Step 6 strategy docs.
    - CSS selectors are non-empty for required fields.
    - Article extraction works on minimal HTML fixtures.
    - Paywall detection works for paywalled sites.

Reference:
    Step 5 Architecture Blueprint -- SiteAdapter interface.
    Step 6 crawl-strategy-asia.md (Group F) and crawl-strategy-global.md (Group G-J).
"""

from __future__ import annotations

import pytest

from src.crawling.adapters.base_adapter import BaseSiteAdapter
from src.crawling.adapters.multilingual import MULTILINGUAL_ADAPTERS


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


class TestAdapterRegistry:
    """Verify the adapter registry contains all 77 expected sites."""

    EXPECTED_SITE_IDS = [
        # Group F: Asia-Pacific (23)
        "people", "globaltimes", "scmp", "taiwannews", "yomiuri", "thehindu",
        "mainichi", "asahi", "yahoo_jp", "timesofindia", "hindustantimes",
        "economictimes", "indianexpress", "philstar", "manilatimes", "inquirer",
        "jakartapost", "antaranews", "tempo_id", "focustaiwan", "taipeitimes",
        "vnexpress", "vietnamnews",
        # Group G: Europe/ME (38)
        "thesun", "bild", "lemonde", "themoscowtimes", "arabnews", "aljazeera",
        "israelhayom", "euronews", "spiegel", "sueddeutsche", "welt", "faz",
        "corriere", "repubblica", "ansa", "elpais", "elmundo", "abc_es",
        "lavanguardia", "lefigaro", "liberation", "france24", "ouestfrance",
        "wyborcza", "pap", "idnes", "intellinews", "balkaninsight",
        "centraleuropeantimes", "aftonbladet", "tv2_no", "yle", "icelandmonitor",
        "middleeasteye", "almonitor", "haaretz", "jpost", "jordantimes",
        # Group H: Africa (4)
        "allafrica", "africanews", "theafricareport", "panapress",
        # Group I: Latin America (8)
        "clarin", "lanacion_ar", "folha", "oglobo", "elmercurio", "biobiochile",
        "eltiempo", "elcomercio_pe",
        # Group J: Russia/Central Asia (4)
        "gogo_mn", "ria", "rg", "rbc",
    ]

    def test_registry_count(self):
        assert len(MULTILINGUAL_ADAPTERS) == 77

    @pytest.mark.parametrize("site_id", EXPECTED_SITE_IDS)
    def test_site_in_registry(self, site_id: str):
        assert site_id in MULTILINGUAL_ADAPTERS

    @pytest.mark.parametrize("site_id", EXPECTED_SITE_IDS)
    def test_adapter_is_subclass(self, site_id: str):
        cls = MULTILINGUAL_ADAPTERS[site_id]
        assert issubclass(cls, BaseSiteAdapter)


# ---------------------------------------------------------------------------
# Interface compliance
# ---------------------------------------------------------------------------


class TestInterfaceCompliance:
    """Verify each adapter implements the full BaseSiteAdapter interface."""

    REQUIRED_METHODS = [
        "extract_article",
        "get_section_urls",
        "handle_encoding",
        "normalize_date",
        "get_article_links_from_page",
        "get_rss_urls",
        "get_selectors",
        "get_anti_block_config",
    ]

    @pytest.mark.parametrize("site_id", list(MULTILINGUAL_ADAPTERS.keys()))
    def test_has_all_methods(self, site_id: str):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        for method in self.REQUIRED_METHODS:
            assert hasattr(adapter, method), f"{site_id} missing method: {method}"
            assert callable(getattr(adapter, method))

    @pytest.mark.parametrize("site_id", list(MULTILINGUAL_ADAPTERS.keys()))
    def test_get_section_urls_returns_list(self, site_id: str):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        urls = adapter.get_section_urls()
        assert isinstance(urls, list)
        assert len(urls) > 0
        for url in urls:
            assert url.startswith("http")

    @pytest.mark.parametrize("site_id", list(MULTILINGUAL_ADAPTERS.keys()))
    def test_get_selectors_returns_dict(self, site_id: str):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        selectors = adapter.get_selectors()
        assert isinstance(selectors, dict)
        assert "title_css" in selectors
        assert "body_css" in selectors

    @pytest.mark.parametrize("site_id", list(MULTILINGUAL_ADAPTERS.keys()))
    def test_get_anti_block_config_returns_dict(self, site_id: str):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        config = adapter.get_anti_block_config()
        assert isinstance(config, dict)
        assert "rate_limit" in config
        assert "requires_proxy" in config
        assert config["rate_limit"] > 0


# ---------------------------------------------------------------------------
# Site metadata
# ---------------------------------------------------------------------------


class TestSiteMetadata:
    """Verify site metadata matches the specification."""

    SITE_SPECS = {
        "people":         {"name": "People's Daily",          "lang": "zh", "group": "F", "region": "cn"},
        "globaltimes":    {"name": "Global Times",            "lang": "en", "group": "F", "region": "cn"},
        "scmp":           {"name": "South China Morning Post","lang": "en", "group": "F", "region": "cn"},
        "taiwannews":     {"name": "Taiwan News",             "lang": "en", "group": "F", "region": "tw"},
        "yomiuri":        {"name": "Yomiuri Shimbun",         "lang": "ja", "group": "F", "region": "jp"},
        "thehindu":       {"name": "The Hindu",               "lang": "en", "group": "F", "region": "in"},
        "thesun":         {"name": "The Sun",                 "lang": "en", "group": "G", "region": "uk"},
        "bild":           {"name": "Bild",                    "lang": "de", "group": "G", "region": "de"},
        "lemonde":        {"name": "Le Monde",                "lang": "en", "group": "G", "region": "fr"},
        "themoscowtimes": {"name": "The Moscow Times",        "lang": "en", "group": "G", "region": "ru"},
        "arabnews":       {"name": "Arab News",               "lang": "en", "group": "G", "region": "me"},
        "aljazeera":      {"name": "Al Jazeera English",      "lang": "en", "group": "G", "region": "me"},
        "israelhayom":    {"name": "Israel Hayom",            "lang": "en", "group": "G", "region": "il"},
    }

    @pytest.mark.parametrize("site_id,spec", list(SITE_SPECS.items()))
    def test_site_id_matches(self, site_id: str, spec: dict):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        assert adapter.SITE_ID == site_id

    @pytest.mark.parametrize("site_id,spec", list(SITE_SPECS.items()))
    def test_language_matches(self, site_id: str, spec: dict):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        assert adapter.LANGUAGE == spec["lang"]

    @pytest.mark.parametrize("site_id,spec", list(SITE_SPECS.items()))
    def test_group_matches(self, site_id: str, spec: dict):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        assert adapter.GROUP == spec["group"]

    @pytest.mark.parametrize("site_id,spec", list(SITE_SPECS.items()))
    def test_region_matches(self, site_id: str, spec: dict):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        assert adapter.REGION == spec["region"]

    @pytest.mark.parametrize("site_id,spec", list(SITE_SPECS.items()))
    def test_site_url_valid(self, site_id: str, spec: dict):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        assert adapter.SITE_URL.startswith("http")


# ---------------------------------------------------------------------------
# Rate limits and anti-block (Step 6 compliance)
# ---------------------------------------------------------------------------


class TestRateLimits:
    """Verify rate limits match Step 6 strategy documents."""

    # Sites with MANDATORY crawl-delay from robots.txt
    MANDATORY_RATES = {
        "people": 120.0,     # robots.txt crawl-delay: 120
        "scmp": 10.0,        # robots.txt crawl-delay: 10
        "arabnews": 10.0,    # robots.txt crawl-delay: 10
    }

    @pytest.mark.parametrize("site_id,min_rate", list(MANDATORY_RATES.items()))
    def test_mandatory_rate_limit(self, site_id: str, min_rate: float):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        assert adapter.RATE_LIMIT_SECONDS >= min_rate

    PROXY_REQUIRED = ["yomiuri", "bild"]

    @pytest.mark.parametrize("site_id", PROXY_REQUIRED)
    def test_proxy_required(self, site_id: str):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        assert adapter.REQUIRES_PROXY is True
        assert adapter.PROXY_REGION != ""

    HIGH_BLOCK_SITES = ["yomiuri", "thehindu", "thesun", "bild", "lemonde", "aljazeera"]

    @pytest.mark.parametrize("site_id", HIGH_BLOCK_SITES)
    def test_high_block_level(self, site_id: str):
        adapter = MULTILINGUAL_ADAPTERS[site_id]()
        assert adapter.BOT_BLOCK_LEVEL == "HIGH"


# ---------------------------------------------------------------------------
# Article extraction on minimal HTML fixtures
# ---------------------------------------------------------------------------


class TestArticleExtraction:
    """Test extract_article on minimal HTML fixtures."""

    def test_people_extraction(self):
        adapter = MULTILINGUAL_ADAPTERS["people"]()
        html = """
        <html><body>
        <div class="rm_txt"><h1>Test Chinese Title</h1></div>
        <div class="rm_txt_con"><p>Body text content here.</p></div>
        <div class="box01"><span class="fl">2026年02月26日12:25</span></div>
        </body></html>
        """
        result = adapter.extract_article(html, "http://world.people.com.cn/n1/2026/test.html")
        assert result["title"] == "Test Chinese Title"
        assert "Body text content" in result["body"]
        assert result["category"] == "world"

    def test_scmp_json_ld_extraction(self):
        adapter = MULTILINGUAL_ADAPTERS["scmp"]()
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "NewsArticle", "headline": "SCMP Test", "datePublished": "2026-02-26T10:00:00+08:00",
         "author": {"name": "Test Author"}}
        </script>
        </head><body>
        <h1>SCMP Test</h1>
        <div itemProp="articleBody"><p>Article body text.</p></div>
        </body></html>
        """
        result = adapter.extract_article(html, "https://www.scmp.com/news/china/article/123")
        assert result["title"] == "SCMP Test"
        assert "Article body text" in result["body"]
        assert result["author"] == "Test Author"
        assert result["published_at"] is not None

    def test_yomiuri_ruby_stripping(self):
        adapter = MULTILINGUAL_ADAPTERS["yomiuri"]()
        html = """
        <html><body>
        <h1><ruby>東京<rt>とうきょう</rt></ruby>で大雪</h1>
        <article><p>Article body.</p></article>
        </body></html>
        """
        result = adapter.extract_article(html, "https://www.yomiuri.co.jp/national/20260226-test/")
        assert "とうきょう" not in result["title"]
        assert "東京" in result["title"]

    def test_bild_bildplus_detection(self):
        adapter = MULTILINGUAL_ADAPTERS["bild"]()
        html = """
        <html><body>
        <h1 class="article-headline">BILDplus Test</h1>
        <svg class="bildplus-icon"></svg>
        <div class="article-body"><p>Paywalled content.</p></div>
        </body></html>
        """
        result = adapter.extract_article(html, "https://www.bild.de/politik/test.bild.html")
        assert result["is_paywall_truncated"] is True
        assert result["body"] == ""  # Body skipped for BILDplus

    def test_lemonde_hard_paywall(self):
        adapter = MULTILINGUAL_ADAPTERS["lemonde"]()
        html = """
        <html><body>
        <h1 class="article__title">Le Monde Test</h1>
        <p class="article__desc">Lead paragraph only.</p>
        </body></html>
        """
        result = adapter.extract_article(html, "https://www.lemonde.fr/en/article/test")
        assert result["title"] == "Le Monde Test"
        assert "Lead paragraph only" in result["body"]
        assert result["is_paywall_truncated"] is True

    def test_aljazeera_extraction(self):
        adapter = MULTILINGUAL_ADAPTERS["aljazeera"]()
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "NewsArticle", "headline": "AJ Test", "datePublished": "2026-02-26T10:00:00Z",
         "author": {"name": "AJ Staff"}}
        </script>
        </head><body>
        <h1>AJ Test</h1>
        <div class="wysiwyg"><p>Al Jazeera article body.</p></div>
        </body></html>
        """
        result = adapter.extract_article(html, "https://www.aljazeera.com/news/2026/2/26/test")
        assert result["title"] == "AJ Test"
        assert "Al Jazeera article body" in result["body"]

    def test_arabnews_rtl_stripping(self):
        adapter = MULTILINGUAL_ADAPTERS["arabnews"]()
        html = """
        <html><body>
        <h1 class="page-title">Arab News\u200f Test</h1>
        <div class="field--name-body"><p>Body text with \u200e marks.</p></div>
        </body></html>
        """
        result = adapter.extract_article(html, "https://www.arabnews.com/saudi-arabia/test")
        assert "\u200f" not in result["title"]
        assert "\u200e" not in result["body"]

    def test_israelhayom_rss_extraction(self):
        adapter = MULTILINGUAL_ADAPTERS["israelhayom"]()
        content_encoded = "<p>Full article body from RSS content:encoded.</p>"
        rss_item = {
            "title": "Israel Hayom RSS Test",
            "link": "https://www.israelhayom.com/2026/02/26/test/",
            "dc:creator": "Test Author",
            "pubDate": "Thu, 26 Feb 2026 10:00:00 +0200",
            "category": "News, Politics",
        }
        result = adapter.extract_from_rss_content(content_encoded, rss_item)
        assert result["title"] == "Israel Hayom RSS Test"
        assert "Full article body from RSS" in result["body"]
        assert result["author"] == "Test Author"
        assert result["category"] == "News"

    def test_globaltimes_extraction(self):
        adapter = MULTILINGUAL_ADAPTERS["globaltimes"]()
        html = """
        <html><body>
        <h3>GT Test Headline</h3>
        <div class="article_right"><p>GT article body content.</p></div>
        </body></html>
        """
        result = adapter.extract_article(html, "https://www.globaltimes.cn/page/202602/test.shtml")
        assert result["title"] == "GT Test Headline"
        assert "GT article body content" in result["body"]

    def test_themoscowtimes_extraction(self):
        adapter = MULTILINGUAL_ADAPTERS["themoscowtimes"]()
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "NewsArticle", "headline": "MT Test",
         "datePublished": "2026-02-26T10:00:00+03:00",
         "author": {"name": "MT Author"}}
        </script>
        </head><body>
        <h1>MT Test</h1>
        <div class="article__content"><p>Moscow Times body.</p></div>
        </body></html>
        """
        result = adapter.extract_article(html, "https://www.themoscowtimes.com/2026/02/26/test")
        assert result["title"] == "MT Test"
        assert "Moscow Times body" in result["body"]
        assert result["author"] == "MT Author"
