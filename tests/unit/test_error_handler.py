"""Tests for src.utils.error_handler -- retry decorator and Circuit Breaker."""

import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.error_handler import (
    GlobalNewsError,
    CrawlError,
    NetworkError,
    RateLimitError,
    BlockDetectedError,
    ParseError,
    PipelineStageError,
    retry_with_backoff,
    CircuitBreaker,
    CircuitState,
)


class TestExceptionHierarchy:
    """Test the custom exception hierarchy."""

    def test_crawl_error_is_global_news_error(self):
        """CrawlError should be a subclass of GlobalNewsError."""
        assert issubclass(CrawlError, GlobalNewsError)

    def test_network_error_has_status_code(self):
        """NetworkError should store status_code and url."""
        err = NetworkError("timeout", status_code=504, url="https://example.com")
        assert err.status_code == 504
        assert err.url == "https://example.com"
        assert err.context["status_code"] == 504

    def test_rate_limit_error_has_retry_after(self):
        """RateLimitError should store retry_after."""
        err = RateLimitError("too many requests", retry_after=30.0, site_id="chosun")
        assert err.retry_after == 30.0
        assert err.site_id == "chosun"

    def test_pipeline_stage_error_has_stage_info(self):
        """PipelineStageError should store stage name and number."""
        err = PipelineStageError("OOM", stage_name="stage_2_features", stage_number=2)
        assert err.stage_name == "stage_2_features"
        assert err.stage_number == 2


class TestRetryDecorator:
    """Test the retry_with_backoff decorator."""

    def test_no_retry_on_success(self):
        """Successful calls should not be retried."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        def succeeds():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeeds()
        assert result == "ok"
        assert call_count == 1

    @patch("src.utils.error_handler.time.sleep")
    def test_retries_on_network_error(self, mock_sleep):
        """Should retry on NetworkError up to max_retries."""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_seconds=0.01, max_seconds=0.05)
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("timeout", status_code=503)
            return "recovered"

        result = fails_then_succeeds()
        assert result == "recovered"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch("src.utils.error_handler.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep):
        """Should raise after exhausting max_retries."""

        @retry_with_backoff(max_retries=2, base_seconds=0.01, max_seconds=0.05)
        def always_fails():
            raise NetworkError("timeout", status_code=503)

        with pytest.raises(NetworkError):
            always_fails()

    def test_no_retry_on_non_retryable_status(self):
        """Should not retry on status codes not in retryable set (e.g., 404)."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        def fails_404():
            nonlocal call_count
            call_count += 1
            raise NetworkError("not found", status_code=404)

        with pytest.raises(NetworkError):
            fails_404()
        assert call_count == 1  # No retry for 404


class TestCircuitBreaker:
    """Test the Circuit Breaker pattern implementation."""

    def test_initial_state_is_closed(self):
        """New circuit breaker should start in CLOSED state."""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.is_call_allowed()

    def test_opens_after_threshold_failures(self):
        """Circuit should open after failure_threshold consecutive failures."""
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert not cb.is_call_allowed()

    def test_half_open_after_recovery_timeout(self):
        """Circuit should transition to HALF_OPEN after recovery_timeout."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)  # Wait for recovery
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.is_call_allowed()

    def test_closes_after_half_open_successes(self):
        """Circuit should close after enough successes in HALF_OPEN state."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1, half_open_max_calls=2)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        # Now in HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_reopens_on_half_open_failure(self):
        """Circuit should reopen if a call fails in HALF_OPEN state."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        # Now in HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        """Explicit reset should return circuit to CLOSED state."""
        cb = CircuitBreaker("test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
