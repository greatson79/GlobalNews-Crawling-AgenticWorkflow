"""Tests for URL Discovery: RSS parsing, sitemap parsing, DOM navigation, URL normalization.

Tests cover:
    - URL normalization (tracking params, relative URLs, canonicalization)
    - Article URL heuristic filtering
    - RSS 2.0 and Atom feed parsing with malformed XML graceful handling
    - Sitemap parsing including sitemap index (nested sitemaps)
    - DOM navigation with CSS selectors
    - Discovery pipeline fallback chain
    - Date parsing utilities
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import ParseError as ETParseError

import pytest

from src.crawling.url_discovery import (
    normalize_url,
    is_article_url,
    RSSParser,
    SitemapParser,
    DOMNavigator,
    URLDiscovery,
    _parse_datetime_string,
    TRACKING_PARAMS,
)
from src.crawling.contracts import DiscoveredURL
from src.crawling.network_guard import NetworkGuard, FetchResponse
from src.utils.error_handler import NetworkError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_guard():
    """Create a mock NetworkGuard."""
    guard = MagicMock(spec=NetworkGuard)
    return guard


def _make_fetch_response(text: str, url: str = "https://example.com") -> FetchResponse:
    """Helper to create a FetchResponse from text content."""
    return FetchResponse(
        url=url,
        status_code=200,
        headers={"content-type": "text/html"},
        text=text,
        content=text.encode("utf-8"),
        elapsed_seconds=0.5,
        encoding="utf-8",
        content_type="text/html",
    )


# ===========================================================================
# URL Normalization Tests
# ===========================================================================

class TestNormalizeURL:
    """Tests for normalize_url()."""

    def test_strips_utm_params(self):
        """Tracking parameters (utm_*) should be stripped."""
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=123"
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=123" in result

    def test_strips_fbclid(self):
        """Facebook click ID should be stripped."""
        url = "https://example.com/article?fbclid=abc123&page=1"
        result = normalize_url(url)
        assert "fbclid" not in result
        assert "page=1" in result

    def test_strips_gclid(self):
        """Google click ID should be stripped."""
        url = "https://example.com/article?gclid=xyz789"
        result = normalize_url(url)
        assert "gclid" not in result
        assert result == "https://example.com/article"

    def test_lowercases_hostname(self):
        """Hostname should be lowercased."""
        url = "https://WWW.EXAMPLE.COM/Article/123"
        result = normalize_url(url)
        assert "www.example.com" in result
        # Path case should be preserved
        assert "/Article/123" in result

    def test_resolves_relative_url(self):
        """Relative URLs should be resolved against base_url."""
        url = "/article/123"
        result = normalize_url(url, base_url="https://example.com")
        assert result == "https://example.com/article/123"

    def test_strips_fragment(self):
        """URL fragments (#...) should be removed."""
        url = "https://example.com/article#comments"
        result = normalize_url(url)
        assert "#" not in result

    def test_strips_trailing_slash(self):
        """Trailing slashes should be removed (except root)."""
        url = "https://example.com/article/"
        result = normalize_url(url)
        assert result.endswith("/article")

    def test_root_path_keeps_slash(self):
        """Root path should keep its slash."""
        url = "https://example.com/"
        result = normalize_url(url)
        assert result.endswith("/")

    def test_sorts_query_params(self):
        """Query parameters should be sorted for consistency."""
        url1 = "https://example.com/search?b=2&a=1"
        url2 = "https://example.com/search?a=1&b=2"
        assert normalize_url(url1) == normalize_url(url2)

    def test_empty_url_returns_empty(self):
        """Empty URL should return empty string."""
        assert normalize_url("") == ""
        assert normalize_url("   ") == ""

    def test_invalid_url_returns_empty(self):
        """Invalid URLs (no scheme) should return empty."""
        assert normalize_url("not-a-url") == ""
        assert normalize_url("ftp://example.com") == ""

    def test_strips_default_ports(self):
        """Default ports (80, 443) should be stripped."""
        url = "https://example.com:443/article"
        result = normalize_url(url)
        assert ":443" not in result

    def test_preserves_non_default_ports(self):
        """Non-default ports should be preserved."""
        url = "https://example.com:8080/article"
        result = normalize_url(url)
        assert ":8080" in result


class TestIsArticleURL:
    """Tests for is_article_url() heuristic filtering."""

    def test_rejects_image_urls(self):
        """Image URLs should be rejected."""
        assert is_article_url("https://example.com/image.jpg") is False
        assert is_article_url("https://example.com/photo.png") is False

    def test_rejects_asset_urls(self):
        """CSS/JS/font URLs should be rejected."""
        assert is_article_url("https://example.com/style.css") is False
        assert is_article_url("https://example.com/app.js") is False

    def test_rejects_category_pages(self):
        """Category/tag pages should be rejected."""
        assert is_article_url("https://example.com/category/politics") is False
        assert is_article_url("https://example.com/tag/economy") is False

    def test_rejects_admin_pages(self):
        """Admin/login pages should be rejected."""
        assert is_article_url("https://example.com/wp-admin/post") is False
        assert is_article_url("https://example.com/login") is False

    def test_accepts_article_urls(self):
        """Article-like URLs should be accepted."""
        assert is_article_url("https://example.com/2024/01/15/breaking-news") is True
        assert is_article_url("https://example.com/article/12345") is True
        assert is_article_url("https://example.com/news/politics/scandal-update") is True

    def test_rejects_empty_url(self):
        """Empty URL should be rejected."""
        assert is_article_url("") is False

    def test_rejects_root_path(self):
        """Root path (homepage) should be rejected."""
        assert is_article_url("https://example.com/") is False


# ===========================================================================
# RSS Parser Tests
# ===========================================================================

class TestRSSParser:
    """Tests for RSSParser (Tier 1)."""

    def test_parse_rss_20_feed(self, mock_guard):
        """Should parse standard RSS 2.0 feeds."""
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Test Feed</title>
            <item>
              <title>Breaking News Article</title>
              <link>https://example.com/2024/01/breaking-news</link>
              <pubDate>Mon, 20 Jan 2025 10:00:00 GMT</pubDate>
            </item>
            <item>
              <title>Sports Update</title>
              <link>https://example.com/2024/01/sports-update</link>
              <pubDate>Mon, 20 Jan 2025 09:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>"""

        mock_guard.fetch.return_value = _make_fetch_response(rss_xml)
        parser = RSSParser(mock_guard)

        results = parser._parse_feed_raw(
            "https://example.com/rss", "test_site", max_age_days=365
        )

        assert len(results) >= 2
        assert all(isinstance(r, DiscoveredURL) for r in results)
        assert results[0].discovered_via == "rss"
        assert results[0].source_id == "test_site"

    def test_parse_atom_feed(self, mock_guard):
        """Should parse Atom feeds."""
        atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Test Atom Feed</title>
          <entry>
            <title>Atom Article</title>
            <link href="https://example.com/2024/01/atom-article"/>
            <published>2025-01-20T10:00:00Z</published>
          </entry>
        </feed>"""

        mock_guard.fetch.return_value = _make_fetch_response(atom_xml)
        parser = RSSParser(mock_guard)

        results = parser._parse_feed_raw(
            "https://example.com/atom", "test_site", max_age_days=365
        )

        assert len(results) >= 1
        assert "atom-article" in results[0].url

    def test_malformed_xml_no_crash(self, mock_guard):
        """Malformed XML should not crash -- return empty list."""
        bad_xml = "This is not XML at all <broken>"

        mock_guard.fetch.return_value = _make_fetch_response(bad_xml)
        parser = RSSParser(mock_guard)

        results = parser._parse_feed_raw(
            "https://example.com/bad-rss", "test_site"
        )

        assert results == []

    def test_empty_feed_returns_empty(self, mock_guard):
        """Empty feed (no items) should return empty list."""
        empty_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Empty Feed</title>
          </channel>
        </rss>"""

        mock_guard.fetch.return_value = _make_fetch_response(empty_rss)
        parser = RSSParser(mock_guard)

        results = parser._parse_feed_raw(
            "https://example.com/empty-rss", "test_site"
        )

        assert results == []

    def test_network_error_returns_empty(self, mock_guard):
        """Network errors should return empty list (no crash)."""
        mock_guard.fetch.side_effect = NetworkError("Connection failed", url="https://example.com/rss")
        parser = RSSParser(mock_guard)

        results = parser._parse_feed_raw(
            "https://example.com/rss", "test_site"
        )

        assert results == []

    def test_filters_non_article_urls(self, mock_guard):
        """Non-article URLs (images, categories) should be filtered out."""
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Real Article</title>
              <link>https://example.com/2024/01/real-article</link>
            </item>
            <item>
              <title>Image</title>
              <link>https://example.com/image.jpg</link>
            </item>
            <item>
              <title>Category</title>
              <link>https://example.com/category/news</link>
            </item>
          </channel>
        </rss>"""

        mock_guard.fetch.return_value = _make_fetch_response(rss_xml)
        parser = RSSParser(mock_guard)

        results = parser._parse_feed_raw(
            "https://example.com/rss", "test_site", max_age_days=365
        )

        urls = [r.url for r in results]
        assert any("real-article" in u for u in urls)
        assert not any("image.jpg" in u for u in urls)


# ===========================================================================
# Sitemap Parser Tests
# ===========================================================================

class TestSitemapParser:
    """Tests for SitemapParser (Tier 1)."""

    def test_parse_basic_urlset(self, mock_guard):
        """Should parse basic sitemap <urlset>."""
        # Use relative dates so the test doesn't break over time
        recent_date = (datetime.now(timezone.utc) - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
        older_date = (datetime.now(timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ")

        sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url>
            <loc>https://example.com/2024/01/article-one</loc>
            <lastmod>{recent_date}</lastmod>
          </url>
          <url>
            <loc>https://example.com/2024/01/article-two</loc>
            <lastmod>{older_date}</lastmod>
          </url>
        </urlset>"""

        mock_guard.fetch.return_value = _make_fetch_response(sitemap_xml)
        parser = SitemapParser(mock_guard)

        results = parser.parse_sitemap(
            "https://example.com/sitemap.xml",
            "test_site",
            max_age_days=1,
        )

        assert len(results) >= 2
        assert all(r.discovered_via == "sitemap" for r in results)

    def test_parse_sitemap_index(self, mock_guard):
        """Should parse sitemap index and recurse into child sitemaps."""
        recent = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

        index_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <sitemap>
            <loc>https://example.com/sitemap-news.xml</loc>
            <lastmod>{recent}</lastmod>
          </sitemap>
        </sitemapindex>"""

        child_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url>
            <loc>https://example.com/2024/01/nested-article</loc>
            <lastmod>{recent}</lastmod>
          </url>
        </urlset>"""

        # First call returns index, second returns child
        mock_guard.fetch.side_effect = [
            _make_fetch_response(index_xml),
            _make_fetch_response(child_xml),
        ]

        parser = SitemapParser(mock_guard)
        results = parser.parse_sitemap(
            "https://example.com/sitemap.xml",
            "test_site",
            max_age_days=1,
        )

        assert len(results) >= 1
        assert "nested-article" in results[0].url

    def test_malformed_sitemap_no_crash(self, mock_guard):
        """Malformed sitemap XML should not crash."""
        bad_xml = "<broken xml garbage"

        mock_guard.fetch.return_value = _make_fetch_response(bad_xml)
        parser = SitemapParser(mock_guard)

        results = parser.parse_sitemap(
            "https://example.com/sitemap.xml",
            "test_site",
        )

        assert results == []

    def test_relative_sitemap_url_resolved(self, mock_guard):
        """Relative sitemap URL should be resolved against base_url."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url>
            <loc>https://example.com/article/1</loc>
          </url>
        </urlset>"""

        mock_guard.fetch.return_value = _make_fetch_response(sitemap_xml)
        parser = SitemapParser(mock_guard)

        results = parser.parse_sitemap(
            "/sitemap.xml",
            "test_site",
            base_url="https://example.com",
            max_age_days=365,
        )

        # The sitemap URL should have been resolved
        mock_guard.fetch.assert_called_once()
        call_url = mock_guard.fetch.call_args[0][0]
        assert call_url.startswith("https://")

    def test_url_pattern_filter(self, mock_guard):
        """url_pattern should filter URLs by regex."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/news/article-1</loc></url>
          <url><loc>https://example.com/sports/game-1</loc></url>
          <url><loc>https://example.com/news/article-2</loc></url>
        </urlset>"""

        mock_guard.fetch.return_value = _make_fetch_response(sitemap_xml)
        parser = SitemapParser(mock_guard)

        results = parser.parse_sitemap(
            "https://example.com/sitemap.xml",
            "test_site",
            max_age_days=365,
            url_pattern=r"/news/",
        )

        assert all("/news/" in r.url for r in results)

    def test_max_urls_limit(self, mock_guard):
        """max_urls should cap the number of collected URLs."""
        urls = "\n".join(
            f"<url><loc>https://example.com/article/{i}</loc></url>"
            for i in range(100)
        )
        sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        {urls}
        </urlset>"""

        mock_guard.fetch.return_value = _make_fetch_response(sitemap_xml)
        parser = SitemapParser(mock_guard)

        results = parser.parse_sitemap(
            "https://example.com/sitemap.xml",
            "test_site",
            max_age_days=365,
            max_urls=10,
        )

        assert len(results) <= 10


# ===========================================================================
# DOM Navigator Tests
# ===========================================================================

class TestDOMNavigator:
    """Tests for DOMNavigator (Tier 2)."""

    def test_extracts_article_links(self, mock_guard):
        """Should extract article links from HTML page."""
        html = """
        <html><body>
          <div class="articles">
            <a href="/2024/01/article-1">Article 1</a>
            <a href="/2024/01/article-2">Article 2</a>
            <a href="/category/news">News Category</a>
            <a href="/image.jpg">Image</a>
          </div>
        </body></html>"""

        mock_guard.fetch.return_value = _make_fetch_response(
            html, url="https://example.com/news"
        )
        nav = DOMNavigator(mock_guard)

        results = nav.discover_from_page(
            "https://example.com/news",
            source_id="test_site",
            base_url="https://example.com",
        )

        urls = [r.url for r in results]
        assert any("article-1" in u for u in urls)
        assert any("article-2" in u for u in urls)
        # Category and image should be filtered
        assert not any("category" in u for u in urls)
        assert not any("image.jpg" in u for u in urls)

    def test_custom_css_selector(self, mock_guard):
        """Custom CSS selectors should limit extraction scope."""
        html = """
        <html><body>
          <nav><a href="/about">About</a></nav>
          <div class="article-list">
            <a href="/story/1" class="article-link">Story 1</a>
            <a href="/story/2" class="article-link">Story 2</a>
          </div>
        </body></html>"""

        mock_guard.fetch.return_value = _make_fetch_response(html)
        nav = DOMNavigator(mock_guard)

        results = nav.discover_from_page(
            "https://example.com/list",
            source_id="test_site",
            article_link_selector="a.article-link",
            base_url="https://example.com",
        )

        assert len(results) == 2
        assert all("story" in r.url for r in results)

    def test_deduplicates_links(self, mock_guard):
        """Duplicate URLs on the same page should be deduplicated."""
        html = """
        <html><body>
          <a href="/article/1">Link 1</a>
          <a href="/article/1">Link 1 again</a>
          <a href="/article/2">Link 2</a>
        </body></html>"""

        mock_guard.fetch.return_value = _make_fetch_response(html)
        nav = DOMNavigator(mock_guard)

        results = nav.discover_from_page(
            "https://example.com",
            source_id="test_site",
            base_url="https://example.com",
        )

        urls = [r.url for r in results]
        assert len(urls) == len(set(urls))  # All unique


# ===========================================================================
# Date Parsing Tests
# ===========================================================================

class TestDateParsing:
    """Tests for _parse_datetime_string()."""

    def test_iso_8601_with_timezone(self):
        """ISO 8601 with timezone offset should parse correctly."""
        dt = _parse_datetime_string("2025-01-20T10:00:00+09:00")
        assert dt is not None
        assert dt.tzinfo is not None
        # Should be converted to UTC
        assert dt.hour == 1  # 10:00 +09:00 = 01:00 UTC

    def test_iso_8601_utc_z(self):
        """ISO 8601 with Z suffix should parse as UTC."""
        dt = _parse_datetime_string("2025-01-20T10:00:00Z")
        assert dt is not None
        assert dt.tzinfo == timezone.utc

    def test_date_only(self):
        """Date-only string should parse with midnight UTC."""
        dt = _parse_datetime_string("2025-01-20")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 20

    def test_rfc_2822_format(self):
        """RFC 2822 date format (common in RSS) should parse."""
        dt = _parse_datetime_string("Mon, 20 Jan 2025 10:00:00 GMT")
        assert dt is not None
        assert dt.year == 2025

    def test_none_for_empty(self):
        """Empty/None input should return None."""
        assert _parse_datetime_string("") is None
        assert _parse_datetime_string("   ") is None

    def test_none_for_garbage(self):
        """Garbage input should return None (not raise)."""
        assert _parse_datetime_string("not a date") is None
        assert _parse_datetime_string("abc123") is None

    def test_datetime_with_space_separator(self):
        """Datetime with space separator should parse."""
        dt = _parse_datetime_string("2025-01-20 10:00:00")
        assert dt is not None
        assert dt.hour == 10


# ===========================================================================
# URL Discovery Pipeline Tests
# ===========================================================================

class TestURLDiscoveryPipeline:
    """Tests for the URLDiscovery orchestrator."""

    def test_rss_first_in_chain(self, mock_guard):
        """RSS should be tried first when configured as primary method."""
        site_config = {
            "url": "https://example.com",
            "crawl": {
                "primary_method": "rss",
                "fallback_methods": ["sitemap", "dom"],
                "rss_url": "https://example.com/rss",
                "sitemap_url": "/sitemap.xml",
            },
        }

        rss_xml = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item><link>https://example.com/article/1</link></item>
          <item><link>https://example.com/article/2</link></item>
          <item><link>https://example.com/article/3</link></item>
          <item><link>https://example.com/article/4</link></item>
          <item><link>https://example.com/article/5</link></item>
        </channel></rss>"""

        mock_guard.fetch.return_value = _make_fetch_response(rss_xml)

        discovery = URLDiscovery(mock_guard, min_urls_threshold=3)
        results = discovery.discover(site_config, "test_site", max_age_days=365)

        assert len(results) >= 3
        # Should only have called RSS (not sitemap or DOM)
        assert mock_guard.fetch.call_count == 1

    def test_fallback_to_sitemap(self, mock_guard):
        """Should fall back to sitemap if RSS yields too few URLs."""
        site_config = {
            "url": "https://example.com",
            "crawl": {
                "primary_method": "rss",
                "fallback_methods": ["sitemap"],
                "rss_url": "https://example.com/rss",
                "sitemap_url": "/sitemap.xml",
            },
        }

        empty_rss = """<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>"""

        sitemap_xml = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/article/1</loc></url>
          <url><loc>https://example.com/article/2</loc></url>
          <url><loc>https://example.com/article/3</loc></url>
          <url><loc>https://example.com/article/4</loc></url>
          <url><loc>https://example.com/article/5</loc></url>
          <url><loc>https://example.com/article/6</loc></url>
        </urlset>"""

        mock_guard.fetch.side_effect = [
            _make_fetch_response(empty_rss),
            _make_fetch_response(sitemap_xml),
        ]

        discovery = URLDiscovery(mock_guard, min_urls_threshold=3)
        results = discovery.discover(site_config, "test_site", max_age_days=365)

        # Should have tried both RSS and sitemap
        assert mock_guard.fetch.call_count == 2
        assert len(results) >= 3

    def test_deduplication_across_tiers(self, mock_guard):
        """URLs discovered in multiple tiers should be deduplicated."""
        site_config = {
            "url": "https://example.com",
            "crawl": {
                "primary_method": "rss",
                "fallback_methods": ["sitemap"],
                "rss_url": "https://example.com/rss",
                "sitemap_url": "/sitemap.xml",
            },
        }

        # RSS returns 1 article
        rss_xml = """<?xml version="1.0"?><rss version="2.0"><channel>
          <item><link>https://example.com/article/shared</link></item>
        </channel></rss>"""

        # Sitemap returns the same article plus one more
        sitemap_xml = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/article/shared</loc></url>
          <url><loc>https://example.com/article/unique</loc></url>
          <url><loc>https://example.com/article/unique2</loc></url>
          <url><loc>https://example.com/article/unique3</loc></url>
          <url><loc>https://example.com/article/unique4</loc></url>
          <url><loc>https://example.com/article/unique5</loc></url>
        </urlset>"""

        mock_guard.fetch.side_effect = [
            _make_fetch_response(rss_xml),
            _make_fetch_response(sitemap_xml),
        ]

        discovery = URLDiscovery(mock_guard, min_urls_threshold=5)
        results = discovery.discover(site_config, "test_site", max_age_days=365)

        urls = [r.url for r in results]
        assert len(urls) == len(set(urls))  # No duplicates
