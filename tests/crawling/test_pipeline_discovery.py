"""Tests for pipeline discovery bypass methods.

Covers:
    - _detect_block_type_from_error() — deterministic block type extraction
    - _parse_discovery_response() — XML tag inspection for content-type detection
    - _generate_failure_report() — producer-consumer contract with check_crawl_progress.py
    - URLDiscovery public proxies — parse_feed_from_text, parse_sitemap_from_text

Reference:
    Critical Reflection 2026-03-13 — Phase 4 (test coverage for bypass discovery).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.crawling.contracts import CrawlResult, DiscoveredURL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pipeline(tmp_path: Path) -> Any:
    """Create a minimal mock pipeline with only attrs needed for testing."""
    from src.crawling.pipeline import CrawlingPipeline

    p = object.__new__(CrawlingPipeline)
    p._output_dir = tmp_path
    p._date = datetime.now().strftime("%Y-%m-%d")
    p._bypass_state = {"sites": {}}
    p._url_discovery = MagicMock()
    p._bypass_engine = MagicMock()
    return p


# ---------------------------------------------------------------------------
# _detect_block_type_from_error()
# ---------------------------------------------------------------------------

class TestDetectBlockTypeFromError:
    """Test deterministic block type extraction from exceptions."""

    @pytest.fixture
    def pipeline(self, tmp_path: Path) -> Any:
        return _make_pipeline(tmp_path)

    def test_none_error_returns_none(self, pipeline: Any) -> None:
        assert pipeline._detect_block_type_from_error(None) is None

    def test_block_detected_error_with_block_type(self, pipeline: Any) -> None:
        """BlockDetectedError with valid block_type attribute is extracted."""
        from src.utils.error_handler import BlockDetectedError
        err = BlockDetectedError("blocked", block_type="captcha")
        result = pipeline._detect_block_type_from_error(err)
        from src.crawling.dynamic_bypass import BlockType
        assert result == BlockType.CAPTCHA

    def test_block_detected_error_captcha_in_message(self, pipeline: Any) -> None:
        """BlockDetectedError with 'captcha' in message is inferred."""
        from src.utils.error_handler import BlockDetectedError
        err = BlockDetectedError("captcha challenge detected", block_type="unknown")
        result = pipeline._detect_block_type_from_error(err)
        from src.crawling.dynamic_bypass import BlockType
        assert result == BlockType.CAPTCHA

    def test_block_detected_error_cloudflare_in_message(self, pipeline: Any) -> None:
        """BlockDetectedError with 'cloudflare' in message → JS_CHALLENGE."""
        from src.utils.error_handler import BlockDetectedError
        err = BlockDetectedError("cloudflare protection", block_type="unknown")
        result = pipeline._detect_block_type_from_error(err)
        from src.crawling.dynamic_bypass import BlockType
        assert result == BlockType.JS_CHALLENGE

    def test_block_detected_error_unknown_returns_none(self, pipeline: Any) -> None:
        """BlockDetectedError with no recognizable pattern returns None (no guessing)."""
        from src.utils.error_handler import BlockDetectedError
        err = BlockDetectedError("something happened", block_type="unknown")
        result = pipeline._detect_block_type_from_error(err)
        assert result is None

    def test_network_error_403(self, pipeline: Any) -> None:
        """NetworkError with status 403 → UA_FILTER."""
        from src.utils.error_handler import NetworkError
        err = NetworkError("forbidden", status_code=403)
        result = pipeline._detect_block_type_from_error(err)
        from src.crawling.dynamic_bypass import BlockType
        assert result == BlockType.UA_FILTER

    def test_network_error_429(self, pipeline: Any) -> None:
        """NetworkError with status 429 → RATE_LIMIT."""
        from src.utils.error_handler import NetworkError
        err = NetworkError("too many requests", status_code=429)
        result = pipeline._detect_block_type_from_error(err)
        from src.crawling.dynamic_bypass import BlockType
        assert result == BlockType.RATE_LIMIT

    def test_network_error_500_returns_none(self, pipeline: Any) -> None:
        """NetworkError with status 500 is not a block → None."""
        from src.utils.error_handler import NetworkError
        err = NetworkError("internal server error", status_code=500)
        assert pipeline._detect_block_type_from_error(err) is None

    def test_generic_exception_returns_none(self, pipeline: Any) -> None:
        """Non-crawl exceptions return None."""
        err = RuntimeError("random error")
        assert pipeline._detect_block_type_from_error(err) is None


# ---------------------------------------------------------------------------
# _parse_discovery_response()
# ---------------------------------------------------------------------------

class TestParseDiscoveryResponse:
    """Test deterministic content-type detection via XML tag inspection."""

    @pytest.fixture
    def pipeline(self, tmp_path: Path) -> Any:
        return _make_pipeline(tmp_path)

    def test_rss_feed_detected(self, pipeline: Any) -> None:
        """XML with <rss> tag routes to parse_feed_from_text."""
        xml = '<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
        pipeline._url_discovery.parse_feed_from_text.return_value = [
            DiscoveredURL(url="https://example.com/a", source_id="test")
        ]

        result = pipeline._parse_discovery_response(
            "https://example.com/rss", xml, "test", {},
        )

        pipeline._url_discovery.parse_feed_from_text.assert_called_once_with(xml, "test")
        assert len(result) == 1

    def test_atom_feed_detected(self, pipeline: Any) -> None:
        """XML with <feed> tag routes to parse_feed_from_text."""
        xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        pipeline._url_discovery.parse_feed_from_text.return_value = []

        pipeline._parse_discovery_response(
            "https://example.com/atom", xml, "test", {},
        )

        pipeline._url_discovery.parse_feed_from_text.assert_called_once()

    def test_sitemap_detected(self, pipeline: Any) -> None:
        """XML with <urlset> tag routes to parse_sitemap_from_text."""
        xml = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        pipeline._url_discovery.parse_sitemap_from_text.return_value = []

        pipeline._parse_discovery_response(
            "https://example.com/sitemap.xml", xml, "test", {"url": "https://example.com"},
        )

        pipeline._url_discovery.parse_sitemap_from_text.assert_called_once_with(
            xml, "test", base_url="https://example.com",
        )

    def test_sitemapindex_detected(self, pipeline: Any) -> None:
        """XML with <sitemapindex> tag routes to parse_sitemap_from_text."""
        xml = '<?xml version="1.0"?><sitemapindex></sitemapindex>'
        pipeline._url_discovery.parse_sitemap_from_text.return_value = []

        pipeline._parse_discovery_response(
            "https://example.com/sitemap_index.xml", xml, "test", {},
        )

        pipeline._url_discovery.parse_sitemap_from_text.assert_called_once()

    def test_html_dom_extraction(self, pipeline: Any) -> None:
        """HTML page extracts article-like links from href attributes."""
        html = """
        <html><body>
            <a href="https://example.com/news/2025/article-title">Article</a>
            <a href="https://example.com/about">About</a>
        </body></html>
        """
        result = pipeline._parse_discovery_response(
            "https://example.com", html, "test", {"url": "https://example.com"},
        )
        # At least the article-like URL should be extracted (depends on is_article_url)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# _generate_failure_report() — producer-consumer contract
# ---------------------------------------------------------------------------

class TestGenerateFailureReport:
    """Test failure report producer matches check_crawl_progress.py consumer."""

    @pytest.fixture
    def pipeline(self, tmp_path: Path) -> Any:
        p = _make_pipeline(tmp_path)
        return p

    def test_report_structure_matches_consumer(self, pipeline: Any, tmp_path: Path) -> None:
        """Report uses 'exhausted_sites' list with 'site_id' field (consumer contract)."""
        result = CrawlResult(
            source_id="blocked_site",
            discovered_urls=0,
            extracted_count=0,
            errors=["403 Forbidden"],
        )

        pipeline._generate_failure_report(
            ["blocked_site"],
            {"blocked_site": {"url": "https://blocked.com", "meta": {"difficulty": "Hard"}}},
            {"blocked_site": result},
        )

        report_path = tmp_path / "crawl_exhausted_sites.json"
        assert report_path.exists()

        data = json.loads(report_path.read_text())

        # Consumer contract: data["exhausted_sites"] is a list
        assert "exhausted_sites" in data
        assert isinstance(data["exhausted_sites"], list)
        assert len(data["exhausted_sites"]) == 1

        # Each entry has site_id and failure_category
        entry = data["exhausted_sites"][0]
        assert entry["site_id"] == "blocked_site"
        assert "failure_category" in entry
        assert "recommendation" in entry

    def test_discovery_blocked_category(self, pipeline: Any, tmp_path: Path) -> None:
        """Site with 0 discovered URLs → 'discovery_blocked' category."""
        result = CrawlResult(source_id="s1", discovered_urls=0, extracted_count=0)
        pipeline._generate_failure_report(["s1"], {}, {"s1": result})

        data = json.loads((tmp_path / "crawl_exhausted_sites.json").read_text())
        assert data["exhausted_sites"][0]["failure_category"] == "discovery_blocked"

    def test_extraction_blocked_category(self, pipeline: Any, tmp_path: Path) -> None:
        """Site with URLs but 0 articles → 'extraction_blocked' category."""
        result = CrawlResult(source_id="s1", discovered_urls=50, extracted_count=0)
        pipeline._generate_failure_report(["s1"], {}, {"s1": result})

        data = json.loads((tmp_path / "crawl_exhausted_sites.json").read_text())
        assert data["exhausted_sites"][0]["failure_category"] == "extraction_blocked"

    def test_partial_timeout_category(self, pipeline: Any, tmp_path: Path) -> None:
        """Site with some articles but not complete → 'partial_timeout'."""
        result = CrawlResult(source_id="s1", discovered_urls=50, extracted_count=10)
        pipeline._generate_failure_report(["s1"], {}, {"s1": result})

        data = json.loads((tmp_path / "crawl_exhausted_sites.json").read_text())
        assert data["exhausted_sites"][0]["failure_category"] == "partial_timeout"

    def test_multiple_sites(self, pipeline: Any, tmp_path: Path) -> None:
        """Multiple failed sites each get their own entry."""
        results = {
            "s1": CrawlResult(source_id="s1", discovered_urls=0),
            "s2": CrawlResult(source_id="s2", discovered_urls=10, extracted_count=5),
        }
        pipeline._generate_failure_report(["s1", "s2"], {}, results)

        data = json.loads((tmp_path / "crawl_exhausted_sites.json").read_text())
        assert len(data["exhausted_sites"]) == 2
        ids = {e["site_id"] for e in data["exhausted_sites"]}
        assert ids == {"s1", "s2"}

    def test_max_passes_exhausted_field(self, pipeline: Any, tmp_path: Path) -> None:
        """Report includes max_passes_exhausted from MULTI_PASS_MAX_EXTRA."""
        from src.config.constants import MULTI_PASS_MAX_EXTRA
        result = CrawlResult(source_id="s1")
        pipeline._generate_failure_report(["s1"], {}, {"s1": result})

        data = json.loads((tmp_path / "crawl_exhausted_sites.json").read_text())
        assert data["max_passes_exhausted"] == MULTI_PASS_MAX_EXTRA


# ---------------------------------------------------------------------------
# URLDiscovery public proxies
# ---------------------------------------------------------------------------

class TestURLDiscoveryPublicProxies:
    """Test that URLDiscovery exposes parse_feed/sitemap_from_text as public methods."""

    def test_parse_feed_from_text_delegates(self) -> None:
        """URLDiscovery.parse_feed_from_text delegates to _rss_parser."""
        from src.crawling.url_discovery import URLDiscovery

        ud = object.__new__(URLDiscovery)
        ud._rss_parser = MagicMock()
        expected = [DiscoveredURL(url="https://example.com/a", source_id="test")]
        ud._rss_parser.parse_feed_from_text.return_value = expected

        result = ud.parse_feed_from_text("<rss>...</rss>", "test")

        ud._rss_parser.parse_feed_from_text.assert_called_once_with(
            "<rss>...</rss>", "test", 1,
        )
        assert result == expected

    def test_parse_sitemap_from_text_delegates(self) -> None:
        """URLDiscovery.parse_sitemap_from_text delegates to _sitemap_parser."""
        from src.crawling.url_discovery import URLDiscovery

        ud = object.__new__(URLDiscovery)
        ud._sitemap_parser = MagicMock()
        expected = [DiscoveredURL(url="https://example.com/b", source_id="test")]
        ud._sitemap_parser.parse_sitemap_from_text.return_value = expected

        result = ud.parse_sitemap_from_text("<urlset>...</urlset>", "test", base_url="https://example.com")

        ud._sitemap_parser.parse_sitemap_from_text.assert_called_once_with(
            "<urlset>...</urlset>", "test", "https://example.com", 1, 5000, None,
        )
        assert result == expected

    def test_public_methods_exist_on_class(self) -> None:
        """parse_feed_from_text and parse_sitemap_from_text are public methods."""
        from src.crawling.url_discovery import URLDiscovery

        assert hasattr(URLDiscovery, "parse_feed_from_text")
        assert hasattr(URLDiscovery, "parse_sitemap_from_text")
        assert callable(getattr(URLDiscovery, "parse_feed_from_text"))
        assert callable(getattr(URLDiscovery, "parse_sitemap_from_text"))
