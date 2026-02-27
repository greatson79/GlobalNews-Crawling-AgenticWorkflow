"""Tests for multilingual date parsing across all supported languages.

Validates:
    - Chinese date formats (2026年02月26日, relative times).
    - Japanese date formats (2026年2月26日 14時30分, day-of-week, relative).
    - German date formats (15. Februar 2026, 15.02.2026).
    - French date formats (15 janvier 2026).
    - Chinese author extraction (记者 patterns).
    - Japanese author extraction (記者 patterns).
    - Timezone-aware UTC conversion preserves calendar date.
    - Date-only values use noon default to prevent day-shift.
    - BaseSiteAdapter.normalize_date handles ISO 8601 and RFC 2822.

Reference:
    Step 6 crawl-strategy-asia.md (CJK date formats).
    Step 6 crawl-strategy-global.md (European date formats).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from src.crawling.adapters.multilingual._ml_utils import (
    parse_chinese_date,
    parse_japanese_date,
    parse_german_date,
    parse_french_date,
    extract_chinese_author,
    extract_japanese_author,
    TZ_CST,
    TZ_JST,
    TZ_CET,
)


# ---------------------------------------------------------------------------
# Chinese date parsing
# ---------------------------------------------------------------------------


class TestChineseDateParsing:
    """Test Chinese date formats from People's Daily and Xinhua-style sites."""

    def test_full_datetime(self):
        result = parse_chinese_date("2026\u5e7402\u670826\u65e512:25")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 26

    def test_full_datetime_spaces(self):
        result = parse_chinese_date("2026\u5e74 2\u6708 26\u65e5 12:25")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 26

    def test_datetime_chinese_colon(self):
        """Chinese full-width colon in time."""
        result = parse_chinese_date("2026\u5e7402\u670826\u65e512\uff1a25")
        assert result is not None
        assert result.year == 2026

    def test_date_only(self):
        result = parse_chinese_date("2026\u5e7402\u670826\u65e5")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 26  # noon default preserves calendar date

    def test_date_only_preserves_day(self):
        """Date-only should use noon to prevent UTC day-shift."""
        result = parse_chinese_date("2026\u5e7402\u670826\u65e5")
        assert result is not None
        # Result is UTC; original is CST noon (12:00) = UTC 04:00
        # Day should be 26, not 25
        assert result.day == 26

    def test_relative_hours(self):
        result = parse_chinese_date("3\u5c0f\u65f6\u524d")
        assert result is not None
        now = datetime.now(timezone.utc)
        delta = abs((now - result).total_seconds())
        assert 3 * 3600 - 60 < delta < 3 * 3600 + 60

    def test_relative_minutes(self):
        result = parse_chinese_date("5\u5206\u949f\u524d")
        assert result is not None
        now = datetime.now(timezone.utc)
        delta = abs((now - result).total_seconds())
        assert 5 * 60 - 30 < delta < 5 * 60 + 30

    def test_relative_days(self):
        result = parse_chinese_date("2\u5929\u524d")
        assert result is not None
        now = datetime.now(timezone.utc)
        delta = abs((now - result).total_seconds())
        assert 2 * 86400 - 60 < delta < 2 * 86400 + 60

    def test_relative_seconds(self):
        result = parse_chinese_date("30\u79d2\u524d")
        assert result is not None
        now = datetime.now(timezone.utc)
        delta = abs((now - result).total_seconds())
        assert delta < 60

    def test_empty_returns_none(self):
        assert parse_chinese_date("") is None

    def test_garbage_returns_none(self):
        assert parse_chinese_date("no date here") is None

    def test_timezone_utc_output(self):
        """All returned datetimes must be UTC."""
        result = parse_chinese_date("2026\u5e7402\u670826\u65e512:25")
        assert result is not None
        assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# Japanese date parsing
# ---------------------------------------------------------------------------


class TestJapaneseDateParsing:
    """Test Japanese date formats from Yomiuri-style sites."""

    def test_full_datetime(self):
        result = parse_japanese_date("2026\u5e742\u670826\u65e5 14\u664230\u5206")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 26

    def test_full_datetime_with_dow(self):
        """Day of week in parentheses: (水) for Wednesday."""
        result = parse_japanese_date("2026\u5e742\u670826\u65e5(\u6c34) 14\u664230\u5206")
        assert result is not None
        assert result.year == 2026

    def test_date_only(self):
        result = parse_japanese_date("2026\u5e742\u670826\u65e5")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 26  # noon default preserves calendar date

    def test_date_only_preserves_day(self):
        """Date-only should use noon to prevent UTC day-shift."""
        result = parse_japanese_date("2026\u5e742\u670826\u65e5")
        assert result is not None
        assert result.day == 26

    def test_relative_hours(self):
        result = parse_japanese_date("3\u6642\u9593\u524d")
        assert result is not None
        now = datetime.now(timezone.utc)
        delta = abs((now - result).total_seconds())
        assert 3 * 3600 - 60 < delta < 3 * 3600 + 60

    def test_relative_minutes(self):
        result = parse_japanese_date("5\u5206\u524d")
        assert result is not None

    def test_relative_days(self):
        result = parse_japanese_date("2\u65e5\u524d")
        assert result is not None

    def test_empty_returns_none(self):
        assert parse_japanese_date("") is None

    def test_timezone_utc_output(self):
        result = parse_japanese_date("2026\u5e742\u670826\u65e5 14\u664230\u5206")
        assert result is not None
        assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# German date parsing
# ---------------------------------------------------------------------------


class TestGermanDateParsing:
    """Test German date formats from Bild/Spiegel-style sites."""

    def test_long_format_date_only(self):
        result = parse_german_date("15. Februar 2026")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 15

    def test_long_format_with_time(self):
        result = parse_german_date("15. Februar 2026, 14:30 Uhr")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 15

    def test_short_format_date_only(self):
        result = parse_german_date("15.02.2026")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 15

    def test_short_format_with_time(self):
        result = parse_german_date("15.02.2026, 14:30")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 15

    def test_umlaut_month_maerz(self):
        result = parse_german_date("3. M\u00e4rz 2026")
        assert result is not None
        assert result.month == 3

    def test_all_german_months(self):
        months = [
            ("Januar", 1), ("Februar", 2), ("M\u00e4rz", 3), ("April", 4),
            ("Mai", 5), ("Juni", 6), ("Juli", 7), ("August", 8),
            ("September", 9), ("Oktober", 10), ("November", 11), ("Dezember", 12),
        ]
        for name, num in months:
            result = parse_german_date(f"1. {name} 2026")
            assert result is not None, f"Failed for {name}"
            assert result.month == num, f"Wrong month for {name}: got {result.month}"

    def test_date_only_preserves_day(self):
        """Date-only should use noon to prevent UTC day-shift."""
        result = parse_german_date("15. Februar 2026")
        assert result is not None
        assert result.day == 15

    def test_empty_returns_none(self):
        assert parse_german_date("") is None

    def test_timezone_utc_output(self):
        result = parse_german_date("15. Februar 2026, 14:30 Uhr")
        assert result is not None
        assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# French date parsing
# ---------------------------------------------------------------------------


class TestFrenchDateParsing:
    """Test French date formats from Le Monde-style sites."""

    def test_date_only(self):
        result = parse_french_date("15 janvier 2026")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_accent_month_fevrier(self):
        result = parse_french_date("15 f\u00e9vrier 2026")
        assert result is not None
        assert result.month == 2

    def test_accent_month_decembre(self):
        result = parse_french_date("15 d\u00e9cembre 2026")
        assert result is not None
        assert result.month == 12

    def test_all_french_months(self):
        months = [
            ("janvier", 1), ("f\u00e9vrier", 2), ("mars", 3), ("avril", 4),
            ("mai", 5), ("juin", 6), ("juillet", 7), ("ao\u00fbt", 8),
            ("septembre", 9), ("octobre", 10), ("novembre", 11), ("d\u00e9cembre", 12),
        ]
        for name, num in months:
            result = parse_french_date(f"15 {name} 2026")
            assert result is not None, f"Failed for {name}"
            assert result.month == num, f"Wrong month for {name}: got {result.month}"

    def test_date_only_preserves_day(self):
        result = parse_french_date("15 janvier 2026")
        assert result is not None
        assert result.day == 15

    def test_empty_returns_none(self):
        assert parse_french_date("") is None

    def test_timezone_utc_output(self):
        result = parse_french_date("15 janvier 2026")
        assert result is not None
        assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# Chinese author extraction
# ---------------------------------------------------------------------------


class TestChineseAuthorExtraction:
    """Test Chinese byline/author extraction patterns."""

    def test_reporter_2_char(self):
        assert extract_chinese_author("\u8bb0\u8005\u738b\u660e\u62a5\u9053") == "\u738b\u660e"

    def test_reporter_3_char(self):
        assert extract_chinese_author("\u8bb0\u8005\u674e\u660e\u534e\u62a5\u9053") == "\u674e\u660e\u534e"

    def test_reporter_at_end(self):
        assert extract_chinese_author("\u8bb0\u8005\u738b\u4e94") == "\u738b\u4e94"

    def test_reporter_with_space(self):
        assert extract_chinese_author("\u8bb0\u8005 \u738b\u660e") == "\u738b\u660e"

    def test_editor_pattern(self):
        assert extract_chinese_author("\u7f16\u8f91\uff1a\u674e\u7ea2") == "\u674e\u7ea2"

    def test_editor_half_width_colon(self):
        assert extract_chinese_author("\u7f16\u8f91:\u674e\u7ea2") == "\u674e\u7ea2"

    def test_embedded_reporter(self):
        """Reporter pattern embedded in longer text."""
        text = "\u672c\u62a5\u8bb0\u8005\u5f20\u4e09\u53d1\u81ea\u5317\u4eac"
        result = extract_chinese_author(text)
        assert result == "\u5f20\u4e09"

    def test_no_author_returns_none(self):
        assert extract_chinese_author("no Chinese byline here") is None


# ---------------------------------------------------------------------------
# Japanese author extraction
# ---------------------------------------------------------------------------


class TestJapaneseAuthorExtraction:
    """Test Japanese byline/author extraction patterns."""

    def test_reporter_prefix(self):
        result = extract_japanese_author("\u8a18\u8005 \u5c71\u7530\u592a\u90ce")
        assert result is not None
        assert "\u5c71\u7530" in result

    def test_reporter_suffix(self):
        result = extract_japanese_author("\u5c71\u7530\u592a\u90ce \u8a18\u8005")
        assert result is not None
        assert "\u5c71\u7530" in result

    def test_no_author_returns_none(self):
        assert extract_japanese_author("no Japanese byline here") is None


# ---------------------------------------------------------------------------
# BaseSiteAdapter.normalize_date (ISO 8601 and RFC 2822)
# ---------------------------------------------------------------------------


class TestNormalizeDateBase:
    """Test the base adapter's normalize_date for standard formats.

    These are used by most adapters as the primary date parsing path
    (Schema.org datePublished, meta tags).
    """

    @pytest.fixture
    def adapter(self):
        """Create a concrete adapter instance for testing normalize_date."""
        from src.crawling.adapters.multilingual import MULTILINGUAL_ADAPTERS
        return MULTILINGUAL_ADAPTERS["globaltimes"]()

    def test_iso8601_with_timezone(self, adapter):
        result = adapter.normalize_date("2026-02-26T10:00:00+08:00")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.tzinfo == timezone.utc

    def test_iso8601_utc_z(self, adapter):
        result = adapter.normalize_date("2026-02-26T10:00:00Z")
        assert result is not None
        assert result.year == 2026
        assert result.tzinfo == timezone.utc

    def test_iso8601_no_timezone(self, adapter):
        result = adapter.normalize_date("2026-02-26T10:00:00")
        assert result is not None
        assert result.year == 2026

    def test_date_only_iso(self, adapter):
        result = adapter.normalize_date("2026-02-26")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 26

    def test_rfc2822(self, adapter):
        result = adapter.normalize_date("Thu, 26 Feb 2026 10:00:00 +0200")
        assert result is not None
        assert result.year == 2026

    def test_empty_returns_none(self, adapter):
        assert adapter.normalize_date("") is None
        assert adapter.normalize_date("   ") is None

    def test_garbage_returns_none(self, adapter):
        assert adapter.normalize_date("not a date at all") is None


# ---------------------------------------------------------------------------
# Cross-adapter date parsing (Yomiuri uses Japanese, Bild uses German)
# ---------------------------------------------------------------------------


class TestAdapterDateChaining:
    """Test that adapter.normalize_date chains to language-specific parsers."""

    def test_yomiuri_japanese_date(self):
        from src.crawling.adapters.multilingual import MULTILINGUAL_ADAPTERS
        adapter = MULTILINGUAL_ADAPTERS["yomiuri"]()
        result = adapter.normalize_date("2026\u5e742\u670826\u65e5 14\u664230\u5206")
        assert result is not None
        assert result.year == 2026

    def test_yomiuri_iso_date(self):
        from src.crawling.adapters.multilingual import MULTILINGUAL_ADAPTERS
        adapter = MULTILINGUAL_ADAPTERS["yomiuri"]()
        result = adapter.normalize_date("2026-02-26T10:00:00+09:00")
        assert result is not None
        assert result.year == 2026

    def test_bild_german_date(self):
        from src.crawling.adapters.multilingual import MULTILINGUAL_ADAPTERS
        adapter = MULTILINGUAL_ADAPTERS["bild"]()
        result = adapter.normalize_date("15. Februar 2026, 14:30 Uhr")
        assert result is not None
        assert result.year == 2026

    def test_bild_iso_date(self):
        from src.crawling.adapters.multilingual import MULTILINGUAL_ADAPTERS
        adapter = MULTILINGUAL_ADAPTERS["bild"]()
        result = adapter.normalize_date("2026-02-26T10:00:00+01:00")
        assert result is not None
        assert result.year == 2026

    def test_lemonde_french_date(self):
        from src.crawling.adapters.multilingual import MULTILINGUAL_ADAPTERS
        adapter = MULTILINGUAL_ADAPTERS["lemonde"]()
        result = adapter.normalize_date("15 f\u00e9vrier 2026")
        assert result is not None
        assert result.month == 2
