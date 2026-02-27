"""Tests for block_detector.py — 7-Type Block Diagnosis Engine.

Verifies that all 7 block types are correctly detected with appropriate
confidence scores, and that legitimate responses are not misclassified.

Test categories:
    - Per-type detection: Each of the 7 block types has dedicated tests.
    - False positive prevention: Legitimate errors are not misclassified.
    - Confidence scoring: Confidence values are within [0, 1].
    - Sorting/priority: Higher confidence diagnoses come first.
    - Edge cases: Empty bodies, minimal responses, unusual headers.
"""

import pytest

from src.crawling.block_detector import (
    BlockDetector,
    BlockDiagnosis,
    BlockType,
    HttpResponse,
    CAPTCHADetector,
    FingerprintDetector,
    GeoBlockDetector,
    IPBlockDetector,
    JSChallengeDetector,
    RateLimitDetector,
    UAFilterDetector,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def detector() -> BlockDetector:
    """Default BlockDetector with all 7 detectors and default threshold."""
    return BlockDetector()


def _make_response(
    status_code: int = 200,
    headers: dict | None = None,
    body: str = "",
    url: str = "https://example.com/article",
    original_url: str = "",
) -> HttpResponse:
    """Helper to create HttpResponse objects for testing."""
    return HttpResponse(
        status_code=status_code,
        headers=headers or {},
        body=body,
        url=url,
        original_url=original_url or url,
    )


# =============================================================================
# 1. IP Block Detection
# =============================================================================

class TestIPBlockDetector:
    """Tests for IP-based block detection."""

    def test_403_forbidden(self, detector: BlockDetector) -> None:
        """HTTP 403 should trigger IP block detection."""
        resp = _make_response(status_code=403, body="<h1>Forbidden</h1>")
        diagnoses = detector.diagnose(resp)
        assert any(d.block_type == BlockType.IP_BLOCK for d in diagnoses)

    def test_403_with_access_denied_body(self, detector: BlockDetector) -> None:
        """403 with 'access denied' in body should have high confidence."""
        resp = _make_response(
            status_code=403,
            body="<html><body><h1>Access Denied</h1><p>Your IP has been blocked.</p></body></html>",
        )
        diagnoses = detector.diagnose(resp)
        ip_diag = [d for d in diagnoses if d.block_type == BlockType.IP_BLOCK]
        assert len(ip_diag) >= 1
        assert ip_diag[0].confidence >= 0.5

    def test_waf_header(self, detector: BlockDetector) -> None:
        """AWS WAF block header should be detected."""
        resp = _make_response(
            status_code=403,
            headers={"x-amzn-waf-action": "block"},
            body="Request blocked",
        )
        diagnoses = detector.diagnose(resp)
        ip_diag = [d for d in diagnoses if d.block_type == BlockType.IP_BLOCK]
        assert len(ip_diag) >= 1

    def test_200_ok_is_not_ip_block(self, detector: BlockDetector) -> None:
        """Normal 200 response should not trigger IP block."""
        resp = _make_response(
            status_code=200,
            body="<html><body><h1>News Article</h1><p>Content here.</p></body></html>",
        )
        diagnoses = detector.diagnose(resp)
        ip_diag = [d for d in diagnoses if d.block_type == BlockType.IP_BLOCK]
        assert len(ip_diag) == 0

    def test_recommended_tier_for_ip_block(self, detector: BlockDetector) -> None:
        """IP blocks should recommend Tier 5 (proxy rotation)."""
        resp = _make_response(status_code=403, body="Access Denied")
        diagnoses = detector.diagnose(resp)
        ip_diag = [d for d in diagnoses if d.block_type == BlockType.IP_BLOCK]
        if ip_diag:
            assert ip_diag[0].recommended_tier == 5


# =============================================================================
# 2. UA Filter Detection
# =============================================================================

class TestUAFilterDetector:
    """Tests for User-Agent filtering detection."""

    def test_406_not_acceptable(self, detector: BlockDetector) -> None:
        """HTTP 406 should trigger UA filter detection."""
        resp = _make_response(status_code=406, body="Not Acceptable")
        diagnoses = detector.diagnose(resp)
        ua_diag = [d for d in diagnoses if d.block_type == BlockType.UA_FILTER]
        assert len(ua_diag) >= 1

    def test_redirect_to_bot_check(self, detector: BlockDetector) -> None:
        """Redirect to a bot-check URL should be detected."""
        resp = _make_response(
            status_code=200,
            body="<html>Please verify you are human</html>",
            url="https://example.com/bot-check",
            original_url="https://example.com/article",
        )
        diagnoses = detector.diagnose(resp)
        ua_diag = [d for d in diagnoses if d.block_type == BlockType.UA_FILTER]
        assert len(ua_diag) >= 1

    def test_bot_detected_in_body(self, detector: BlockDetector) -> None:
        """'bot detected' in body should trigger UA filter."""
        resp = _make_response(
            status_code=200,
            body="<html><body>Bot detected. Please use a modern browser.</body></html>",
        )
        diagnoses = detector.diagnose(resp)
        ua_diag = [d for d in diagnoses if d.block_type == BlockType.UA_FILTER]
        assert len(ua_diag) >= 1


# =============================================================================
# 3. Rate Limit Detection
# =============================================================================

class TestRateLimitDetector:
    """Tests for rate limit detection."""

    def test_429_status(self, detector: BlockDetector) -> None:
        """HTTP 429 should trigger rate limit detection with high confidence."""
        resp = _make_response(status_code=429, body="Too Many Requests")
        diagnoses = detector.diagnose(resp)
        rl_diag = [d for d in diagnoses if d.block_type == BlockType.RATE_LIMIT]
        assert len(rl_diag) >= 1
        assert rl_diag[0].confidence >= 0.7

    def test_retry_after_header(self, detector: BlockDetector) -> None:
        """Retry-After header should be detected as evidence."""
        resp = _make_response(
            status_code=429,
            headers={"Retry-After": "60"},
            body="Rate limited",
        )
        diagnoses = detector.diagnose(resp)
        rl_diag = [d for d in diagnoses if d.block_type == BlockType.RATE_LIMIT]
        assert len(rl_diag) >= 1
        assert any("Retry-After" in e for e in rl_diag[0].evidence)

    def test_ratelimit_remaining_zero(self, detector: BlockDetector) -> None:
        """x-ratelimit-remaining: 0 should be detected."""
        resp = _make_response(
            status_code=200,
            headers={"x-ratelimit-remaining": "0"},
            body="<html>Normal page</html>",
        )
        diagnoses = detector.diagnose(resp)
        rl_diag = [d for d in diagnoses if d.block_type == BlockType.RATE_LIMIT]
        assert len(rl_diag) >= 1

    def test_503_with_rate_limit_language(self, detector: BlockDetector) -> None:
        """503 with rate limit language should be detected."""
        resp = _make_response(
            status_code=503,
            body="Service temporarily unavailable. Rate limit exceeded.",
        )
        diagnoses = detector.diagnose(resp)
        rl_diag = [d for d in diagnoses if d.block_type == BlockType.RATE_LIMIT]
        assert len(rl_diag) >= 1

    def test_recommended_tier_for_rate_limit(self, detector: BlockDetector) -> None:
        """Rate limits should recommend Tier 1 (delay adjustment)."""
        resp = _make_response(status_code=429, body="Too Many Requests")
        diagnoses = detector.diagnose(resp)
        rl_diag = [d for d in diagnoses if d.block_type == BlockType.RATE_LIMIT]
        if rl_diag:
            assert rl_diag[0].recommended_tier == 1


# =============================================================================
# 4. CAPTCHA Detection
# =============================================================================

class TestCAPTCHADetector:
    """Tests for CAPTCHA challenge detection."""

    def test_recaptcha_script(self, detector: BlockDetector) -> None:
        """reCAPTCHA script source should be detected."""
        resp = _make_response(
            status_code=200,
            body='<html><script src="https://www.google.com/recaptcha/api.js"></script></html>',
        )
        diagnoses = detector.diagnose(resp)
        cap_diag = [d for d in diagnoses if d.block_type == BlockType.CAPTCHA]
        assert len(cap_diag) >= 1

    def test_hcaptcha_dom(self, detector: BlockDetector) -> None:
        """hCaptcha DOM element should be detected."""
        resp = _make_response(
            status_code=200,
            body='<html><div class="h-captcha" data-sitekey="xxx"></div></html>',
        )
        diagnoses = detector.diagnose(resp)
        cap_diag = [d for d in diagnoses if d.block_type == BlockType.CAPTCHA]
        assert len(cap_diag) >= 1

    def test_cloudflare_turnstile(self, detector: BlockDetector) -> None:
        """Cloudflare Turnstile should be detected."""
        resp = _make_response(
            status_code=200,
            body='<html><script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script></html>',
        )
        diagnoses = detector.diagnose(resp)
        cap_diag = [d for d in diagnoses if d.block_type == BlockType.CAPTCHA]
        assert len(cap_diag) >= 1

    def test_captcha_title(self, detector: BlockDetector) -> None:
        """Page title containing 'captcha' should be detected."""
        resp = _make_response(
            status_code=200,
            body="<html><head><title>CAPTCHA Verification Required</title></head><body></body></html>",
        )
        diagnoses = detector.diagnose(resp)
        cap_diag = [d for d in diagnoses if d.block_type == BlockType.CAPTCHA]
        assert len(cap_diag) >= 1

    def test_normal_page_not_captcha(self, detector: BlockDetector) -> None:
        """Normal news article should not be detected as CAPTCHA."""
        resp = _make_response(
            status_code=200,
            body=(
                "<html><head><title>Breaking News</title></head>"
                "<body><h1>News Article</h1><p>Content about current events.</p></body></html>"
            ),
        )
        diagnoses = detector.diagnose(resp)
        cap_diag = [d for d in diagnoses if d.block_type == BlockType.CAPTCHA]
        assert len(cap_diag) == 0


# =============================================================================
# 5. JS Challenge Detection
# =============================================================================

class TestJSChallengeDetector:
    """Tests for JavaScript challenge detection."""

    def test_cloudflare_503(self, detector: BlockDetector) -> None:
        """Cloudflare 503 with server header should be detected."""
        resp = _make_response(
            status_code=503,
            headers={"server": "cloudflare", "cf-ray": "abc123"},
            body='<html><body>Please wait while we verify your browser...</body></html>',
        )
        diagnoses = detector.diagnose(resp)
        js_diag = [d for d in diagnoses if d.block_type == BlockType.JS_CHALLENGE]
        assert len(js_diag) >= 1
        assert js_diag[0].confidence >= 0.5

    def test_js_redirect_small_body(self, detector: BlockDetector) -> None:
        """Small body with JS redirect should be detected."""
        resp = _make_response(
            status_code=200,
            body='<html><script>window.location="https://example.com/verify";</script></html>',
        )
        diagnoses = detector.diagnose(resp)
        js_diag = [d for d in diagnoses if d.block_type == BlockType.JS_CHALLENGE]
        assert len(js_diag) >= 1

    def test_cloudflare_challenge_variables(self, detector: BlockDetector) -> None:
        """Cloudflare challenge JavaScript variables should be detected."""
        resp = _make_response(
            status_code=503,
            body='<html><script>var _cf_chl_opt = {cvId: "2", cType: "managed"};</script></html>',
        )
        diagnoses = detector.diagnose(resp)
        js_diag = [d for d in diagnoses if d.block_type == BlockType.JS_CHALLENGE]
        assert len(js_diag) >= 1

    def test_empty_body_200(self, detector: BlockDetector) -> None:
        """HTTP 200 with near-empty body may indicate JS-only page."""
        resp = _make_response(status_code=200, body="   ")
        diagnoses = detector.diagnose(resp)
        js_diag = [d for d in diagnoses if d.block_type == BlockType.JS_CHALLENGE]
        assert len(js_diag) >= 1


# =============================================================================
# 6. Fingerprint Detection
# =============================================================================

class TestFingerprintDetector:
    """Tests for TLS/browser fingerprint rejection detection."""

    def test_kasada_header(self, detector: BlockDetector) -> None:
        """Kasada anti-bot header should be detected."""
        resp = _make_response(
            status_code=403,
            headers={"x-kpsdk-ct": "some-token"},
            body="Blocked",
        )
        diagnoses = detector.diagnose(resp)
        fp_diag = [d for d in diagnoses if d.block_type == BlockType.FINGERPRINT]
        assert len(fp_diag) >= 1

    def test_perimeterx_header(self, detector: BlockDetector) -> None:
        """PerimeterX header should be detected."""
        resp = _make_response(
            status_code=403,
            headers={"x-px": "1"},
            body="Forbidden",
        )
        diagnoses = detector.diagnose(resp)
        fp_diag = [d for d in diagnoses if d.block_type == BlockType.FINGERPRINT]
        assert len(fp_diag) >= 1

    def test_datadome_cookie(self, detector: BlockDetector) -> None:
        """DataDome cookie should be detected."""
        resp = _make_response(
            status_code=200,
            headers={"set-cookie": "datadome=abc123; path=/; domain=.example.com"},
            body="<html>Page content</html>",
        )
        diagnoses = detector.diagnose(resp)
        fp_diag = [d for d in diagnoses if d.block_type == BlockType.FINGERPRINT]
        assert len(fp_diag) >= 1


# =============================================================================
# 7. Geo-Block Detection
# =============================================================================

class TestGeoBlockDetector:
    """Tests for geographic restriction detection."""

    def test_not_available_in_region(self, detector: BlockDetector) -> None:
        """'Not available in your region' should be detected."""
        resp = _make_response(
            status_code=200,
            body="<html><body>Sorry, this content is not available in your region.</body></html>",
        )
        diagnoses = detector.diagnose(resp)
        geo_diag = [d for d in diagnoses if d.block_type == BlockType.GEO_BLOCK]
        assert len(geo_diag) >= 1

    def test_redirect_to_regional_domain(self, detector: BlockDetector) -> None:
        """Redirect to a regional domain variant should be detected."""
        resp = _make_response(
            status_code=200,
            body="<html>Redirected</html>",
            url="https://cn.example.com/article",
            original_url="https://example.com/article",
        )
        diagnoses = detector.diagnose(resp)
        geo_diag = [d for d in diagnoses if d.block_type == BlockType.GEO_BLOCK]
        assert len(geo_diag) >= 1

    def test_451_unavailable(self, detector: BlockDetector) -> None:
        """HTTP 451 should be detected as potential geo-block."""
        resp = _make_response(
            status_code=451,
            body="<html>Unavailable for legal reasons</html>",
        )
        diagnoses = detector.diagnose(resp)
        geo_diag = [d for d in diagnoses if d.block_type == BlockType.GEO_BLOCK]
        assert len(geo_diag) >= 1

    def test_same_domain_redirect_not_geo(self, detector: BlockDetector) -> None:
        """Redirect within the same domain should not trigger geo-block."""
        resp = _make_response(
            status_code=200,
            body="<html>Article content here</html>",
            url="https://example.com/en/article",
            original_url="https://example.com/article",
        )
        diagnoses = detector.diagnose(resp)
        geo_diag = [d for d in diagnoses if d.block_type == BlockType.GEO_BLOCK]
        assert len(geo_diag) == 0


# =============================================================================
# Cross-Cutting Tests
# =============================================================================

class TestBlockDetectorCrossCutting:
    """Tests for cross-cutting behavior of the BlockDetector."""

    def test_normal_200_no_blocks(self, detector: BlockDetector) -> None:
        """A normal 200 response with real content should produce zero diagnoses."""
        resp = _make_response(
            status_code=200,
            body=(
                "<html><head><title>News</title></head>"
                "<body><article><h1>Article Title</h1>"
                "<p>This is a real news article with substantial content "
                "about current world events and political developments.</p>"
                "</article></body></html>"
            ),
        )
        diagnoses = detector.diagnose(resp)
        assert len(diagnoses) == 0

    def test_server_error_not_block(self, detector: BlockDetector) -> None:
        """HTTP 500 Internal Server Error is NOT a block (it is a server bug)."""
        resp = _make_response(
            status_code=500,
            body="<html><body>Internal Server Error</body></html>",
        )
        diagnoses = detector.diagnose(resp)
        # 500 should not be classified as any block type
        # (500 is in RETRY_STATUS_CODES but not a blocking signal)
        assert len(diagnoses) == 0

    def test_404_not_block(self, detector: BlockDetector) -> None:
        """HTTP 404 Not Found is NOT a block (it is a missing page)."""
        resp = _make_response(
            status_code=404,
            body="<html><body>Page not found</body></html>",
        )
        diagnoses = detector.diagnose(resp)
        assert len(diagnoses) == 0

    def test_confidence_within_bounds(self, detector: BlockDetector) -> None:
        """All diagnosis confidence values should be within [0.0, 1.0]."""
        resp = _make_response(
            status_code=403,
            headers={"x-amzn-waf-action": "block", "cf-ray": "test"},
            body="Access Denied. Your IP has been blocked. CAPTCHA required.",
        )
        diagnoses = detector.diagnose(resp)
        for d in diagnoses:
            assert 0.0 <= d.confidence <= 1.0, f"Confidence out of range: {d.confidence}"

    def test_diagnoses_sorted_by_confidence(self, detector: BlockDetector) -> None:
        """Diagnoses should be sorted by confidence, highest first."""
        resp = _make_response(
            status_code=429,
            headers={"Retry-After": "30"},
            body="Too Many Requests. Access Denied.",
        )
        diagnoses = detector.diagnose(resp)
        if len(diagnoses) >= 2:
            for i in range(len(diagnoses) - 1):
                assert diagnoses[i].confidence >= diagnoses[i + 1].confidence

    def test_is_blocked_convenience(self, detector: BlockDetector) -> None:
        """is_blocked() should return True for blocked responses."""
        blocked = _make_response(status_code=429, body="Too Many Requests")
        normal = _make_response(
            status_code=200,
            body="<html><body><article><h1>Real news</h1><p>Article content here.</p></article></body></html>",
        )
        assert detector.is_blocked(blocked) is True
        assert detector.is_blocked(normal) is False

    def test_primary_diagnosis(self, detector: BlockDetector) -> None:
        """primary_diagnosis() should return highest confidence or None."""
        blocked = _make_response(status_code=429, body="Too Many Requests")
        normal = _make_response(
            status_code=200,
            body="<html><body><article><h1>Real news</h1><p>Article content here.</p></article></body></html>",
        )
        assert detector.primary_diagnosis(blocked) is not None
        assert detector.primary_diagnosis(normal) is None

    def test_custom_confidence_threshold(self) -> None:
        """Custom confidence threshold should filter low-confidence diagnoses."""
        strict = BlockDetector(confidence_threshold=0.9)
        resp = _make_response(status_code=403, body="Forbidden")
        diagnoses = strict.diagnose(resp)
        for d in diagnoses:
            assert d.confidence >= 0.9

    def test_http_response_header_case_insensitive(self) -> None:
        """HttpResponse.header() should be case-insensitive."""
        resp = HttpResponse(
            status_code=200,
            headers={"Content-Type": "text/html", "X-Custom": "value"},
        )
        assert resp.header("content-type") == "text/html"
        assert resp.header("CONTENT-TYPE") == "text/html"
        assert resp.header("x-custom") == "value"
        assert resp.header("missing", "default") == "default"

    def test_block_diagnosis_validation(self) -> None:
        """BlockDiagnosis should validate confidence and tier bounds."""
        with pytest.raises(ValueError, match="Confidence"):
            BlockDiagnosis(block_type=BlockType.IP_BLOCK, confidence=1.5)
        with pytest.raises(ValueError, match="tier"):
            BlockDiagnosis(block_type=BlockType.IP_BLOCK, confidence=0.5, recommended_tier=7)

    def test_detector_exception_safety(self) -> None:
        """Detector pipeline should not crash even if a detector raises."""

        class BrokenDetector:
            block_type = BlockType.IP_BLOCK
            def detect(self, response: HttpResponse) -> None:
                raise RuntimeError("Intentional test failure")

        detector = BlockDetector(detectors=[BrokenDetector(), RateLimitDetector()])
        resp = _make_response(status_code=429, body="Too Many Requests")
        # Should not raise; broken detector is skipped
        diagnoses = detector.diagnose(resp)
        assert len(diagnoses) >= 1
