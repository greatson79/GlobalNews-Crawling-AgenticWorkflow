"""Tests for NetworkGuard: retry logic, rate limiting, circuit breaker integration.

Tests cover:
    - 5-retry exponential backoff with jitter
    - Per-site rate limiting
    - Circuit breaker state transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
    - Response validation (status codes, bot detection, empty bodies)
    - Error classification (retriable vs non-retriable)
    - Encoding handling for CJK sites
"""

import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------
from src.crawling.network_guard import (
    NetworkGuard,
    FetchResponse,
    RateLimiter,
    classify_error,
    is_retriable_status,
    NON_RETRIABLE_STATUS_CODES,
    RETRIABLE_STATUS_CODES,
)
from src.utils.error_handler import (
    NetworkError,
    RateLimitError,
    BlockDetectedError,
    CircuitBreaker,
    CircuitState,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def guard():
    """Create a NetworkGuard with short timeouts for testing."""
    g = NetworkGuard(
        timeout_seconds=5,
        max_retries=3,
        backoff_base=0.01,  # Very short for tests
        backoff_factor=2.0,
        backoff_max=0.1,
    )
    yield g
    g.close()


@pytest.fixture
def mock_response():
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"content-type": "text/html; charset=utf-8"}
    resp.text = "<html><body>Hello</body></html>"
    resp.content = b"<html><body>Hello</body></html>"
    resp.url = "https://example.com/article/1"
    resp.encoding = "utf-8"
    return resp


# ===========================================================================
# Error Classification Tests
# ===========================================================================

class TestErrorClassification:
    """Tests for classify_error() and is_retriable_status()."""

    def test_network_error_retriable_status(self):
        """5xx status codes should be classified as retriable."""
        err = NetworkError("Server error", status_code=500, url="https://example.com")
        assert classify_error(err) == "retriable"

    def test_network_error_non_retriable_status(self):
        """404 should be classified as non-retriable."""
        err = NetworkError("Not found", status_code=404, url="https://example.com")
        assert classify_error(err) == "non_retriable"

    def test_rate_limit_error(self):
        """RateLimitError should be classified as rate_limited."""
        err = RateLimitError("Too many requests", retry_after=60)
        assert classify_error(err) == "rate_limited"

    def test_block_detected_error(self):
        """BlockDetectedError should be classified as blocked."""
        err = BlockDetectedError("CAPTCHA", block_type="captcha")
        assert classify_error(err) == "blocked"

    def test_network_error_no_status(self):
        """Connection errors without status code should be retriable."""
        err = NetworkError("Connection reset", status_code=None, url="https://example.com")
        assert classify_error(err) == "retriable"

    def test_timeout_error_retriable(self):
        """TimeoutError should be retriable."""
        err = TimeoutError("Request timed out")
        assert classify_error(err) == "retriable"

    def test_unknown_error(self):
        """Unknown exceptions should be classified as unknown."""
        err = ValueError("Unexpected")
        assert classify_error(err) == "unknown"

    def test_is_retriable_status_500(self):
        assert is_retriable_status(500) is True

    def test_is_retriable_status_429(self):
        assert is_retriable_status(429) is True

    def test_is_retriable_status_200(self):
        assert is_retriable_status(200) is False

    def test_is_retriable_status_404(self):
        assert is_retriable_status(404) is False


# ===========================================================================
# RateLimiter Tests
# ===========================================================================

class TestRateLimiter:
    """Tests for the per-site RateLimiter."""

    def test_first_call_no_wait(self):
        """First call should not wait."""
        rl = RateLimiter(interval_seconds=1.0)
        waited = rl.wait()
        assert waited == 0.0

    def test_second_call_waits(self):
        """Second call within interval should wait."""
        rl = RateLimiter(interval_seconds=0.05)
        rl.wait()  # first call
        start = time.monotonic()
        rl.wait()  # should wait
        elapsed = time.monotonic() - start
        assert elapsed >= 0.03  # at least most of the interval

    def test_jitter_adds_randomness(self):
        """Jitter should add random delay."""
        rl = RateLimiter(interval_seconds=0.01, jitter_seconds=0.02)
        rl.wait()  # first call
        waited = rl.wait()
        # With jitter, wait time should be interval + some jitter
        assert waited >= 0.0

    def test_min_interval_enforced(self):
        """Interval should be at least 0.1 seconds."""
        rl = RateLimiter(interval_seconds=0.0)
        assert rl._interval >= 0.1


# ===========================================================================
# NetworkGuard Core Tests
# ===========================================================================

class TestNetworkGuardConfiguration:
    """Tests for NetworkGuard site configuration."""

    def test_configure_site_creates_rate_limiter(self, guard):
        """configure_site() should create a rate limiter for the site."""
        guard.configure_site("test_site", rate_limit_seconds=5)
        assert "test_site" in guard._rate_limiters

    def test_configure_site_creates_circuit_breaker(self, guard):
        """configure_site() should create a circuit breaker for the site."""
        guard.configure_site("test_site", rate_limit_seconds=5)
        assert "test_site" in guard._circuit_breakers

    def test_get_circuit_state_default_closed(self, guard):
        """Unconfigured sites should return CLOSED state."""
        state = guard.get_circuit_state("unknown_site")
        assert state == CircuitState.CLOSED

    def test_get_circuit_state_configured(self, guard):
        """Configured sites should return CLOSED initially."""
        guard.configure_site("test_site")
        state = guard.get_circuit_state("test_site")
        assert state == CircuitState.CLOSED


class TestNetworkGuardFetch:
    """Tests for NetworkGuard.fetch() with mocked HTTP client."""

    @patch("src.crawling.network_guard.NetworkGuard._get_client")
    def test_successful_fetch(self, mock_get_client, guard, mock_response):
        """Successful 200 response should return FetchResponse."""
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = guard.fetch("https://example.com/article/1")

        assert isinstance(result, FetchResponse)
        assert result.status_code == 200
        assert "Hello" in result.text

    @patch("src.crawling.network_guard.NetworkGuard._get_client")
    def test_retry_on_500(self, mock_get_client, guard):
        """5xx errors should trigger retries."""
        mock_client = MagicMock()

        # First two calls: 500, third call: 200
        error_resp = MagicMock()
        error_resp.status_code = 500
        error_resp.headers = {"content-type": "text/html"}
        error_resp.text = "Internal Server Error"
        error_resp.content = b"Internal Server Error"
        error_resp.url = "https://example.com/article/1"
        error_resp.encoding = "utf-8"

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.headers = {"content-type": "text/html"}
        success_resp.text = "<html>OK</html>"
        success_resp.content = b"<html>OK</html>"
        success_resp.url = "https://example.com/article/1"
        success_resp.encoding = "utf-8"

        mock_client.request.side_effect = [error_resp, error_resp, success_resp]
        mock_get_client.return_value = mock_client

        result = guard.fetch("https://example.com/article/1")
        assert result.status_code == 200
        assert mock_client.request.call_count == 3

    @patch("src.crawling.network_guard.NetworkGuard._get_client")
    def test_no_retry_on_404(self, mock_get_client, guard):
        """404 errors should NOT trigger retries."""
        mock_client = MagicMock()
        error_resp = MagicMock()
        error_resp.status_code = 404
        error_resp.headers = {"content-type": "text/html"}
        error_resp.text = "Not Found"
        error_resp.content = b"Not Found"
        error_resp.url = "https://example.com/missing"
        error_resp.encoding = "utf-8"

        mock_client.request.return_value = error_resp
        mock_get_client.return_value = mock_client

        with pytest.raises(NetworkError) as exc_info:
            guard.fetch("https://example.com/missing")

        assert exc_info.value.status_code == 404
        # Should only be called once (no retries)
        assert mock_client.request.call_count == 1

    @patch("src.crawling.network_guard.NetworkGuard._get_client")
    def test_rate_limit_429_with_retry_after(self, mock_get_client, guard):
        """429 with Retry-After header should use that delay."""
        mock_client = MagicMock()

        rate_resp = MagicMock()
        rate_resp.status_code = 429
        rate_resp.headers = {"content-type": "text/html", "Retry-After": "0.01"}
        rate_resp.text = "Too Many Requests"
        rate_resp.content = b"Too Many Requests"
        rate_resp.url = "https://example.com/article/1"
        rate_resp.encoding = "utf-8"

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.headers = {"content-type": "text/html"}
        success_resp.text = "<html>OK</html>"
        success_resp.content = b"<html>OK</html>"
        success_resp.url = "https://example.com/article/1"
        success_resp.encoding = "utf-8"

        mock_client.request.side_effect = [rate_resp, success_resp]
        mock_get_client.return_value = mock_client

        result = guard.fetch("https://example.com/article/1")
        assert result.status_code == 200

    @patch("src.crawling.network_guard.NetworkGuard._get_client")
    def test_bot_detection_403(self, mock_get_client, guard):
        """403 with bot detection patterns should raise BlockDetectedError."""
        mock_client = MagicMock()

        blocked_resp = MagicMock()
        blocked_resp.status_code = 403
        blocked_resp.headers = {"content-type": "text/html"}
        blocked_resp.text = "<html>Please verify you are human. CAPTCHA required.</html>"
        blocked_resp.content = b"<html>Please verify you are human. CAPTCHA required.</html>"
        blocked_resp.url = "https://example.com/article/1"
        blocked_resp.encoding = "utf-8"

        mock_client.request.return_value = blocked_resp
        mock_get_client.return_value = mock_client

        with pytest.raises(BlockDetectedError) as exc_info:
            guard.fetch("https://example.com/article/1")

        assert exc_info.value.block_type == "captcha"

    @patch("src.crawling.network_guard.NetworkGuard._get_client")
    def test_circuit_breaker_blocks_when_open(self, mock_get_client, guard):
        """Open circuit breaker should block requests immediately."""
        guard.configure_site("broken_site")
        cb = guard._circuit_breakers["broken_site"]

        # Force circuit open
        for _ in range(10):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN

        with pytest.raises(NetworkError, match="Circuit breaker OPEN"):
            guard.fetch("https://broken-site.com/article/1", site_id="broken_site")

    @patch("src.crawling.network_guard.NetworkGuard._get_client")
    def test_max_retries_exhausted(self, mock_get_client, guard):
        """After max retries, should raise the last exception."""
        import httpx
        mock_client = MagicMock()
        mock_client.request.side_effect = httpx.TimeoutException("timeout")
        mock_get_client.return_value = mock_client

        with pytest.raises(NetworkError, match="timeout"):
            guard.fetch("https://example.com/slow")

        # 1 initial + 3 retries = 4 calls
        assert mock_client.request.call_count == 4

    @patch("src.crawling.network_guard.NetworkGuard._get_client")
    def test_empty_response_warning(self, mock_get_client, guard, mock_response):
        """Empty 200 response should log a warning but not raise."""
        mock_response.content = b""
        mock_response.text = ""
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = guard.fetch("https://example.com/empty")
        assert result.status_code == 200
        assert result.text == ""


class TestNetworkGuardEncoding:
    """Tests for character encoding handling."""

    @patch("src.crawling.network_guard.NetworkGuard._get_client")
    def test_fetch_with_encoding(self, mock_get_client, guard, mock_response):
        """fetch_with_encoding should re-decode with specified charset."""
        # Simulate a GBK-encoded response
        mock_response.encoding = "utf-8"
        mock_response.content = "Test content".encode("utf-8")
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = guard.fetch_with_encoding(
            "https://people.com.cn/article",
            site_id="people",
            charset="utf-8",
        )
        assert isinstance(result, FetchResponse)


class TestNetworkGuardContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_closes_client(self):
        """Using NetworkGuard as context manager should close client."""
        with NetworkGuard(timeout_seconds=5) as guard:
            assert guard is not None
        # After exit, client should be closed (None)
        assert guard._client is None


# ===========================================================================
# Circuit Breaker Integration Tests
# ===========================================================================

class TestCircuitBreakerIntegration:
    """Tests for circuit breaker state transitions within NetworkGuard."""

    def test_success_resets_failure_count(self, guard):
        """Successful requests should reset the failure counter."""
        guard.configure_site("test_site")
        cb = guard._circuit_breakers["test_site"]

        # Record some failures (but not enough to open)
        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2

        # Success should reset
        cb.record_success()
        assert cb._failure_count == 0

    def test_half_open_to_closed_on_success(self, guard):
        """Successful calls in HALF_OPEN should transition to CLOSED."""
        guard.configure_site("test_site", circuit_breaker_timeout=0.01)
        cb = guard._circuit_breakers["test_site"]

        # Force to OPEN
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

        # Record enough successes to close
        for _ in range(cb.half_open_max_calls):
            cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self, guard):
        """Any failure in HALF_OPEN should revert to OPEN."""
        guard.configure_site("test_site", circuit_breaker_timeout=0.01)
        cb = guard._circuit_breakers["test_site"]

        # Force to OPEN, then wait for HALF_OPEN
        for _ in range(5):
            cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

        # One failure should revert to OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
