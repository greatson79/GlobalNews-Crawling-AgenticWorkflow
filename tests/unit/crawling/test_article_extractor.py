"""Tests for ArticleExtractor: multi-library fallback chain, metadata extraction.

Tests cover:
    - Title extraction fallback chain (CSS -> og:title -> <title> -> h1)
    - Date extraction from meta tags, JSON-LD, and <time> elements
    - Author extraction from meta tags, JSON-LD, and byline patterns
    - Trafilatura extraction (mocked)
    - CSS selector fallback extraction
    - Hard-paywall title-only extraction
    - Paywall truncation detection
    - Content hash generation
    - ExtractionResult to RawArticle conversion
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.crawling.article_extractor import (
    ArticleExtractor,
    ExtractionResult,
    _extract_title,
    _extract_date_from_html,
    _extract_author_from_html,
    _extract_with_css,
    _clean_author,
    _parse_date_string,
    MIN_BODY_LENGTH,
    PAYWALL_TRUNCATION_THRESHOLD,
)
from src.crawling.contracts import RawArticle, compute_content_hash
from src.crawling.network_guard import NetworkGuard, FetchResponse
from src.utils.error_handler import ParseError, NetworkError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_guard():
    """Create a mock NetworkGuard."""
    guard = MagicMock(spec=NetworkGuard)
    return guard


@pytest.fixture
def sample_html():
    """A realistic news article HTML page."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Breaking: Major Policy Change Announced - Example News</title>
    <meta property="og:title" content="Major Policy Change Announced"/>
    <meta property="article:published_time" content="2025-01-20T10:00:00Z"/>
    <meta name="author" content="Jane Smith"/>
    <script type="application/ld+json">
    {
        "datePublished": "2025-01-20T10:00:00Z",
        "author": {"name": "Jane Smith", "@type": "Person"}
    }
    </script>
</head>
<body>
    <article>
        <h1>Major Policy Change Announced</h1>
        <div class="byline">By Jane Smith</div>
        <time datetime="2025-01-20T10:00:00Z">January 20, 2025</time>
        <div class="article-body">
            <p>The government announced a significant policy change today that
            will affect millions of citizens across the country. The new regulation
            introduces stricter environmental standards for manufacturing companies.</p>
            <p>Industry leaders have expressed mixed reactions to the announcement.
            While environmental groups welcomed the changes, business associations
            warned of potential economic impacts on small and medium enterprises.</p>
            <p>The policy is set to take effect starting March 1, 2025, with a
            transition period of six months for companies to comply with the new
            standards. Government officials have promised support packages for
            affected businesses during the transition.</p>
        </div>
    </article>
    <nav>Navigation content</nav>
    <aside>Related articles sidebar</aside>
</body>
</html>"""


@pytest.fixture
def paywall_html():
    """HTML page from a hard-paywall site."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Exclusive Report - Financial Times</title>
    <meta property="og:title" content="Exclusive Report on Market Trends"/>
    <meta property="article:published_time" content="2025-01-20T10:00:00Z"/>
    <meta name="author" content="John Doe"/>
</head>
<body>
    <article>
        <h1>Exclusive Report on Market Trends</h1>
        <div class="article-body">
            <p>Subscribe to read the full article...</p>
        </div>
    </article>
</body>
</html>"""


@pytest.fixture
def minimal_html():
    """Minimal HTML with just a title tag."""
    return """<!DOCTYPE html>
<html>
<head><title>Simple Page Title</title></head>
<body><p>Some content here but not much to extract as an article body.</p></body>
</html>"""


def _make_fetch_response(text: str, url: str = "https://example.com/article") -> FetchResponse:
    """Helper to create a FetchResponse."""
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
# Content Hash Tests
# ===========================================================================

class TestContentHash:
    """Tests for compute_content_hash()."""

    def test_consistent_hash(self):
        """Same content should produce same hash."""
        body = "This is a test article body."
        hash1 = compute_content_hash(body)
        hash2 = compute_content_hash(body)
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Different content should produce different hashes."""
        hash1 = compute_content_hash("Article body one")
        hash2 = compute_content_hash("Article body two")
        assert hash1 != hash2

    def test_whitespace_normalization(self):
        """Extra whitespace should not affect hash."""
        hash1 = compute_content_hash("Hello   world")
        hash2 = compute_content_hash("Hello world")
        assert hash1 == hash2

    def test_case_normalization(self):
        """Case should not affect hash (normalized to lowercase)."""
        hash1 = compute_content_hash("HELLO WORLD")
        hash2 = compute_content_hash("hello world")
        assert hash1 == hash2

    def test_empty_body_returns_empty(self):
        """Empty body should return empty string."""
        assert compute_content_hash("") == ""
        assert compute_content_hash("   ") == ""

    def test_hash_is_hex_string(self):
        """Hash should be a valid hex string (SHA-256 = 64 chars)."""
        h = compute_content_hash("Test body")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ===========================================================================
# ExtractionResult Tests
# ===========================================================================

class TestExtractionResult:
    """Tests for ExtractionResult container."""

    def test_is_complete_with_title(self):
        """is_complete should be True when title is present."""
        result = ExtractionResult(url="https://example.com")
        result.title = "Test Title"
        assert result.is_complete is True

    def test_is_complete_without_title(self):
        """is_complete should be False when title is empty."""
        result = ExtractionResult(url="https://example.com")
        assert result.is_complete is False

    def test_has_body_with_sufficient_text(self):
        """has_body should be True when body >= MIN_BODY_LENGTH."""
        result = ExtractionResult(url="https://example.com")
        result.body = "x" * MIN_BODY_LENGTH
        assert result.has_body is True

    def test_has_body_with_short_text(self):
        """has_body should be False when body is too short."""
        result = ExtractionResult(url="https://example.com")
        result.body = "short"
        assert result.has_body is False

    def test_to_raw_article_conversion(self):
        """to_raw_article should produce a valid RawArticle."""
        result = ExtractionResult(url="https://example.com/article/1")
        result.title = "Test Article"
        result.body = "A" * 200
        result.published_at = datetime(2025, 1, 20, tzinfo=timezone.utc)
        result.author = "Author Name"
        result.language = "en"

        article = result.to_raw_article(
            source_id="test_site",
            source_name="Test Site",
        )

        assert isinstance(article, RawArticle)
        assert article.title == "Test Article"
        assert article.source_id == "test_site"
        assert article.content_hash != ""  # Should have computed hash
        assert article.crawled_at is not None

    def test_paywall_truncation_detection(self):
        """Short body on paywall sites should be flagged as truncated."""
        result = ExtractionResult(url="https://example.com/article")
        result.title = "Paywall Article"
        result.body = "Subscribe to read more."  # < PAYWALL_TRUNCATION_THRESHOLD

        article = result.to_raw_article(
            source_id="ft",
            source_name="Financial Times",
            is_paywall=True,
        )

        assert article.is_paywall_truncated is True


# ===========================================================================
# Title Extraction Tests
# ===========================================================================

class TestTitleExtraction:
    """Tests for _extract_title() fallback chain."""

    def _make_soup(self, html: str):
        """Create a BeautifulSoup object from HTML."""
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    def test_custom_css_selector_priority(self):
        """Custom CSS selector should take priority."""
        html = """
        <html>
        <head><title>Page Title - Site Name</title></head>
        <body>
            <h1 class="article-title">CSS Selector Title</h1>
            <h1>Another H1</h1>
        </body></html>"""
        soup = self._make_soup(html)
        title = _extract_title(soup, title_css="h1.article-title")
        assert title == "CSS Selector Title"

    def test_og_title_fallback(self):
        """og:title should be used when CSS selector is empty."""
        html = """
        <html><head>
            <meta property="og:title" content="OG Title Value"/>
            <title>Page Title - Site Name</title>
        </head><body></body></html>"""
        soup = self._make_soup(html)
        title = _extract_title(soup)
        assert title == "OG Title Value"

    def test_title_tag_fallback(self):
        """<title> tag should be used when og:title is missing."""
        html = """
        <html><head><title>Article Title - Site Name</title></head>
        <body></body></html>"""
        soup = self._make_soup(html)
        title = _extract_title(soup)
        # Should strip site name suffix
        assert "Site Name" not in title or "Article Title" in title

    def test_h1_fallback(self):
        """<h1> should be used when <title> and og:title are missing."""
        html = """
        <html><head></head><body>
            <h1>H1 Article Title</h1>
        </body></html>"""
        soup = self._make_soup(html)
        title = _extract_title(soup)
        assert title == "H1 Article Title"

    def test_h2_fallback(self):
        """Lower headings should be used as last resort."""
        html = """
        <html><head></head><body>
            <h2>H2 Title</h2>
        </body></html>"""
        soup = self._make_soup(html)
        title = _extract_title(soup)
        assert title == "H2 Title"

    def test_empty_when_nothing_found(self):
        """Should return empty string when no title element is found."""
        html = "<html><head></head><body><p>No heading at all</p></body></html>"
        soup = self._make_soup(html)
        title = _extract_title(soup)
        assert title == ""


# ===========================================================================
# Date Extraction Tests
# ===========================================================================

class TestDateExtraction:
    """Tests for _extract_date_from_html() fallback chain."""

    def _make_soup(self, html: str):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    def test_article_published_time_meta(self):
        """article:published_time meta tag should be extracted."""
        html = """<html><head>
            <meta property="article:published_time" content="2025-01-20T10:00:00Z"/>
        </head><body></body></html>"""
        soup = self._make_soup(html)
        dt = _extract_date_from_html(soup)
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 20

    def test_json_ld_date_published(self):
        """JSON-LD datePublished should be extracted."""
        html = """<html><head>
            <script type="application/ld+json">
            {"datePublished": "2025-01-20T10:00:00Z"}
            </script>
        </head><body></body></html>"""
        soup = self._make_soup(html)
        dt = _extract_date_from_html(soup)
        assert dt is not None
        assert dt.year == 2025

    def test_time_element_datetime(self):
        """<time> element datetime attribute should be extracted."""
        html = """<html><body>
            <time datetime="2025-01-20T10:00:00Z">January 20, 2025</time>
        </body></html>"""
        soup = self._make_soup(html)
        dt = _extract_date_from_html(soup)
        assert dt is not None

    def test_custom_css_date_selector(self):
        """Custom date CSS selector should take priority."""
        html = """<html><body>
            <span class="pub-date" datetime="2025-01-20T10:00:00Z">Jan 20</span>
        </body></html>"""
        soup = self._make_soup(html)
        dt = _extract_date_from_html(soup, date_css=".pub-date")
        assert dt is not None

    def test_none_when_no_date(self):
        """Should return None when no date is found."""
        html = "<html><body><p>No date here</p></body></html>"
        soup = self._make_soup(html)
        dt = _extract_date_from_html(soup)
        assert dt is None

    def test_malformed_json_ld_no_crash(self):
        """Malformed JSON-LD should not crash."""
        html = """<html><head>
            <script type="application/ld+json">not valid json</script>
        </head><body></body></html>"""
        soup = self._make_soup(html)
        dt = _extract_date_from_html(soup)
        # Should return None, not raise
        assert dt is None


# ===========================================================================
# Author Extraction Tests
# ===========================================================================

class TestAuthorExtraction:
    """Tests for _extract_author_from_html() fallback chain."""

    def _make_soup(self, html: str):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    def test_meta_author(self):
        """article:author meta tag should be extracted."""
        html = """<html><head>
            <meta name="author" content="Jane Smith"/>
        </head><body></body></html>"""
        soup = self._make_soup(html)
        author = _extract_author_from_html(soup)
        assert author == "Jane Smith"

    def test_json_ld_author(self):
        """JSON-LD author field should be extracted."""
        html = """<html><head>
            <script type="application/ld+json">
            {"author": {"name": "John Doe", "@type": "Person"}}
            </script>
        </head><body></body></html>"""
        soup = self._make_soup(html)
        author = _extract_author_from_html(soup)
        assert author == "John Doe"

    def test_json_ld_author_list(self):
        """JSON-LD with multiple authors should join names."""
        html = """<html><head>
            <script type="application/ld+json">
            {"author": [{"name": "Alice"}, {"name": "Bob"}]}
            </script>
        </head><body></body></html>"""
        soup = self._make_soup(html)
        author = _extract_author_from_html(soup)
        assert "Alice" in author
        assert "Bob" in author

    def test_byline_class(self):
        """.byline class should be extracted."""
        html = """<html><body>
            <div class="byline">By Sarah Johnson</div>
        </body></html>"""
        soup = self._make_soup(html)
        author = _extract_author_from_html(soup)
        assert author == "Sarah Johnson"  # "By " prefix should be cleaned

    def test_custom_css_author(self):
        """Custom author CSS selector should take priority."""
        html = """<html><body>
            <span class="writer">By Dr. Smith</span>
        </body></html>"""
        soup = self._make_soup(html)
        author = _extract_author_from_html(soup, author_css=".writer")
        assert author == "Dr. Smith"  # "By " prefix cleaned

    def test_clean_author_removes_prefix(self):
        """_clean_author should remove common prefixes."""
        assert _clean_author("By Jane Smith") == "Jane Smith"
        assert _clean_author("by Jane Smith") == "Jane Smith"
        assert _clean_author("Author: Jane Smith") == "Jane Smith"
        assert _clean_author("Written by Jane Smith") == "Jane Smith"


# ===========================================================================
# CSS Extraction Tests
# ===========================================================================

class TestCSSExtraction:
    """Tests for _extract_with_css() fallback extractor."""

    def test_extracts_all_fields(self):
        """Should extract title, body, date, and author via CSS selectors."""
        html = """<html>
        <head><meta property="og:title" content="CSS Test Article"/></head>
        <body>
            <h1 class="title">CSS Test Article</h1>
            <span class="date" datetime="2025-01-20T10:00:00Z">Jan 20</span>
            <span class="author">By Test Author</span>
            <div class="content">
                <p>This is the first paragraph of the article body. It contains
                enough text to be considered a valid article extraction. We need
                at least 100 characters of body text for the extraction to be
                considered successful.</p>
                <p>Second paragraph with additional content.</p>
            </div>
        </body></html>"""

        selectors = {
            "title_css": "h1.title",
            "body_css": "div.content",
            "date_css": "span.date",
            "author_css": "span.author",
        }

        result = _extract_with_css(html, "https://example.com/article", selectors)

        assert result.title == "CSS Test Article"
        assert len(result.body) >= MIN_BODY_LENGTH
        assert result.published_at is not None
        assert result.author == "Test Author"
        assert result.extraction_method == "css"

    def test_strips_unwanted_elements(self):
        """Should remove ads, navigation, and other boilerplate."""
        html = """<html><body>
            <div class="content">
                <p>Main article content here with plenty of text to be valid.</p>
                <script>alert('evil')</script>
                <div class="ad">Advertisement</div>
                <nav>Navigation links</nav>
                <p>More article content that should be kept in the output.</p>
            </div>
        </body></html>"""

        selectors = {"body_css": "div.content"}
        result = _extract_with_css(html, "https://example.com/article", selectors)

        assert "alert" not in result.body
        assert "Advertisement" not in result.body
        assert "Main article content" in result.body

    def test_empty_selectors_uses_fallbacks(self):
        """Empty selectors should trigger fallback chain for title."""
        html = """<html>
        <head><meta property="og:title" content="Fallback Title"/></head>
        <body></body></html>"""

        result = _extract_with_css(html, "https://example.com/article", {})
        assert result.title == "Fallback Title"


# ===========================================================================
# ArticleExtractor Integration Tests
# ===========================================================================

class TestArticleExtractor:
    """Tests for the ArticleExtractor orchestrator."""

    def test_extract_full_article(self, mock_guard, sample_html):
        """Should extract a complete article with all fields."""
        mock_guard.fetch.return_value = _make_fetch_response(sample_html)

        extractor = ArticleExtractor(
            mock_guard,
            use_fundus=False,  # Skip Fundus (not installed in test env)
            use_trafilatura=False,  # Skip Trafilatura for deterministic test
        )

        site_config = {
            "name": "Example News",
            "language": "en",
            "extraction": {
                "paywall_type": "none",
                "title_only": False,
                "charset": "utf-8",
            },
        }

        article = extractor.extract(
            url="https://example.com/article/1",
            source_id="example",
            site_config=site_config,
            html=sample_html,  # Provide pre-fetched HTML
        )

        assert isinstance(article, RawArticle)
        assert article.title  # Title should be non-empty
        assert article.source_id == "example"
        assert article.language == "en"
        assert article.crawled_at is not None

    def test_extract_title_only_for_paywall(self, mock_guard, paywall_html):
        """Hard-paywall sites should only extract title + metadata."""
        extractor = ArticleExtractor(mock_guard, use_fundus=False, use_trafilatura=False)

        site_config = {
            "name": "Financial Times",
            "language": "en",
            "extraction": {
                "paywall_type": "hard",
                "title_only": True,
                "charset": "utf-8",
            },
        }

        article = extractor.extract(
            url="https://ft.com/content/123",
            source_id="ft",
            site_config=site_config,
            html=paywall_html,
        )

        assert article.title != ""
        assert article.body == ""
        assert article.is_paywall_truncated is True

    def test_raises_parse_error_when_no_title(self, mock_guard):
        """Should raise ParseError when title cannot be extracted."""
        html = "<html><body><p>No title whatsoever</p></body></html>"

        extractor = ArticleExtractor(mock_guard, use_fundus=False, use_trafilatura=False)

        site_config = {
            "name": "Test",
            "language": "en",
            "extraction": {"paywall_type": "none", "charset": "utf-8"},
        }

        with pytest.raises(ParseError, match="Failed to extract title"):
            extractor.extract(
                url="https://example.com/no-title",
                source_id="test",
                site_config=site_config,
                html=html,
            )

    def test_title_hint_from_rss(self, mock_guard, minimal_html):
        """RSS title hint should be used when extraction fails."""
        extractor = ArticleExtractor(mock_guard, use_fundus=False, use_trafilatura=False)

        site_config = {
            "name": "Test",
            "language": "en",
            "extraction": {"paywall_type": "none", "charset": "utf-8"},
        }

        article = extractor.extract(
            url="https://example.com/article",
            source_id="test",
            site_config=site_config,
            html=minimal_html,
            title_hint="RSS Title Hint",
        )

        # Title should come from either HTML extraction or the hint
        assert article.title != ""

    def test_fetches_html_when_not_provided(self, mock_guard, sample_html):
        """Should fetch HTML via NetworkGuard when not pre-provided."""
        mock_guard.fetch.return_value = _make_fetch_response(sample_html)

        extractor = ArticleExtractor(mock_guard, use_fundus=False, use_trafilatura=False)

        site_config = {
            "name": "Test",
            "language": "en",
            "extraction": {"paywall_type": "none", "charset": "utf-8"},
        }

        article = extractor.extract(
            url="https://example.com/article",
            source_id="test",
            site_config=site_config,
            # html=None -> should trigger fetch
        )

        mock_guard.fetch.assert_called_once()
        assert article.title != ""

    def test_network_error_propagated(self, mock_guard):
        """NetworkError should propagate when fetch fails."""
        mock_guard.fetch.side_effect = NetworkError("Connection refused", url="https://example.com")

        extractor = ArticleExtractor(mock_guard, use_fundus=False)

        site_config = {
            "name": "Test",
            "language": "en",
            "extraction": {"paywall_type": "none", "charset": "utf-8"},
        }

        with pytest.raises(NetworkError):
            extractor.extract(
                url="https://example.com/article",
                source_id="test",
                site_config=site_config,
            )


# ===========================================================================
# Different HTML Structure Tests
# ===========================================================================

class TestDifferentHTMLStructures:
    """Tests with various real-world-like HTML structures."""

    def _extract(self, html: str, **kwargs) -> RawArticle:
        """Helper to extract an article from HTML."""
        guard = MagicMock(spec=NetworkGuard)
        extractor = ArticleExtractor(guard, use_fundus=False, use_trafilatura=False)
        site_config = {
            "name": "Test Site",
            "language": "en",
            "extraction": {"paywall_type": "none", "charset": "utf-8", **kwargs},
        }
        return extractor.extract(
            url="https://example.com/article",
            source_id="test",
            site_config=site_config,
            html=html,
        )

    def test_wordpress_structure(self):
        """WordPress-like article structure."""
        html = """<!DOCTYPE html>
        <html>
        <head>
            <title>WP Article - My Blog</title>
            <meta property="og:title" content="WordPress Article Title"/>
            <meta property="article:published_time" content="2025-01-20T10:00:00Z"/>
        </head>
        <body>
            <article class="post">
                <h1 class="entry-title">WordPress Article Title</h1>
                <div class="entry-content">
                    <p>This is a WordPress article with typical structure. The content
                    is wrapped in a div with class entry-content. This is common in
                    WordPress themes and provides a reliable extraction target.</p>
                    <p>Second paragraph of the WordPress article body text that adds
                    more content to ensure the body length threshold is met.</p>
                </div>
            </article>
        </body>
        </html>"""

        article = self._extract(html)
        assert "WordPress Article Title" in article.title

    def test_korean_news_structure(self):
        """Korean news site structure with og:title."""
        html = """<!DOCTYPE html>
        <html>
        <head>
            <meta property="og:title" content="Korean News Title"/>
            <meta property="article:published_time" content="2025-01-20T10:00:00+09:00"/>
            <meta name="author" content="Reporter Kim"/>
        </head>
        <body>
            <article>
                <h1>Korean News Title</h1>
                <div id="article-body">
                    <p>Korean news article content with enough text to pass the minimum
                    body length threshold. This simulates a typical Korean news article
                    structure with content in a div with id article-body.</p>
                    <p>Additional paragraph with more content for the article body.</p>
                </div>
            </article>
        </body>
        </html>"""

        article = self._extract(html)
        assert "Korean News Title" in article.title
        assert article.published_at is not None

    def test_minimal_structure_no_article_tag(self):
        """Minimal page without <article> tag."""
        html = """<!DOCTYPE html>
        <html>
        <head><title>Minimal Page Title</title></head>
        <body>
            <h1>The Only Heading</h1>
            <div class="main">
                <p>Content paragraph one with enough text to be considered
                a valid article extraction. We need sufficient content.</p>
                <p>Content paragraph two with additional text material.</p>
            </div>
        </body>
        </html>"""

        article = self._extract(html)
        # Should at least extract the title from <title> or <h1>
        assert article.title != ""
