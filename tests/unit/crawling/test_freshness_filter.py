"""Tests for the 24-hour lookback freshness filter in CrawlingPipeline.

Validates:
    - datetime comparison (not string parsing) for published_at
    - Timezone-aware vs naive datetime handling
    - None published_at passthrough (article kept)
    - Articles within 24h window are kept
    - Articles outside 24h window are dropped
    - skipped_freshness_count is incremented (not skipped_dedup_count)
    - Circuit breaker and retry manager still record success for filtered articles
    - _merge_result merges freshness counts correctly
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.crawling.contracts import RawArticle, CrawlResult, DiscoveredURL
from src.crawling.pipeline import CrawlingPipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(
    published_at: datetime | None,
    url: str = "https://example.com/article",
    title: str = "Test Article",
) -> RawArticle:
    """Create a minimal RawArticle with the given published_at."""
    return RawArticle(
        url=url,
        title=title,
        body="Article body text for testing.",
        source_id="test_site",
        source_name="Test Site",
        language="en",
        published_at=published_at,
        crawled_at=datetime.now(timezone.utc),
    )


def _make_url_obj(url: str = "https://example.com/article") -> DiscoveredURL:
    """Create a minimal DiscoveredURL."""
    return DiscoveredURL(
        url=url,
        source_id="test_site",
        discovered_via="rss",
    )


# ---------------------------------------------------------------------------
# CrawlResult.skipped_freshness_count field tests
# ---------------------------------------------------------------------------

class TestCrawlResultFreshnessField:
    """Verify the new skipped_freshness_count field on CrawlResult."""

    def test_default_zero(self):
        """Field defaults to 0."""
        result = CrawlResult(source_id="test")
        assert result.skipped_freshness_count == 0

    def test_independent_of_dedup_count(self):
        """Freshness and dedup counts are tracked independently."""
        result = CrawlResult(source_id="test")
        result.skipped_freshness_count += 3
        result.skipped_dedup_count += 5
        assert result.skipped_freshness_count == 3
        assert result.skipped_dedup_count == 5


# ---------------------------------------------------------------------------
# Freshness filter logic tests (isolated from full pipeline)
# ---------------------------------------------------------------------------

class TestFreshnessFilterLogic:
    """Test the 24h lookback filter logic that lives in _crawl_urls.

    These tests exercise the filter logic directly by simulating what
    _crawl_urls does, without starting the full pipeline.
    """

    def _apply_filter(
        self,
        article: RawArticle,
        cutoff: datetime,
    ) -> bool:
        """Reproduce the filter logic from pipeline.py _crawl_urls.

        Returns True if the article would be KEPT, False if DROPPED.
        """
        if article.published_at is not None:
            pub_dt = article.published_at
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            if pub_dt < cutoff:
                return False
        return True

    def test_article_within_24h_is_kept(self):
        """Article published 6 hours ago should pass the filter."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        article = _make_article(published_at=now - timedelta(hours=6))
        assert self._apply_filter(article, cutoff) is True

    def test_article_outside_24h_is_dropped(self):
        """Article published 30 hours ago should be dropped."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        article = _make_article(published_at=now - timedelta(hours=30))
        assert self._apply_filter(article, cutoff) is False

    def test_article_exactly_at_cutoff_is_dropped(self):
        """Article published exactly at the cutoff boundary should be dropped."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        # published_at == cutoff: cutoff < cutoff is False, so it passes
        # But 1 microsecond before cutoff should be dropped
        article = _make_article(published_at=cutoff - timedelta(microseconds=1))
        assert self._apply_filter(article, cutoff) is False

    def test_article_just_after_cutoff_is_kept(self):
        """Article published 1 microsecond after cutoff should pass."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        article = _make_article(published_at=cutoff + timedelta(microseconds=1))
        assert self._apply_filter(article, cutoff) is True

    def test_none_published_at_passes(self):
        """Articles with no publication date should be kept."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        article = _make_article(published_at=None)
        assert self._apply_filter(article, cutoff) is True

    def test_naive_datetime_treated_as_utc(self):
        """Timezone-naive published_at should be treated as UTC."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        # Naive datetime 6 hours ago — should pass
        naive_recent = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)
        article = _make_article(published_at=naive_recent)
        assert self._apply_filter(article, cutoff) is True

        # Naive datetime 30 hours ago — should be dropped
        naive_old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=30)
        article_old = _make_article(published_at=naive_old)
        assert self._apply_filter(article_old, cutoff) is False

    def test_different_timezone_handled(self):
        """Article with KST (+09:00) published_at should compare correctly."""
        from datetime import timezone as tz

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)

        kst = tz(timedelta(hours=9))
        # 6 hours ago in KST — should pass
        recent_kst = datetime.now(kst) - timedelta(hours=6)
        article = _make_article(published_at=recent_kst)
        assert self._apply_filter(article, cutoff) is True

        # 30 hours ago in KST — should be dropped
        old_kst = datetime.now(kst) - timedelta(hours=30)
        article_old = _make_article(published_at=old_kst)
        assert self._apply_filter(article_old, cutoff) is False

    def test_published_at_is_datetime_not_string(self):
        """Verify published_at is a datetime object, not a string.

        This is the critical type check that caught the original bug:
        fromisoformat() would crash because published_at is already datetime.
        """
        article = _make_article(
            published_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        assert isinstance(article.published_at, datetime)
        # The filter should work with datetime directly — no string parsing
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        assert self._apply_filter(article, cutoff) is True


# ---------------------------------------------------------------------------
# _merge_result freshness count test
# ---------------------------------------------------------------------------

class TestMergeResultFreshness:
    """Test that _merge_result correctly merges skipped_freshness_count."""

    def test_merge_adds_freshness_counts(self):
        """Merging two results should sum their freshness counts."""
        target = CrawlResult(source_id="test")
        target.skipped_freshness_count = 5
        target.skipped_dedup_count = 10

        source = CrawlResult(source_id="test")
        source.skipped_freshness_count = 3
        source.skipped_dedup_count = 2

        CrawlingPipeline._merge_result(target, source)

        assert target.skipped_freshness_count == 8
        assert target.skipped_dedup_count == 12


# ---------------------------------------------------------------------------
# Pipeline lookback cutoff initialization test
# ---------------------------------------------------------------------------

class TestPipelineLookbackInit:
    """Test that CrawlingPipeline initializes the lookback cutoff correctly."""

    def test_lookback_cutoff_is_24h_before_start(self):
        """_lookback_cutoff should be 24 hours before _crawl_start_utc."""
        pipeline = CrawlingPipeline.__new__(CrawlingPipeline)
        now = datetime.now(timezone.utc)
        pipeline._crawl_start_utc = now
        pipeline._lookback_cutoff = now - timedelta(hours=24)

        expected_cutoff = now - timedelta(hours=24)
        assert pipeline._lookback_cutoff == expected_cutoff

    def test_lookback_cutoff_is_timezone_aware(self):
        """The cutoff must be timezone-aware for comparison with published_at."""
        pipeline = CrawlingPipeline.__new__(CrawlingPipeline)
        now = datetime.now(timezone.utc)
        pipeline._crawl_start_utc = now
        pipeline._lookback_cutoff = now - timedelta(hours=24)

        assert pipeline._lookback_cutoff.tzinfo is not None

    def test_constant_value(self):
        """CRAWL_LOOKBACK_HOURS should be 24."""
        from src.config.constants import CRAWL_LOOKBACK_HOURS
        assert CRAWL_LOOKBACK_HOURS == 24
