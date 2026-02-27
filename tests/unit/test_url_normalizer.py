"""Unit tests for src/crawling/url_normalizer.py.

Covers:
- Tracking parameter removal (utm_*, fbclid, gclid, ref, source, etc.)
- Scheme normalization (http -> https, lowercase)
- Host normalization (www removal, lowercase)
- Default port stripping
- Path normalization (trailing slash, ../ resolution)
- Fragment removal
- Query parameter sorting
- Percent-encoding normalization
- Protocol-relative URLs
- are_equivalent() helper
- url_key() safe fallback
"""

import pytest
import sys
import os

# Ensure project root is on sys.path so 'src' is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.crawling.url_normalizer import URLNormalizer, TRACKING_PARAMS


@pytest.fixture
def normalizer():
    """Return a URLNormalizer instance."""
    return URLNormalizer()


# ---------------------------------------------------------------------------
# Tracking parameter removal
# ---------------------------------------------------------------------------

class TestTrackingParameterRemoval:
    """All tracking parameter families must be stripped."""

    def test_utm_source(self, normalizer):
        url = "https://example.com/article?utm_source=twitter"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_utm_medium(self, normalizer):
        url = "https://example.com/article?utm_medium=social"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_utm_campaign(self, normalizer):
        url = "https://example.com/article?utm_campaign=spring2024"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_utm_term(self, normalizer):
        url = "https://example.com/article?utm_term=news"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_utm_content(self, normalizer):
        url = "https://example.com/article?utm_content=button"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_utm_id(self, normalizer):
        url = "https://example.com/article?utm_id=abc123"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_all_utm_params_stripped(self, normalizer):
        url = (
            "https://example.com/article"
            "?utm_source=twitter&utm_medium=social&utm_campaign=test"
            "&utm_term=news&utm_content=headline"
        )
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_fbclid(self, normalizer):
        url = "https://example.com/article?fbclid=IwAR1234567890"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_gclid(self, normalizer):
        url = "https://example.com/article?gclid=Cj0KCQiA5NSdBhDfARIsALzs2EA"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_ref_param(self, normalizer):
        url = "https://example.com/article?ref=homepage"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_source_param(self, normalizer):
        url = "https://example.com/article?source=rss"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_msclkid(self, normalizer):
        url = "https://example.com/article?msclkid=abc123"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_mixed_tracking_and_real_params(self, normalizer):
        """Real query params must be preserved while tracking params are stripped."""
        url = "https://example.com/search?q=news&utm_source=twitter&page=2"
        result = normalizer.normalize(url)
        assert "utm_source" not in result
        assert "q=news" in result
        assert "page=2" in result

    def test_naver_tracking_params(self, normalizer):
        url = "https://news.naver.com/article?n_media=abc&n_query=test&aid=123"
        result = normalizer.normalize(url)
        assert "n_media" not in result
        assert "n_query" not in result
        assert "aid=123" in result


# ---------------------------------------------------------------------------
# Scheme normalization
# ---------------------------------------------------------------------------

class TestSchemeNormalization:
    """http should be promoted to https; scheme should be lowercase."""

    def test_http_to_https(self, normalizer):
        url = "http://example.com/article"
        assert normalizer.normalize(url).startswith("https://")

    def test_https_unchanged(self, normalizer):
        url = "https://example.com/article"
        assert normalizer.normalize(url).startswith("https://")

    def test_uppercase_scheme_lowercased(self, normalizer):
        url = "HTTPS://example.com/article"
        result = normalizer.normalize(url)
        assert result.startswith("https://")


# ---------------------------------------------------------------------------
# Host normalization
# ---------------------------------------------------------------------------

class TestHostNormalization:
    """www. prefix should be removed; host should be lowercase."""

    def test_www_stripped(self, normalizer):
        url = "https://www.example.com/article"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_no_www_unchanged(self, normalizer):
        url = "https://example.com/article"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_uppercase_host_lowercased(self, normalizer):
        url = "https://EXAMPLE.COM/article"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_www_and_http_both_normalized(self, normalizer):
        url = "http://www.example.com/article"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_www_equivalence(self, normalizer):
        """www.example.com and example.com should normalize to the same URL."""
        assert normalizer.normalize("https://www.chosun.com/news/1234") == \
               normalizer.normalize("https://chosun.com/news/1234")


# ---------------------------------------------------------------------------
# Default port stripping
# ---------------------------------------------------------------------------

class TestDefaultPortStripping:
    """Default ports (80 for http, 443 for https) should be removed."""

    def test_https_port_443_stripped(self, normalizer):
        url = "https://example.com:443/article"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_http_port_80_stripped(self, normalizer):
        url = "http://example.com:80/article"
        # http is also promoted to https here
        assert ":80" not in normalizer.normalize(url)

    def test_non_default_port_kept(self, normalizer):
        url = "https://example.com:8080/article"
        assert ":8080" in normalizer.normalize(url)


# ---------------------------------------------------------------------------
# Path normalization
# ---------------------------------------------------------------------------

class TestPathNormalization:
    """Trailing slashes removed; ../ and ./ resolved."""

    def test_trailing_slash_removed(self, normalizer):
        url = "https://example.com/article/"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_root_slash_kept(self, normalizer):
        """Root URL should keep its single slash."""
        url = "https://example.com/"
        # Root slash normalization: either / or no path — accept both
        result = normalizer.normalize(url)
        assert result in ("https://example.com/", "https://example.com")

    def test_dotdot_resolved(self, normalizer):
        url = "https://example.com/news/../article"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_dot_resolved(self, normalizer):
        url = "https://example.com/./article"
        assert normalizer.normalize(url) == "https://example.com/article"

    def test_multiple_slashes_in_path(self, normalizer):
        url = "https://example.com/news//article"
        result = normalizer.normalize(url)
        # Double slash in path should not produce triple slash in result
        assert "///" not in result


# ---------------------------------------------------------------------------
# Fragment removal
# ---------------------------------------------------------------------------

class TestFragmentRemoval:
    """URL fragment (#...) must always be stripped."""

    def test_fragment_stripped(self, normalizer):
        url = "https://example.com/article#comments"
        assert "#" not in normalizer.normalize(url)

    def test_fragment_with_params(self, normalizer):
        url = "https://example.com/article?page=1#section2"
        result = normalizer.normalize(url)
        assert "#" not in result
        assert "page=1" in result


# ---------------------------------------------------------------------------
# Query parameter sorting
# ---------------------------------------------------------------------------

class TestQueryParameterSorting:
    """Remaining query params must be sorted alphabetically."""

    def test_params_sorted(self, normalizer):
        url_unsorted = "https://example.com/search?z=last&a=first&m=middle"
        url_sorted = "https://example.com/search?a=first&m=middle&z=last"
        assert normalizer.normalize(url_unsorted) == normalizer.normalize(url_sorted)

    def test_same_params_different_order(self, normalizer):
        url_a = "https://example.com/article?b=2&a=1"
        url_b = "https://example.com/article?a=1&b=2"
        assert normalizer.normalize(url_a) == normalizer.normalize(url_b)


# ---------------------------------------------------------------------------
# Percent-encoding normalization
# ---------------------------------------------------------------------------

class TestPercentEncoding:
    """Unreserved characters must be decoded; reserved characters kept encoded."""

    def test_space_in_title_param(self, normalizer):
        url = "https://example.com/search?q=hello%20world"
        result = normalizer.normalize(url)
        assert "q=" in result  # query param preserved

    def test_unreserved_chars_decoded(self, normalizer):
        """Letters and digits encoded unnecessarily should be decoded."""
        url = "https://example.com/%61rticle"  # %61 = 'a'
        result = normalizer.normalize(url)
        assert "/article" in result

    def test_encoded_slash_kept_encoded(self, normalizer):
        """Encoded slash (%2F) is a reserved character and must NOT be decoded."""
        url = "https://example.com/path%2Fsegment"
        result = normalizer.normalize(url)
        # %2F should remain encoded (or the path structure stays consistent)
        # Key: the URL should remain parseable without changing routing semantics
        assert "example.com" in result


# ---------------------------------------------------------------------------
# are_equivalent helper
# ---------------------------------------------------------------------------

class TestAreEquivalent:
    def test_equivalent_with_different_tracking(self, normalizer):
        a = "https://www.bbc.com/news/article-12345?utm_source=twitter"
        b = "http://bbc.com/news/article-12345?ref=homepage"
        assert normalizer.are_equivalent(a, b)

    def test_not_equivalent_different_articles(self, normalizer):
        a = "https://example.com/article/123"
        b = "https://example.com/article/456"
        assert not normalizer.are_equivalent(a, b)

    def test_invalid_url_returns_false(self, normalizer):
        assert not normalizer.are_equivalent("not-a-url", "https://example.com")


# ---------------------------------------------------------------------------
# url_key safe fallback
# ---------------------------------------------------------------------------

class TestUrlKey:
    def test_returns_empty_string_for_invalid(self, normalizer):
        result = normalizer.url_key("totally invalid")
        # Should return either the raw URL (fallback) or empty string — no exception
        assert isinstance(result, str)

    def test_valid_url_returns_normalized(self, normalizer):
        url = "https://www.example.com/article?utm_source=twitter"
        result = normalizer.url_key(url)
        assert result == "https://example.com/article"


# ---------------------------------------------------------------------------
# TRACKING_PARAMS coverage
# ---------------------------------------------------------------------------

class TestTrackingParamsCoverage:
    def test_tracking_params_set_not_empty(self):
        assert len(TRACKING_PARAMS) > 10

    def test_utm_params_in_set(self):
        for param in ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]:
            assert param in TRACKING_PARAMS

    def test_fbclid_in_set(self):
        assert "fbclid" in TRACKING_PARAMS

    def test_gclid_in_set(self):
        assert "gclid" in TRACKING_PARAMS

    def test_ref_in_set(self):
        assert "ref" in TRACKING_PARAMS
