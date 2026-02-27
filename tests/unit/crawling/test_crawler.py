"""Tests for Crawler orchestrator: pipeline, JSONL writer, crawl state.

Tests cover:
    - JSONLWriter atomic file operations
    - CrawlState persistence and resume support
    - Crawler per-site pipeline orchestration
    - Error handling (never crash on single site failure)
    - Integration with NetworkGuard, URLDiscovery, ArticleExtractor
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.crawling.crawler import (
    Crawler,
    JSONLWriter,
    CrawlState,
)
from src.crawling.contracts import RawArticle, CrawlResult, DiscoveredURL
from src.crawling.network_guard import NetworkGuard
from src.utils.error_handler import NetworkError, ParseError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "data" / "raw" / "2025-01-20"
    output_dir.mkdir(parents=True)
    return output_dir


@pytest.fixture
def sample_article():
    """Create a sample RawArticle."""
    return RawArticle(
        url="https://example.com/article/1",
        title="Test Article",
        body="This is a test article body with enough content.",
        source_id="test_site",
        source_name="Test Site",
        language="en",
        published_at=datetime(2025, 1, 20, 10, 0, 0, tzinfo=timezone.utc),
        crawled_at=datetime.now(timezone.utc),
        author="Test Author",
        category="news",
        content_hash="abc123",
        crawl_tier=1,
        crawl_method="rss",
        is_paywall_truncated=False,
    )


@pytest.fixture
def sample_site_config():
    """Sample site configuration."""
    return {
        "name": "Test Site",
        "url": "https://example.com",
        "language": "en",
        "group": "E",
        "crawl": {
            "primary_method": "rss",
            "fallback_methods": ["sitemap"],
            "rss_url": "https://example.com/rss",
            "sitemap_url": "/sitemap.xml",
            "rate_limit_seconds": 1,
            "jitter_seconds": 0,
        },
        "anti_block": {
            "ua_tier": 1,
            "bot_block_level": "LOW",
        },
        "extraction": {
            "paywall_type": "none",
            "title_only": False,
            "charset": "utf-8",
        },
        "meta": {
            "enabled": True,
            "difficulty_tier": "Easy",
            "daily_article_estimate": 100,
        },
    }


# ===========================================================================
# JSONLWriter Tests
# ===========================================================================

class TestJSONLWriter:
    """Tests for atomic JSONL file writing."""

    def test_write_single_article(self, tmp_output_dir, sample_article):
        """Should write a single article as one JSONL line."""
        output_path = tmp_output_dir / "test_site.jsonl"

        with JSONLWriter(output_path) as writer:
            writer.write_article(sample_article)

        assert output_path.exists()
        with open(output_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["title"] == "Test Article"
        assert data["url"] == "https://example.com/article/1"

    def test_write_multiple_articles(self, tmp_output_dir, sample_article):
        """Should write multiple articles as separate JSONL lines."""
        output_path = tmp_output_dir / "test_site.jsonl"

        with JSONLWriter(output_path) as writer:
            for i in range(5):
                writer.write_article(sample_article)

        with open(output_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 5

    def test_empty_writer_no_file(self, tmp_output_dir):
        """Zero articles should not create an output file."""
        output_path = tmp_output_dir / "empty.jsonl"

        with JSONLWriter(output_path) as writer:
            pass  # Write nothing

        assert not output_path.exists()

    def test_atomic_write_no_partial(self, tmp_output_dir, sample_article):
        """File should not be visible until writer is closed (atomic)."""
        output_path = tmp_output_dir / "atomic.jsonl"

        writer = JSONLWriter(output_path)
        writer.open()
        writer.write_article(sample_article)

        # Before close, the final file should NOT exist
        assert not output_path.exists()

        writer.close()

        # After close, the file should exist
        assert output_path.exists()

    def test_creates_parent_directories(self, tmp_path, sample_article):
        """Should create parent directories if they don't exist."""
        deep_path = tmp_path / "a" / "b" / "c" / "output.jsonl"

        with JSONLWriter(deep_path) as writer:
            writer.write_article(sample_article)

        assert deep_path.exists()

    def test_count_property(self, tmp_output_dir, sample_article):
        """count property should track written articles."""
        output_path = tmp_output_dir / "count.jsonl"

        with JSONLWriter(output_path) as writer:
            assert writer.count == 0
            writer.write_article(sample_article)
            assert writer.count == 1
            writer.write_article(sample_article)
            assert writer.count == 2

    def test_write_without_open_raises(self, tmp_output_dir, sample_article):
        """Writing without opening should raise RuntimeError."""
        output_path = tmp_output_dir / "noopen.jsonl"
        writer = JSONLWriter(output_path)

        with pytest.raises(RuntimeError, match="not opened"):
            writer.write_article(sample_article)


# ===========================================================================
# CrawlState Tests
# ===========================================================================

class TestCrawlState:
    """Tests for crawl state persistence."""

    def test_mark_and_check_url(self, tmp_output_dir):
        """Should mark URLs as processed and check them."""
        state = CrawlState(tmp_output_dir)

        assert state.is_url_processed("site_a", "https://example.com/1") is False

        state.mark_url_processed("site_a", "https://example.com/1")
        assert state.is_url_processed("site_a", "https://example.com/1") is True

        # Different site should not be affected
        assert state.is_url_processed("site_b", "https://example.com/1") is False

    def test_save_and_reload(self, tmp_output_dir):
        """State should persist across save/reload cycles."""
        state1 = CrawlState(tmp_output_dir)
        state1.mark_url_processed("site_a", "https://example.com/1")
        state1.save()

        # Create a new CrawlState that loads from disk
        state2 = CrawlState(tmp_output_dir)
        assert state2.is_url_processed("site_a", "https://example.com/1") is True

    def test_mark_site_complete(self, tmp_output_dir):
        """Should mark sites as complete."""
        state = CrawlState(tmp_output_dir)

        assert state.is_site_complete("site_a") is False
        state.mark_site_complete("site_a")
        assert state.is_site_complete("site_a") is True

    def test_get_processed_count(self, tmp_output_dir):
        """Should track the count of processed URLs per site."""
        state = CrawlState(tmp_output_dir)

        assert state.get_processed_count("site_a") == 0

        state.mark_url_processed("site_a", "url1")
        state.mark_url_processed("site_a", "url2")
        assert state.get_processed_count("site_a") == 2

    def test_corrupted_state_file(self, tmp_output_dir):
        """Corrupted state file should not crash -- start fresh."""
        state_path = tmp_output_dir / ".crawl_state.json"
        state_path.write_text("THIS IS NOT JSON")

        state = CrawlState(tmp_output_dir)
        # Should have loaded with empty state
        assert state.is_url_processed("site_a", "url1") is False


# ===========================================================================
# RawArticle Serialization Tests
# ===========================================================================

class TestRawArticleSerialization:
    """Tests for RawArticle JSONL serialization/deserialization."""

    def test_round_trip(self, sample_article):
        """Serialization -> deserialization should preserve all fields."""
        json_str = sample_article.to_jsonl_line()
        data = json.loads(json_str)
        restored = RawArticle.from_jsonl_dict(data)

        assert restored.url == sample_article.url
        assert restored.title == sample_article.title
        assert restored.body == sample_article.body
        assert restored.source_id == sample_article.source_id
        assert restored.language == sample_article.language
        assert restored.crawl_method == sample_article.crawl_method

    def test_none_fields_serialized(self):
        """None optional fields should serialize as null."""
        article = RawArticle(
            url="https://example.com",
            title="Test",
            body="Body",
            source_id="test",
            source_name="Test",
            language="en",
            published_at=None,
            crawled_at=datetime.now(timezone.utc),
        )

        data = article.to_jsonl_dict()
        assert data["published_at"] is None
        assert data["author"] is None


# ===========================================================================
# Crawler Integration Tests
# ===========================================================================

class TestCrawler:
    """Tests for the Crawler orchestrator."""

    def test_disabled_site_skipped(self, tmp_path):
        """Disabled sites should be skipped entirely."""
        guard = MagicMock(spec=NetworkGuard)
        crawler = Crawler(
            network_guard=guard,
            crawl_date="2025-01-20",
            output_dir=tmp_path / "raw",
        )

        config = {
            "name": "Disabled",
            "meta": {"enabled": False},
            "crawl": {"rate_limit_seconds": 1},
        }

        result = crawler.crawl_site("disabled_site", config)

        assert result.source_id == "disabled_site"
        assert result.extracted_count == 0
        guard.configure_site.assert_not_called()

    def test_crawl_never_crashes_on_site_error(self, tmp_path):
        """crawl_sites should never crash -- errors are caught per-site."""
        guard = MagicMock(spec=NetworkGuard)
        crawler = Crawler(
            network_guard=guard,
            crawl_date="2025-01-20",
            output_dir=tmp_path / "raw",
        )

        # Mock URLDiscovery to raise an exception
        with patch.object(crawler._url_discovery, "discover", side_effect=Exception("Boom")):
            config = {
                "name": "Error Site",
                "meta": {"enabled": True},
                "crawl": {"rate_limit_seconds": 1, "jitter_seconds": 0},
                "extraction": {"paywall_type": "none"},
            }

            result = crawler.crawl_site("error_site", config)

            assert result.source_id == "error_site"
            assert len(result.errors) > 0

    def test_crawl_multiple_sites(self, tmp_path):
        """crawl_sites should process multiple sites and return results."""
        guard = MagicMock(spec=NetworkGuard)
        crawler = Crawler(
            network_guard=guard,
            crawl_date="2025-01-20",
            output_dir=tmp_path / "raw",
        )

        # Mock discovery to return empty
        with patch.object(crawler._url_discovery, "discover", return_value=[]):
            sites = {
                "site_a": {"name": "A", "meta": {"enabled": True},
                           "crawl": {"rate_limit_seconds": 1, "jitter_seconds": 0}},
                "site_b": {"name": "B", "meta": {"enabled": True},
                           "crawl": {"rate_limit_seconds": 1, "jitter_seconds": 0}},
            }

            results = crawler.crawl_sites(sites)

            assert len(results) == 2
            assert all(isinstance(r, CrawlResult) for r in results)

    def test_resume_skips_processed_urls(self, tmp_path):
        """Already-processed URLs should be skipped on resume."""
        guard = MagicMock(spec=NetworkGuard)
        output_dir = tmp_path / "raw"
        date_dir = output_dir / "2025-01-20"
        date_dir.mkdir(parents=True)

        # Pre-populate crawl state with one URL
        state_path = date_dir / ".crawl_state.json"
        state_path.write_text(json.dumps({
            "test_site": {
                "processed_urls": ["https://example.com/article/1"],
                "complete": False,
            }
        }))

        crawler = Crawler(
            network_guard=guard,
            crawl_date="2025-01-20",
            output_dir=output_dir,
        )

        urls = [
            DiscoveredURL(url="https://example.com/article/1", source_id="test_site"),
            DiscoveredURL(url="https://example.com/article/2", source_id="test_site"),
        ]

        # Mock discovery
        with patch.object(crawler._url_discovery, "discover", return_value=urls):
            # Mock extractor to track calls
            with patch.object(crawler._extractor, "extract") as mock_extract:
                mock_extract.return_value = RawArticle(
                    url="https://example.com/article/2",
                    title="Article 2",
                    body="Body" * 50,
                    source_id="test_site",
                    source_name="Test",
                    language="en",
                    published_at=None,
                    crawled_at=datetime.now(timezone.utc),
                )

                config = {
                    "name": "Test",
                    "meta": {"enabled": True},
                    "crawl": {"rate_limit_seconds": 0.1, "jitter_seconds": 0},
                    "extraction": {"paywall_type": "none"},
                }

                result = crawler.crawl_site("test_site", config)

                # Only article/2 should have been extracted (article/1 was already processed)
                assert result.skipped_dedup_count >= 1

    def test_context_manager(self, tmp_path):
        """Crawler should work as context manager."""
        guard = MagicMock(spec=NetworkGuard)

        with Crawler(network_guard=guard, output_dir=tmp_path / "raw") as crawler:
            assert crawler is not None

        guard.close.assert_called_once()
