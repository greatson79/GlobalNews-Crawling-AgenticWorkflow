"""Tests for circuit_breaker.py — Per-Site Circuit Breaker Coordinator.

Verifies:
    - State machine transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.
    - Per-site isolation: different sites have independent circuit states.
    - Thread-safety: concurrent access does not corrupt state.
    - Block-type tracking: BlockAwareCircuitBreaker records block types.
    - Transition history: state changes are logged.
    - Coordinator: centralized management of all circuit breakers.
"""

import threading
import time

import pytest

from src.crawling.circuit_breaker import (
    BlockAwareCircuitBreaker,
    CircuitBreakerCoordinator,
)
from src.utils.error_handler import CircuitState


# =============================================================================
# BlockAwareCircuitBreaker Tests
# =============================================================================

class TestBlockAwareCircuitBreaker:
    """Tests for the extended CircuitBreaker with block tracking."""

    def test_initial_state_is_closed(self) -> None:
        """New circuit breaker should start CLOSED."""
        cb = BlockAwareCircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED

    def test_closed_to_open_after_threshold(self) -> None:
        """Circuit should open after failure_threshold failures."""
        cb = BlockAwareCircuitBreaker(name="test", failure_threshold=3)
        for i in range(3):
            cb.record_block_failure("ip_block")
        assert cb.state == CircuitState.OPEN

    def test_open_blocks_calls(self) -> None:
        """Open circuit should not allow calls."""
        cb = BlockAwareCircuitBreaker(name="test", failure_threshold=2)
        cb.record_block_failure("rate_limit")
        cb.record_block_failure("rate_limit")
        assert cb.state == CircuitState.OPEN
        assert cb.is_call_allowed() is False

    def test_open_to_half_open_after_timeout(self) -> None:
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        cb = BlockAwareCircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for fast test
        )
        cb.record_block_failure("captcha")
        cb.record_block_failure("captcha")
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.is_call_allowed() is True

    def test_half_open_to_closed_after_successes(self) -> None:
        """Circuit should close after enough successes in HALF_OPEN."""
        cb = BlockAwareCircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=2,
        )
        cb.record_block_failure("js_challenge")
        cb.record_block_failure("js_challenge")
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self) -> None:
        """Any failure in HALF_OPEN should re-open the circuit."""
        cb = BlockAwareCircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,
        )
        cb.record_block_failure("fingerprint")
        cb.record_block_failure("fingerprint")
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_block_failure("fingerprint")
        assert cb.state == CircuitState.OPEN

    def test_block_type_tracking(self) -> None:
        """Last block type should be recorded."""
        cb = BlockAwareCircuitBreaker(name="test")
        cb.record_block_failure("ip_block")
        assert cb.last_block_type == "ip_block"
        cb.record_block_failure("captcha")
        assert cb.last_block_type == "captcha"

    def test_transition_history(self) -> None:
        """State transitions should be recorded in history."""
        cb = BlockAwareCircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=1,
        )
        cb.record_block_failure("rate_limit")
        cb.record_block_failure("rate_limit")
        # CLOSED -> OPEN
        time.sleep(0.15)
        _ = cb.state  # Trigger OPEN -> HALF_OPEN
        cb.record_success()
        # HALF_OPEN -> CLOSED

        history = cb.transition_history
        assert len(history) >= 1  # At least CLOSED -> OPEN
        assert any(r["to_state"] == "open" for r in history)

    def test_reset(self) -> None:
        """reset() should return to CLOSED regardless of current state."""
        cb = BlockAwareCircuitBreaker(name="test", failure_threshold=2)
        cb.record_block_failure("ip_block")
        cb.record_block_failure("ip_block")
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_call_allowed() is True

    def test_get_status(self) -> None:
        """get_status() should return a complete status dict."""
        cb = BlockAwareCircuitBreaker(name="test_site")
        cb.record_block_failure("geo_block")
        status = cb.get_status()
        assert status["name"] == "test_site"
        assert status["state"] == "closed"
        assert status["last_block_type"] == "geo_block"
        assert isinstance(status["failure_count"], int)


# =============================================================================
# CircuitBreakerCoordinator Tests
# =============================================================================

class TestCircuitBreakerCoordinator:
    """Tests for the centralized circuit breaker coordinator."""

    def test_new_site_is_allowed(self) -> None:
        """New sites should be allowed (CLOSED by default)."""
        coord = CircuitBreakerCoordinator()
        assert coord.is_allowed("new_site") is True

    def test_per_site_isolation(self) -> None:
        """Failures on one site should not affect another."""
        coord = CircuitBreakerCoordinator(failure_threshold=2)
        coord.record_failure("site_a", "ip_block")
        coord.record_failure("site_a", "ip_block")
        assert coord.is_allowed("site_a") is False  # OPEN
        assert coord.is_allowed("site_b") is True   # Still CLOSED

    def test_record_success_closes_circuit(self) -> None:
        """Successes in HALF_OPEN should close the circuit."""
        coord = CircuitBreakerCoordinator(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=1,
        )
        coord.record_failure("test_site", "rate_limit")
        coord.record_failure("test_site", "rate_limit")
        assert coord.get_state("test_site") == CircuitState.OPEN

        time.sleep(0.15)
        assert coord.get_state("test_site") == CircuitState.HALF_OPEN

        coord.record_success("test_site")
        assert coord.get_state("test_site") == CircuitState.CLOSED

    def test_get_open_circuits(self) -> None:
        """get_open_circuits() should list all OPEN sites."""
        coord = CircuitBreakerCoordinator(failure_threshold=2)
        coord.record_failure("site_a", "ip_block")
        coord.record_failure("site_a", "ip_block")
        coord.record_failure("site_b", "captcha")
        coord.record_failure("site_b", "captcha")

        open_circuits = coord.get_open_circuits()
        assert "site_a" in open_circuits
        assert "site_b" in open_circuits

    def test_reset_site(self) -> None:
        """reset() should force a site back to CLOSED."""
        coord = CircuitBreakerCoordinator(failure_threshold=2)
        coord.record_failure("site_a", "ip_block")
        coord.record_failure("site_a", "ip_block")
        assert coord.get_state("site_a") == CircuitState.OPEN

        coord.reset("site_a")
        assert coord.get_state("site_a") == CircuitState.CLOSED

    def test_reset_all(self) -> None:
        """reset_all() should close all circuits."""
        coord = CircuitBreakerCoordinator(failure_threshold=2)
        coord.record_failure("site_a", "ip_block")
        coord.record_failure("site_a", "ip_block")
        coord.record_failure("site_b", "captcha")
        coord.record_failure("site_b", "captcha")

        coord.reset_all()
        assert coord.get_state("site_a") == CircuitState.CLOSED
        assert coord.get_state("site_b") == CircuitState.CLOSED

    def test_get_all_statuses(self) -> None:
        """get_all_statuses() should return status for all tracked sites."""
        coord = CircuitBreakerCoordinator()
        coord.record_failure("site_a", "ip_block")
        coord.record_success("site_b")

        statuses = coord.get_all_statuses()
        assert "site_a" in statuses
        assert "site_b" in statuses
        assert statuses["site_a"]["name"] == "site_a"
        assert statuses["site_b"]["name"] == "site_b"

    def test_get_statistics(self) -> None:
        """get_statistics() should return aggregate data."""
        coord = CircuitBreakerCoordinator(failure_threshold=2)
        coord.record_failure("site_a", "ip_block")
        coord.record_failure("site_a", "ip_block")
        coord.record_success("site_b")

        stats = coord.get_statistics()
        assert stats["total_circuits"] == 2
        assert stats["state_distribution"]["open"] >= 1
        assert "site_a" in stats["open_circuits"]


# =============================================================================
# Thread-Safety Tests
# =============================================================================

class TestThreadSafety:
    """Tests for thread-safe operation."""

    def test_concurrent_failures_on_same_site(self) -> None:
        """Concurrent failures on the same site should not corrupt state."""
        coord = CircuitBreakerCoordinator(failure_threshold=100)
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(50):
                    coord.record_failure("concurrent_site", "ip_block")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # State should be valid (CLOSED or OPEN, not corrupt)
        state = coord.get_state("concurrent_site")
        assert state in (CircuitState.CLOSED, CircuitState.OPEN)

    def test_concurrent_different_sites(self) -> None:
        """Concurrent access to different sites should not interfere."""
        coord = CircuitBreakerCoordinator(failure_threshold=5)
        errors: list[Exception] = []

        def worker(site_id: str) -> None:
            try:
                for _ in range(10):
                    coord.record_failure(site_id, "rate_limit")
                    coord.record_success(site_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"site_{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All 10 sites should be tracked
        assert coord.get_statistics()["total_circuits"] == 10
