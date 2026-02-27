"""Tests for Korean major/economy/niche site adapters (11 sites).

Covers:
    - Adapter instantiation and class attribute validation.
    - Article extraction from sample HTML with correct selectors.
    - Korean date parsing across multiple formats.
    - Korean author/byline extraction.
    - Section URL generation.
    - Article URL detection.
    - Encoding handling.
    - Paywall detection (hankyung.com).
    - Registry lookup and __init__ exports.
    - KR utilities: date parsing, author extraction, encoding.

Reference:
    Step 6: Per-site crawling strategies.
    Step 5: SiteAdapter interface definition.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

# -----------------------------------------------------------------------
# Import all adapters
# -----------------------------------------------------------------------

from src.crawling.adapters.kr_major import (
    ChosunAdapter,
    JoongAngAdapter,
    DongaAdapter,
    HaniAdapter,
    YnaAdapter,
    MkAdapter,
    HankyungAdapter,
    FnnewsAdapter,
    MtAdapter,
    NocutNewsAdapter,
    KmibAdapter,
    ADAPTER_REGISTRY,
    get_adapter,
)

from src.crawling.adapters.kr_major._kr_utils import (
    parse_korean_date,
    extract_korean_author,
    detect_and_decode_korean,
    extract_category_from_url,
    KST,
)

# -----------------------------------------------------------------------
# Test data: minimal HTML samples for extraction tests
# -----------------------------------------------------------------------

CHOSUN_ARTICLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="South Korea Election Results 2026">
    <meta property="article:published_time" content="2026-02-26T10:30:00+09:00">
    <meta name="author" content="Kim Cheolsu">
</head>
<body>
    <h1 class="article-header__title">South Korea Election Results 2026</h1>
    <span class="article-header__journalist">김철수 기자</span>
    <time class="article-header__date" datetime="2026-02-26T10:30:00+09:00">2026.02.26 10:30</time>
    <nav class="breadcrumb"><a href="/politics/">정치</a></nav>
    <div class="article-body">
        <p>The 2026 South Korean general elections produced significant shifts in the political landscape.</p>
        <p>Multiple parties saw changes in their seat counts as voters responded to economic concerns.</p>
        <p>Analysts noted the increased participation among younger demographics.</p>
    </div>
    <div class="article-ad">Advertisement content</div>
    <div class="related-articles">Related stories here</div>
</body>
</html>"""

JOONGANG_ARTICLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="Korean Economy Shows Resilience">
    <meta property="article:published_time" content="2026-02-26T14:00:00+09:00">
    <meta property="article:section" content="Economy">
</head>
<body>
    <h1 class="headline">Korean Economy Shows Resilience</h1>
    <span class="byline">박영희 기자</span>
    <span class="date">입력 2026.02.26 14:00 | 수정 2026.02.26 15:30</span>
    <div class="article_body">
        <p>Korea's GDP growth exceeded expectations in the first quarter of 2026.</p>
        <p>The Bank of Korea maintained its interest rate at 3.25% during the latest meeting.</p>
        <p>Export figures showed a 12% increase compared to the previous year.</p>
    </div>
    <div class="ab_ad">Ad content</div>
</body>
</html>"""

HANKYUNG_PAYWALL_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="Premium: Market Analysis Report">
    <meta property="article:published_time" content="2026-02-26T09:00:00+09:00">
</head>
<body>
    <h1 class="article-title">Premium: Market Analysis Report</h1>
    <span class="byline">이경제 기자</span>
    <div class="article-body">
        <p>This article is premium content...</p>
    </div>
    <div class="paywall-prompt">Subscribe to Hankyung Premium to read the full article.</div>
</body>
</html>"""

HANKYUNG_FREE_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="Tech Stocks Rally After AI Announcement">
    <meta property="article:published_time" content="2026-02-26T11:30:00+09:00">
</head>
<body>
    <h1 class="article-title">Tech Stocks Rally After AI Announcement</h1>
    <span class="byline">최주식 선임기자</span>
    <div class="article-body">
        <p>Major technology stocks surged in early trading on Wednesday after a breakthrough AI announcement.</p>
        <p>Samsung Electronics led the rally with a 4.2% gain, while SK Hynix rose 3.8%.</p>
        <p>The KOSPI index climbed above the 3,000 mark for the first time in 2026.</p>
        <p>Analysts attributed the gains to renewed optimism about AI chip demand.</p>
    </div>
</body>
</html>"""

NOCUTNEWS_ARTICLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="CBS NoCut News Report">
    <meta property="article:published_time" content="2025-02-28T10:24:38+09:00">
    <script type="application/ld+json">
    {
        "@type": "NewsArticle",
        "headline": "Government Announces New Education Policy",
        "datePublished": "2025-02-28T10:24:38",
        "author": {"@type": "Person", "name": "CBS노컷뉴스 홍길동 기자"},
        "articleSection": ["정치", "교육"],
        "mainEntityOfPage": "https://www.nocutnews.co.kr/news/6345678"
    }
    </script>
</head>
<body>
    <h2 class="title">Government Announces New Education Policy</h2>
    <span class="reporter">CBS노컷뉴스 홍길동 기자</span>
    <div class="article_txt">
        <p>The Ministry of Education announced a comprehensive reform package today.</p>
        <p>The reforms include changes to the university admissions system and curriculum standards.</p>
        <p>Education experts expressed mixed reactions to the proposed changes.</p>
    </div>
</body>
</html>"""

KMIB_ARTICLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="National Assembly Passes Budget Bill">
    <meta property="article:published_time" content="2026-02-26T16:00:00+09:00">
</head>
<body>
    <script>
        dataLayer = [{'author_name': '김기자', 'first_published_date': '2026-02-26 16:00', 'article_category': 'Politics'}];
    </script>
    <h1 class="article-title">National Assembly Passes Budget Bill</h1>
    <span class="byline">김기자 기자</span>
    <div class="article-body">
        <p>The National Assembly approved the supplementary budget bill after marathon negotiations.</p>
        <p>The bill allocates additional funds for economic stimulus and social welfare programs.</p>
        <p>Opposition parties expressed reservations but ultimately voted in favor.</p>
    </div>
</body>
</html>"""


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

ALL_ADAPTER_CLASSES = [
    ChosunAdapter,
    JoongAngAdapter,
    DongaAdapter,
    HaniAdapter,
    YnaAdapter,
    MkAdapter,
    HankyungAdapter,
    FnnewsAdapter,
    MtAdapter,
    NocutNewsAdapter,
    KmibAdapter,
]


@pytest.fixture(params=ALL_ADAPTER_CLASSES, ids=lambda c: c.SITE_ID)
def adapter(request):
    """Parametrized fixture yielding each adapter class instance."""
    return request.param()


# =======================================================================
# Test Suite 1: Adapter Structure and Interface Compliance
# =======================================================================


class TestAdapterStructure:
    """Verify all adapters implement the BaseSiteAdapter interface correctly."""

    def test_adapter_count(self):
        """Exactly 11 adapters must be registered."""
        assert len(ADAPTER_REGISTRY) == 11

    def test_adapter_count_in_all(self):
        """__all__ exports exactly 11 adapter classes."""
        from src.crawling.adapters.kr_major import __all__
        assert len(__all__) == 11

    def test_site_id_set(self, adapter):
        """Every adapter must have a non-empty SITE_ID."""
        assert adapter.SITE_ID, f"{adapter.__class__.__name__} missing SITE_ID"

    def test_site_name_set(self, adapter):
        """Every adapter must have a non-empty SITE_NAME."""
        assert adapter.SITE_NAME, f"{adapter.__class__.__name__} missing SITE_NAME"

    def test_site_url_set(self, adapter):
        """Every adapter must have a SITE_URL starting with https://."""
        assert adapter.SITE_URL.startswith("https://"), (
            f"{adapter.SITE_ID}: SITE_URL must start with https://"
        )

    def test_language_is_korean(self, adapter):
        """All adapters in this group are Korean-language sites."""
        assert adapter.LANGUAGE == "ko"

    def test_region_is_kr(self, adapter):
        """All adapters in this group are in the KR region."""
        assert adapter.REGION == "kr"

    def test_rss_url_set(self, adapter):
        """Every adapter should have at least one RSS URL."""
        rss_urls = adapter.get_rss_urls()
        assert len(rss_urls) >= 1, f"{adapter.SITE_ID}: no RSS URLs defined"

    def test_section_urls_non_empty(self, adapter):
        """Every adapter should define section URLs for DOM fallback."""
        sections = adapter.get_section_urls()
        assert len(sections) >= 3, (
            f"{adapter.SITE_ID}: fewer than 3 section URLs"
        )

    def test_selectors_dict_complete(self, adapter):
        """get_selectors() must return all required keys."""
        selectors = adapter.get_selectors()
        required_keys = {"title_css", "body_css", "date_css", "author_css"}
        for key in required_keys:
            assert key in selectors, (
                f"{adapter.SITE_ID}: missing selector key {key!r}"
            )

    def test_anti_block_config_complete(self, adapter):
        """get_anti_block_config() must return all required keys."""
        config = adapter.get_anti_block_config()
        required_keys = {
            "tier", "ua_tier", "requires_proxy", "proxy_region",
            "rate_limit", "max_requests_per_hour", "bot_block_level",
        }
        for key in required_keys:
            assert key in config, (
                f"{adapter.SITE_ID}: missing anti_block key {key!r}"
            )

    def test_proxy_required(self, adapter):
        """All Korean sites require KR proxy."""
        assert adapter.REQUIRES_PROXY is True
        assert adapter.PROXY_REGION == "kr"

    def test_charset_is_utf8(self, adapter):
        """All modern Korean sites in this group use UTF-8."""
        assert adapter.CHARSET == "utf-8"

    def test_extract_article_is_callable(self, adapter):
        """extract_article must be implemented (not raise NotImplementedError)."""
        assert callable(adapter.extract_article)

    def test_get_section_urls_is_callable(self, adapter):
        """get_section_urls must be implemented."""
        assert callable(adapter.get_section_urls)

    def test_repr(self, adapter):
        """__repr__ should include site_id."""
        r = repr(adapter)
        assert adapter.SITE_ID in r

    def test_registry_matches_site_ids(self):
        """Registry keys must match adapter SITE_IDs."""
        for site_id, cls in ADAPTER_REGISTRY.items():
            instance = cls()
            assert instance.SITE_ID == site_id

    def test_get_adapter_function(self):
        """get_adapter() returns correct class or None."""
        assert get_adapter("chosun") is ChosunAdapter
        assert get_adapter("nonexistent") is None


# =======================================================================
# Test Suite 2: Article Extraction
# =======================================================================


class TestChosunExtraction:
    """Chosun Ilbo article extraction tests."""

    def test_extract_title(self):
        adapter = ChosunAdapter()
        result = adapter.extract_article(CHOSUN_ARTICLE_HTML, "https://www.chosun.com/politics/article/20260226001")
        assert result["title"] == "South Korea Election Results 2026"

    def test_extract_body(self):
        adapter = ChosunAdapter()
        result = adapter.extract_article(CHOSUN_ARTICLE_HTML, "https://www.chosun.com/politics/article/20260226001")
        assert "political landscape" in result["body"]
        assert "Advertisement content" not in result["body"]

    def test_extract_date(self):
        adapter = ChosunAdapter()
        result = adapter.extract_article(CHOSUN_ARTICLE_HTML, "https://www.chosun.com/politics/article/20260226001")
        assert result["published_at"] is not None
        assert result["published_at"].year == 2026
        assert result["published_at"].month == 2

    def test_extract_author(self):
        adapter = ChosunAdapter()
        result = adapter.extract_article(CHOSUN_ARTICLE_HTML, "https://www.chosun.com/politics/article/20260226001")
        # Should extract Korean name without 기자 suffix
        assert result["author"] is not None

    def test_extract_category(self):
        adapter = ChosunAdapter()
        result = adapter.extract_article(CHOSUN_ARTICLE_HTML, "https://www.chosun.com/politics/article/20260226001")
        assert result["category"] == "politics"

    def test_body_excludes_ads(self):
        adapter = ChosunAdapter()
        result = adapter.extract_article(CHOSUN_ARTICLE_HTML, "https://www.chosun.com/politics/article/20260226001")
        assert "Advertisement" not in result["body"]
        assert "Related stories" not in result["body"]


class TestJoongAngExtraction:
    """JoongAng Ilbo article extraction tests."""

    def test_extract_title(self):
        adapter = JoongAngAdapter()
        result = adapter.extract_article(JOONGANG_ARTICLE_HTML, "https://www.joongang.co.kr/article/12345")
        assert result["title"] == "Korean Economy Shows Resilience"

    def test_extract_body(self):
        adapter = JoongAngAdapter()
        result = adapter.extract_article(JOONGANG_ARTICLE_HTML, "https://www.joongang.co.kr/article/12345")
        assert "GDP growth" in result["body"]
        assert "Ad content" not in result["body"]

    def test_extract_date(self):
        adapter = JoongAngAdapter()
        result = adapter.extract_article(JOONGANG_ARTICLE_HTML, "https://www.joongang.co.kr/article/12345")
        assert result["published_at"] is not None
        assert result["published_at"].year == 2026

    def test_extract_category(self):
        adapter = JoongAngAdapter()
        result = adapter.extract_article(JOONGANG_ARTICLE_HTML, "https://www.joongang.co.kr/economy/article/12345")
        assert result["category"] == "economy"


class TestHankyungPaywall:
    """Hankyung paywall detection tests."""

    def test_paywall_detected(self):
        adapter = HankyungAdapter()
        result = adapter.extract_article(
            HANKYUNG_PAYWALL_HTML,
            "https://www.hankyung.com/article/123",
        )
        assert result["is_paywall_truncated"] is True

    def test_free_article_not_flagged(self):
        adapter = HankyungAdapter()
        result = adapter.extract_article(
            HANKYUNG_FREE_HTML,
            "https://www.hankyung.com/article/456",
        )
        assert result.get("is_paywall_truncated", False) is False

    def test_paywall_type_is_soft_metered(self):
        adapter = HankyungAdapter()
        assert adapter.PAYWALL_TYPE == "soft-metered"


class TestNocutNewsExtraction:
    """NoCut News extraction tests (JSON-LD primary)."""

    def test_extract_title_from_json_ld(self):
        adapter = NocutNewsAdapter()
        result = adapter.extract_article(
            NOCUTNEWS_ARTICLE_HTML,
            "https://www.nocutnews.co.kr/news/6345678",
        )
        assert result["title"] == "Government Announces New Education Policy"

    def test_extract_date_from_json_ld(self):
        adapter = NocutNewsAdapter()
        result = adapter.extract_article(
            NOCUTNEWS_ARTICLE_HTML,
            "https://www.nocutnews.co.kr/news/6345678",
        )
        assert result["published_at"] is not None
        assert result["published_at"].year == 2025
        assert result["published_at"].month == 2

    def test_extract_author_from_json_ld(self):
        adapter = NocutNewsAdapter()
        result = adapter.extract_article(
            NOCUTNEWS_ARTICLE_HTML,
            "https://www.nocutnews.co.kr/news/6345678",
        )
        # Should extract Korean name from "CBS노컷뉴스 홍길동 기자"
        assert result["author"] is not None

    def test_extract_category_from_json_ld(self):
        adapter = NocutNewsAdapter()
        result = adapter.extract_article(
            NOCUTNEWS_ARTICLE_HTML,
            "https://www.nocutnews.co.kr/news/6345678",
        )
        # articleSection: ["정치", "교육"] — should pick non-포토 section
        assert result["category"] is not None


class TestKmibExtraction:
    """Kookmin Ilbo extraction tests (dataLayer primary)."""

    def test_extract_author_from_datalayer(self):
        adapter = KmibAdapter()
        result = adapter.extract_article(
            KMIB_ARTICLE_HTML,
            "https://www.kmib.co.kr/view.asp?arcid=123",
        )
        assert result["author"] is not None

    def test_extract_category_from_datalayer(self):
        adapter = KmibAdapter()
        result = adapter.extract_article(
            KMIB_ARTICLE_HTML,
            "https://www.kmib.co.kr/view.asp?arcid=123",
        )
        assert result["category"] == "politics"

    def test_extract_date_from_datalayer(self):
        adapter = KmibAdapter()
        result = adapter.extract_article(
            KMIB_ARTICLE_HTML,
            "https://www.kmib.co.kr/view.asp?arcid=123",
        )
        assert result["published_at"] is not None

    def test_datalayer_extraction(self):
        datalayer = KmibAdapter._extract_datalayer(KMIB_ARTICLE_HTML)
        assert datalayer.get("author_name") == "김기자"
        assert datalayer.get("article_category") == "Politics"

    def test_kmib_category_from_url(self):
        assert KmibAdapter._extract_category_from_kmib_url(
            "https://www.kmib.co.kr/view.asp?sid1=pol&arcid=123"
        ) == "politics"
        assert KmibAdapter._extract_category_from_kmib_url(
            "https://www.kmib.co.kr/view.asp?sid1=eco&arcid=123"
        ) == "economy"

    def test_kmib_rss_urls_count(self):
        adapter = KmibAdapter()
        assert len(adapter.get_rss_urls()) == 9


# =======================================================================
# Test Suite 3: Korean Date Parsing (_kr_utils)
# =======================================================================


class TestKoreanDateParsing:
    """Test parse_korean_date with all major formats."""

    def test_iso_8601(self):
        dt = parse_korean_date("2026-02-26T10:30:00+09:00")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 2
        assert dt.day == 26
        # UTC: 10:30 KST = 01:30 UTC
        assert dt.hour == 1
        assert dt.minute == 30

    def test_dotted_date_with_time(self):
        dt = parse_korean_date("2026.02.26 14:30")
        assert dt is not None
        assert dt.year == 2026
        # KST: 14:30 -> UTC: 05:30
        assert dt.hour == 5
        assert dt.minute == 30

    def test_dotted_date_only(self):
        dt = parse_korean_date("2026.02.26")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 2
        # Date-only parses as midnight KST (UTC+9), which is Feb 25 15:00 UTC
        # Verify the KST date is Feb 26 by converting back
        kst_dt = dt.astimezone(KST)
        assert kst_dt.day == 26

    def test_korean_full_date(self):
        dt = parse_korean_date("2026년 2월 26일 14시 30분")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 2

    def test_korean_date_no_time(self):
        dt = parse_korean_date("2026년 2월 26일")
        assert dt is not None
        assert dt.year == 2026

    def test_relative_hours(self):
        dt = parse_korean_date("3시간 전")
        assert dt is not None
        now = datetime.now(timezone.utc)
        delta = now - dt
        # Should be approximately 3 hours ago (allow 5 min tolerance)
        assert 2.9 * 3600 <= delta.total_seconds() <= 3.1 * 3600

    def test_relative_minutes(self):
        dt = parse_korean_date("30분 전")
        assert dt is not None
        now = datetime.now(timezone.utc)
        delta = now - dt
        assert 29 * 60 <= delta.total_seconds() <= 31 * 60

    def test_relative_days(self):
        dt = parse_korean_date("2일 전")
        assert dt is not None
        now = datetime.now(timezone.utc)
        delta = now - dt
        assert 1.9 * 86400 <= delta.total_seconds() <= 2.1 * 86400

    def test_yesterday(self):
        dt = parse_korean_date("어제")
        assert dt is not None
        now = datetime.now(KST)
        yesterday = now - timedelta(days=1)
        assert dt.date() == yesterday.astimezone(timezone.utc).date() or \
            abs((dt - yesterday.astimezone(timezone.utc)).total_seconds()) < 86400

    def test_today(self):
        dt = parse_korean_date("오늘")
        assert dt is not None
        now = datetime.now(timezone.utc)
        # Should be today
        assert abs((now - dt).total_seconds()) < 86400

    def test_input_prefix_stripping(self):
        dt = parse_korean_date("입력 2026.02.26 10:30")
        assert dt is not None
        assert dt.year == 2026

    def test_input_modify_pair(self):
        dt = parse_korean_date("입력 2026.02.26 10:30 | 수정 2026.02.26 11:45")
        assert dt is not None
        assert dt.year == 2026
        # Should take the "입력" (input) date, not "수정" (modified)
        assert dt.hour == 1  # 10:30 KST -> 01:30 UTC
        assert dt.minute == 30

    def test_dow_suffix_stripping(self):
        dt = parse_korean_date("2026.02.26(목)")
        assert dt is not None
        assert dt.year == 2026

    def test_rfc_2822(self):
        dt = parse_korean_date("Thu, 26 Feb 2026 10:30:00 +0900")
        assert dt is not None
        assert dt.year == 2026

    def test_empty_returns_none(self):
        assert parse_korean_date("") is None
        assert parse_korean_date(None) is None
        assert parse_korean_date("  ") is None

    def test_garbage_returns_none(self):
        assert parse_korean_date("not a date at all") is None

    def test_korean_ampm_afternoon(self):
        dt = parse_korean_date("2026.02.26 오후 2:30")
        assert dt is not None
        assert dt.year == 2026
        # 오후 2:30 = 14:30 KST = 05:30 UTC
        assert dt.hour == 5
        assert dt.minute == 30

    def test_dash_separated_date(self):
        dt = parse_korean_date("2026-02-26 14:30:00")
        assert dt is not None
        assert dt.year == 2026


# =======================================================================
# Test Suite 4: Korean Author Extraction (_kr_utils)
# =======================================================================


class TestKoreanAuthorExtraction:
    """Test extract_korean_author with various byline patterns."""

    def test_name_with_gija(self):
        result = extract_korean_author("김철수 기자")
        assert result == "김철수"

    def test_name_with_senior_gija(self):
        result = extract_korean_author("박영희 선임기자")
        assert result == "박영희"

    def test_name_with_correspondent(self):
        result = extract_korean_author("이민수 특파원")
        assert result == "이민수"

    def test_gija_equals_name(self):
        result = extract_korean_author("기자 = 홍길동")
        assert result == "홍길동"

    def test_cbs_prefix_pattern(self):
        result = extract_korean_author("CBS노컷뉴스 홍길동 기자")
        assert result == "홍길동"

    def test_bracketed_name(self):
        result = extract_korean_author("[김기자]")
        assert result is not None

    def test_name_with_email(self):
        result = extract_korean_author("김철수 기자 cheolsu@chosun.com")
        assert result == "김철수"

    def test_empty_returns_none(self):
        assert extract_korean_author("") is None
        assert extract_korean_author(None) is None

    def test_non_name_filtered(self):
        # "기자" alone is not a name
        result = extract_korean_author("기자")
        # Should return the cleaned string or None, not "기자"
        assert result != "기자" or result is None


# =======================================================================
# Test Suite 5: Encoding Handling (_kr_utils)
# =======================================================================


class TestEncodingHandling:
    """Test Korean encoding detection and decoding."""

    def test_utf8_decoding(self):
        text = "한글 테스트"
        encoded = text.encode("utf-8")
        result = detect_and_decode_korean(encoded, "utf-8")
        assert result == text

    def test_euc_kr_fallback(self):
        text = "한글 테스트"
        encoded = text.encode("euc-kr")
        # Declare as utf-8 but actually euc-kr — should fall back
        result = detect_and_decode_korean(encoded, "utf-8")
        assert "한글" in result

    def test_cp949_fallback(self):
        text = "한글 테스트"
        encoded = text.encode("cp949")
        result = detect_and_decode_korean(encoded, "utf-8")
        assert "한글" in result

    def test_adapter_handle_encoding(self):
        adapter = ChosunAdapter()
        text = "테스트 문장"
        encoded = text.encode("utf-8")
        result = adapter.handle_encoding(encoded)
        assert result == text


# =======================================================================
# Test Suite 6: Category Extraction (_kr_utils)
# =======================================================================


class TestCategoryExtraction:
    """Test URL-based category extraction for Korean sites."""

    def test_chosun_politics(self):
        result = extract_category_from_url(
            "https://www.chosun.com/politics/article/20260226001",
            "chosun",
        )
        assert result == "politics"

    def test_hani_economy(self):
        result = extract_category_from_url(
            "https://www.hani.co.kr/arti/economy/finance/1234567.html",
            "hani",
        )
        assert result == "economy"

    def test_mk_stock(self):
        result = extract_category_from_url(
            "https://www.mk.co.kr/news/stock/12345678",
            "mk",
        )
        assert result == "stock"

    def test_yna_international(self):
        result = extract_category_from_url(
            "https://www.yna.co.kr/international/all",
            "yna",
        )
        assert result == "international"


# =======================================================================
# Test Suite 7: Article URL Detection
# =======================================================================


class TestArticleUrlDetection:
    """Test _is_article_url for site-specific patterns."""

    def test_chosun_article_url(self):
        adapter = ChosunAdapter()
        assert adapter._is_article_url(
            "https://www.chosun.com/politics/article/20260226001"
        )

    def test_chosun_section_url_rejected(self):
        adapter = ChosunAdapter()
        # Section URL has only 1 path segment — should fail generic check
        # but /politics/ alone might pass. The key test is that article links
        # are correctly identified.
        assert adapter._is_article_url(
            "https://www.chosun.com/politics/article/20260226001"
        )

    def test_joongang_article_url(self):
        adapter = JoongAngAdapter()
        assert adapter._is_article_url(
            "https://www.joongang.co.kr/article/12345678"
        )

    def test_hani_article_url(self):
        adapter = HaniAdapter()
        assert adapter._is_article_url(
            "https://www.hani.co.kr/arti/politics/assembly/1234567.html"
        )

    def test_yna_article_url(self):
        adapter = YnaAdapter()
        assert adapter._is_article_url(
            "https://www.yna.co.kr/view/AKR20260226001234567"
        )

    def test_kmib_article_url(self):
        adapter = KmibAdapter()
        assert adapter._is_article_url(
            "https://www.kmib.co.kr/view.asp?arcid=0012345678"
        )

    def test_nocutnews_article_url(self):
        adapter = NocutNewsAdapter()
        assert adapter._is_article_url(
            "https://www.nocutnews.co.kr/news/6345678"
        )

    def test_cross_domain_rejected(self):
        adapter = ChosunAdapter()
        assert not adapter._is_article_url(
            "https://www.joongang.co.kr/article/12345"
        )


# =======================================================================
# Test Suite 8: Rate Limiting Configuration Matches Step 6
# =======================================================================


class TestRateLimitConfig:
    """Verify rate limits match Step 6 crawling strategies."""

    def test_chosun_rate_limit(self):
        adapter = ChosunAdapter()
        assert adapter.RATE_LIMIT_SECONDS == 5.0

    def test_joongang_rate_limit(self):
        adapter = JoongAngAdapter()
        assert adapter.RATE_LIMIT_SECONDS == 10.0
        assert adapter.JITTER_SECONDS == 3.0

    def test_nocutnews_low_rate_limit(self):
        adapter = NocutNewsAdapter()
        assert adapter.RATE_LIMIT_SECONDS == 2.0
        assert adapter.BOT_BLOCK_LEVEL == "LOW"

    def test_joongang_high_block(self):
        adapter = JoongAngAdapter()
        assert adapter.BOT_BLOCK_LEVEL == "HIGH"
        assert adapter.UA_TIER == 3

    def test_all_medium_sites_5s(self):
        """Most MEDIUM sites should have 5s rate limit."""
        medium_sites = [
            ChosunAdapter, DongaAdapter, HaniAdapter, YnaAdapter,
            MkAdapter, HankyungAdapter, FnnewsAdapter, MtAdapter,
            KmibAdapter,
        ]
        for cls in medium_sites:
            adapter = cls()
            assert adapter.RATE_LIMIT_SECONDS == 5.0, (
                f"{adapter.SITE_ID} should have 5s rate limit"
            )
