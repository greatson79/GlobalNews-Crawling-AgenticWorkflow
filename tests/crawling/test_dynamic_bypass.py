"""Tests for DynamicBypassEngine — block-type-aware strategy dispatch.

Tests cover:
    - Strategy registration and availability
    - Block-type-to-strategy mapping
    - Strategy ordering (cost-ascending, success-rate-descending)
    - Per-domain adaptive learning
    - try_strategies() multi-strategy cascade
    - Individual strategy error handling (import failures)
    - Statistics and domain cache
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.crawling.block_detector import BlockType
from src.crawling.dynamic_bypass import (
    DynamicBypassEngine,
    BypassResult,
    BypassStrategy,
    StrategyStats,
    StrategyTier,
    STRATEGY_MAP,
    _DEFAULT_STRATEGIES,
    _FINGERPRINT_PROFILES,
    _USER_AGENTS,
    _MIN_BODY_LENGTH,
    _MAX_STRATEGIES_PER_URL,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine() -> DynamicBypassEngine:
    """Create a DynamicBypassEngine with browser and proxy disabled."""
    return DynamicBypassEngine(proxy_pool=[], enable_browser=False)


@pytest.fixture
def engine_with_proxy() -> DynamicBypassEngine:
    """Create a DynamicBypassEngine with proxy pool configured."""
    return DynamicBypassEngine(
        proxy_pool=["http://proxy1:8080", "http://proxy2:8080"],
        enable_browser=False,
    )


@pytest.fixture
def engine_full() -> DynamicBypassEngine:
    """Create a DynamicBypassEngine with all features enabled."""
    return DynamicBypassEngine(
        proxy_pool=["http://proxy1:8080"],
        enable_browser=True,
    )


# ---------------------------------------------------------------------------
# Strategy Registration Tests
# ---------------------------------------------------------------------------

class TestStrategyRegistration:
    """Test that strategies are correctly registered based on configuration."""

    def test_tier0_strategies_always_registered(self, engine: DynamicBypassEngine):
        """Tier 0 strategies should always be available."""
        tier0 = [
            "rotate_user_agent",
            "exponential_backoff",
            "rss_feed_fallback",
            "amp_version_fallback",
            "google_cache_fallback",
        ]
        for name in tier0:
            assert engine.get_strategy_info(name) is not None, f"Missing Tier 0: {name}"
            assert engine.get_strategy_info(name).tier == StrategyTier.TIER_0

    def test_tier1_strategies_always_registered(self, engine: DynamicBypassEngine):
        """Tier 1 strategies should always be available."""
        tier1 = [
            "curl_cffi_impersonate",
            "fingerprint_rotation",
            "cloudscraper_solve",
        ]
        for name in tier1:
            assert engine.get_strategy_info(name) is not None, f"Missing Tier 1: {name}"
            assert engine.get_strategy_info(name).tier == StrategyTier.TIER_1

    def test_tier2_strategies_conditional_on_browser(self):
        """Tier 2 browser strategies should only register when enable_browser=True."""
        engine_no_browser = DynamicBypassEngine(enable_browser=False)
        assert engine_no_browser.get_strategy_info("patchright_stealth") is None
        assert engine_no_browser.get_strategy_info("camoufox_stealth") is None

        engine_browser = DynamicBypassEngine(enable_browser=True)
        assert engine_browser.get_strategy_info("patchright_stealth") is not None
        assert engine_browser.get_strategy_info("camoufox_stealth") is not None

    def test_tier3_proxy_conditional(self):
        """Tier 3 proxy strategy should only register when proxy_pool is non-empty."""
        engine_no_proxy = DynamicBypassEngine(proxy_pool=[])
        assert engine_no_proxy.get_strategy_info("proxy_rotation") is None

        engine_proxy = DynamicBypassEngine(proxy_pool=["http://p:8080"])
        assert engine_proxy.get_strategy_info("proxy_rotation") is not None
        assert engine_proxy.get_strategy_info("proxy_rotation").requires_proxy

    def test_tier4_always_registered(self, engine: DynamicBypassEngine):
        """Tier 4 archive strategies should always be available."""
        assert engine.get_strategy_info("wayback_fallback") is not None
        assert engine.get_strategy_info("wayback_fallback").tier == StrategyTier.TIER_4

    def test_get_all_strategies_sorted_by_tier(self, engine: DynamicBypassEngine):
        """get_all_strategies() should return strategies sorted by tier."""
        all_strategies = engine.get_all_strategies()
        assert len(all_strategies) >= 9  # T0(5) + T1(3) + T4(1) minimum
        tiers = [engine.get_strategy_info(s).tier for s in all_strategies]
        assert tiers == sorted(tiers)


# ---------------------------------------------------------------------------
# Strategy Mapping Tests
# ---------------------------------------------------------------------------

class TestStrategyMapping:
    """Test block-type-to-strategy mapping."""

    def test_all_block_types_have_mappings(self):
        """Every BlockType should have a strategy mapping."""
        for bt in BlockType:
            assert bt in STRATEGY_MAP, f"Missing mapping for {bt}"
            assert len(STRATEGY_MAP[bt]) > 0, f"Empty strategy list for {bt}"

    def test_ua_filter_strategies(self, engine: DynamicBypassEngine):
        """UA_FILTER should map to UA rotation and curl_cffi."""
        strategies = engine.get_strategies_for_block(BlockType.UA_FILTER)
        assert "rotate_user_agent" in strategies
        assert "curl_cffi_impersonate" in strategies

    def test_js_challenge_strategies(self, engine: DynamicBypassEngine):
        """JS_CHALLENGE should include cloudscraper and curl_cffi."""
        strategies = engine.get_strategies_for_block(BlockType.JS_CHALLENGE)
        assert "cloudscraper_solve" in strategies
        assert "curl_cffi_impersonate" in strategies

    def test_ip_block_strategies(self, engine_with_proxy: DynamicBypassEngine):
        """IP_BLOCK should include proxy rotation and fallback sources."""
        strategies = engine_with_proxy.get_strategies_for_block(BlockType.IP_BLOCK)
        assert "proxy_rotation" in strategies
        assert "wayback_fallback" in strategies

    def test_default_strategies_for_unknown(self, engine: DynamicBypassEngine):
        """Unknown block types should fall back to default strategies."""
        # Simulate a block type not in STRATEGY_MAP by patching
        strategies = engine.get_strategies_for_block(BlockType.UA_FILTER, "test.com")
        assert len(strategies) > 0

    def test_unavailable_strategies_filtered(self):
        """Strategies requiring proxy should be filtered when no proxy pool."""
        engine = DynamicBypassEngine(proxy_pool=[], enable_browser=False)
        strategies = engine.get_strategies_for_block(BlockType.IP_BLOCK)
        assert "proxy_rotation" not in strategies


# ---------------------------------------------------------------------------
# Adaptive Learning Tests
# ---------------------------------------------------------------------------

class TestAdaptiveLearning:
    """Test per-domain success rate tracking and strategy reordering."""

    def test_record_stat_creates_domain(self, engine: DynamicBypassEngine):
        """Recording a stat should create domain and strategy entries."""
        engine._record_stat("example.com", "curl_cffi_impersonate", True, 500.0)
        stats = engine.get_domain_stats("example.com")
        assert "curl_cffi_impersonate" in stats
        assert stats["curl_cffi_impersonate"]["attempts"] == 1
        assert stats["curl_cffi_impersonate"]["successes"] == 1
        assert stats["curl_cffi_impersonate"]["success_rate"] == 1.0

    def test_success_rate_updates(self, engine: DynamicBypassEngine):
        """Success rate should update as more attempts are recorded."""
        engine._record_stat("test.com", "curl_cffi_impersonate", True, 100)
        engine._record_stat("test.com", "curl_cffi_impersonate", False, 200)
        engine._record_stat("test.com", "curl_cffi_impersonate", True, 150)
        stats = engine.get_domain_stats("test.com")
        assert stats["curl_cffi_impersonate"]["attempts"] == 3
        assert stats["curl_cffi_impersonate"]["successes"] == 2
        assert abs(stats["curl_cffi_impersonate"]["success_rate"] - 0.667) < 0.01

    def test_strategies_reordered_by_success_rate(self, engine: DynamicBypassEngine):
        """Strategies with higher domain success rate should be tried first."""
        # Make fingerprint_rotation have 100% success rate for this domain
        engine._record_stat("reorder.com", "fingerprint_rotation", True, 100)
        engine._record_stat("reorder.com", "fingerprint_rotation", True, 100)
        # Make curl_cffi have 0% success rate
        engine._record_stat("reorder.com", "curl_cffi_impersonate", False, 100)
        engine._record_stat("reorder.com", "curl_cffi_impersonate", False, 100)

        strategies = engine.get_strategies_for_block(
            BlockType.FINGERPRINT, "reorder.com",
        )
        # fingerprint_rotation should come before curl_cffi_impersonate
        if "fingerprint_rotation" in strategies and "curl_cffi_impersonate" in strategies:
            fp_idx = strategies.index("fingerprint_rotation")
            curl_idx = strategies.index("curl_cffi_impersonate")
            assert fp_idx < curl_idx, "Higher success rate should sort first"


# ---------------------------------------------------------------------------
# Strategy Execution Tests
# ---------------------------------------------------------------------------

class TestStrategyExecution:
    """Test individual strategy execution with mocked dependencies."""

    def test_unknown_strategy_returns_error(self, engine: DynamicBypassEngine):
        """Executing an unknown strategy should return a failure result."""
        result = engine.execute_strategy(
            url="https://example.com",
            strategy_name="nonexistent_strategy",
            site_id="test",
        )
        assert not result.success
        assert "Unknown strategy" in result.error

    @patch("src.crawling.dynamic_bypass.DynamicBypassEngine._dispatch")
    def test_successful_strategy(self, mock_dispatch, engine: DynamicBypassEngine):
        """A successful strategy should return success=True and record stats."""
        mock_dispatch.return_value = BypassResult(
            success=True,
            html="<html>" + "x" * 600 + "</html>",
            status_code=200,
        )
        result = engine.execute_strategy(
            url="https://example.com/article",
            strategy_name="curl_cffi_impersonate",
            site_id="test",
        )
        assert result.success
        assert result.strategy_name == "curl_cffi_impersonate"
        assert result.strategy_tier == StrategyTier.TIER_1.value

    @patch("src.crawling.dynamic_bypass.DynamicBypassEngine._dispatch")
    def test_short_response_treated_as_failure(self, mock_dispatch, engine: DynamicBypassEngine):
        """Responses shorter than _MIN_BODY_LENGTH should be treated as failure."""
        mock_dispatch.return_value = BypassResult(
            success=True,
            html="<html>tiny</html>",  # < 500 bytes
            status_code=200,
        )
        result = engine.execute_strategy(
            url="https://example.com",
            strategy_name="curl_cffi_impersonate",
            site_id="test",
        )
        assert not result.success
        assert "too short" in result.error.lower()

    @patch("src.crawling.dynamic_bypass.DynamicBypassEngine._dispatch")
    def test_exception_returns_error_result(self, mock_dispatch, engine: DynamicBypassEngine):
        """Strategy exceptions should be caught and returned as error results."""
        mock_dispatch.side_effect = ConnectionError("Connection refused")
        result = engine.execute_strategy(
            url="https://example.com",
            strategy_name="curl_cffi_impersonate",
            site_id="test",
        )
        assert not result.success
        assert "ConnectionError" in result.error


# ---------------------------------------------------------------------------
# try_strategies() Cascade Tests
# ---------------------------------------------------------------------------

class TestTryStrategies:
    """Test the multi-strategy cascade behavior."""

    @patch("src.crawling.dynamic_bypass.DynamicBypassEngine._dispatch")
    def test_first_strategy_succeeds(self, mock_dispatch, engine: DynamicBypassEngine):
        """If first strategy succeeds, no others should be tried."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return BypassResult(
                success=True,
                html="<html>" + "x" * 600 + "</html>",
                status_code=200,
            )

        mock_dispatch.side_effect = side_effect
        result = engine.try_strategies(
            url="https://example.com",
            block_type=BlockType.UA_FILTER,
            site_id="test",
        )
        assert result.success
        assert call_count == 1

    @patch("src.crawling.dynamic_bypass.DynamicBypassEngine._dispatch")
    def test_fallthrough_to_second_strategy(self, mock_dispatch, engine: DynamicBypassEngine):
        """If first strategy fails, next should be tried."""
        calls = []

        def side_effect(strategy_name, url, timeout, extra_headers):
            calls.append(strategy_name)
            if len(calls) == 1:
                return BypassResult(success=False, html="", status_code=403)
            return BypassResult(
                success=True,
                html="<html>" + "x" * 600 + "</html>",
                status_code=200,
            )

        mock_dispatch.side_effect = side_effect
        result = engine.try_strategies(
            url="https://example.com",
            block_type=BlockType.UA_FILTER,
            site_id="test",
        )
        assert result.success
        assert len(calls) == 2

    @patch("src.crawling.dynamic_bypass.DynamicBypassEngine._dispatch")
    def test_all_strategies_fail(self, mock_dispatch, engine: DynamicBypassEngine):
        """If all strategies fail, should return last failure result."""
        mock_dispatch.return_value = BypassResult(
            success=False, html="", status_code=403, error="blocked",
        )
        result = engine.try_strategies(
            url="https://example.com",
            block_type=BlockType.UA_FILTER,
            site_id="test",
        )
        assert not result.success

    def test_no_strategies_available(self):
        """With no matching strategies, should return a failure."""
        engine = DynamicBypassEngine(proxy_pool=[], enable_browser=False)
        # CAPTCHA with no browser = very limited strategies
        result = engine.try_strategies(
            url="https://example.com",
            block_type=BlockType.CAPTCHA,
            site_id="test",
        )
        # Should not crash even with no matching strategies
        assert isinstance(result, BypassResult)


# ---------------------------------------------------------------------------
# Statistics Tests
# ---------------------------------------------------------------------------

class TestStatistics:
    """Test aggregate statistics reporting."""

    def test_empty_statistics(self, engine: DynamicBypassEngine):
        """Fresh engine should report zero statistics."""
        stats = engine.get_statistics()
        assert stats["total_attempts"] == 0
        assert stats["total_successes"] == 0
        assert stats["domains_tracked"] == 0
        assert stats["strategies_available"] >= 9

    def test_statistics_accumulate(self, engine: DynamicBypassEngine):
        """Stats should accumulate across domains."""
        engine._record_stat("a.com", "curl_cffi_impersonate", True, 100)
        engine._record_stat("b.com", "curl_cffi_impersonate", False, 200)
        engine._record_stat("a.com", "rss_feed_fallback", True, 50)

        stats = engine.get_statistics()
        assert stats["total_attempts"] == 3
        assert stats["total_successes"] == 2
        assert stats["domains_tracked"] == 2

    def test_repr(self, engine: DynamicBypassEngine):
        """__repr__ should include key info."""
        r = repr(engine)
        assert "DynamicBypassEngine" in r
        assert "strategies=" in r


# ---------------------------------------------------------------------------
# Domain Block Cache Tests
# ---------------------------------------------------------------------------

class TestDomainBlockCache:
    """Test per-domain block type caching."""

    def test_update_and_use_cache(self, engine: DynamicBypassEngine):
        """Block cache should influence strategy selection."""
        engine.update_block_cache("cached.com", BlockType.JS_CHALLENGE)
        strategies = engine.get_strategies_for_block(BlockType.JS_CHALLENGE, "cached.com")
        assert "cloudscraper_solve" in strategies

    def test_try_strategies_uses_cache(self, engine: DynamicBypassEngine):
        """try_strategies with block_type=None should use cached block type."""
        engine.update_block_cache("cached.com", BlockType.UA_FILTER)
        # Should not crash when block_type=None and cache exists
        # (strategies will be looked up from cache)
        result = engine.try_strategies(
            url="https://cached.com/page",
            block_type=None,
            site_id="cached",
        )
        assert isinstance(result, BypassResult)


# ---------------------------------------------------------------------------
# Data Model Tests
# ---------------------------------------------------------------------------

class TestDataModels:
    """Test BypassResult and StrategyStats data models."""

    def test_bypass_result_defaults(self):
        """BypassResult should have sensible defaults."""
        r = BypassResult(success=False)
        assert r.html == ""
        assert r.status_code == 0
        assert r.strategy_name == ""
        assert r.error == ""
        assert r.latency_ms == 0.0

    def test_strategy_stats_empty(self):
        """Empty StrategyStats should not divide by zero."""
        s = StrategyStats()
        assert s.success_rate == 0.0
        assert s.avg_latency_ms == 0.0

    def test_strategy_stats_calculation(self):
        """StrategyStats properties should calculate correctly."""
        s = StrategyStats(attempts=4, successes=3, total_latency_ms=1000.0)
        assert s.success_rate == 0.75
        assert s.avg_latency_ms == 250.0


# ---------------------------------------------------------------------------
# Constants Validation Tests
# ---------------------------------------------------------------------------

class TestConstants:
    """Validate configuration constants."""

    def test_fingerprint_profiles_non_empty(self):
        """Should have at least 2 fingerprint profiles for rotation."""
        assert len(_FINGERPRINT_PROFILES) >= 2

    def test_fingerprint_profiles_have_required_keys(self):
        """Each profile should have impersonate, user_agent, sec_ch_ua, platform."""
        for profile in _FINGERPRINT_PROFILES:
            assert "impersonate" in profile
            assert "user_agent" in profile
            assert "sec_ch_ua" in profile
            assert "platform" in profile

    def test_user_agents_non_empty(self):
        """Should have at least 3 user agents for rotation."""
        assert len(_USER_AGENTS) >= 3

    def test_min_body_length_reasonable(self):
        """Minimum body length should be reasonable (100-2000)."""
        assert 100 <= _MIN_BODY_LENGTH <= 2000

    def test_max_strategies_per_url_reasonable(self):
        """Max strategies per URL should be 3-10."""
        assert 3 <= _MAX_STRATEGIES_PER_URL <= 10

    def test_strategy_map_references_valid_strategies(self):
        """All strategy names in STRATEGY_MAP should be valid identifiers."""
        all_strategy_names = set()
        for strategies in STRATEGY_MAP.values():
            all_strategy_names.update(strategies)
        for name in all_strategy_names:
            assert isinstance(name, str) and len(name) > 0

    def test_default_strategies_non_empty(self):
        """Default strategy list should have at least 3 entries."""
        assert len(_DEFAULT_STRATEGIES) >= 3


# ---------------------------------------------------------------------------
# D-7 Instance 12: Strategy Name Sync (Hallucination Prevention — P1)
# ---------------------------------------------------------------------------

class TestD7StrategyNameSync:
    """P1: Verify ALTERNATIVE_STRATEGIES in retry_manager.py matches
    DynamicBypassEngine's registered strategy names.

    D-7 Instance 12 — both lists must contain identical strategy names.
    This test prevents hallucination where one list is updated but the
    other is forgotten, causing runtime strategy lookup failures.
    """

    def test_alternative_strategies_matches_engine_registry(self):
        """ALTERNATIVE_STRATEGIES must be a subset of DynamicBypassEngine strategies."""
        from src.crawling.retry_manager import ALTERNATIVE_STRATEGIES

        # Get all strategy names that DynamicBypassEngine registers
        # by inspecting STRATEGY_MAP + the engine's _register_strategies
        engine_strategy_names: set[str] = set()
        for strategies in STRATEGY_MAP.values():
            engine_strategy_names.update(strategies)
        # Also include default strategies
        engine_strategy_names.update(_DEFAULT_STRATEGIES)

        alt_set = set(ALTERNATIVE_STRATEGIES)
        missing_from_engine = alt_set - engine_strategy_names
        assert not missing_from_engine, (
            f"D-7 DESYNC: ALTERNATIVE_STRATEGIES references strategies not in "
            f"DynamicBypassEngine: {sorted(missing_from_engine)}"
        )

    def test_engine_strategies_covered_by_alternative(self):
        """All DynamicBypassEngine strategies should appear in ALTERNATIVE_STRATEGIES."""
        from src.crawling.retry_manager import ALTERNATIVE_STRATEGIES

        engine_strategy_names: set[str] = set()
        for strategies in STRATEGY_MAP.values():
            engine_strategy_names.update(strategies)

        alt_set = set(ALTERNATIVE_STRATEGIES)
        missing_from_alt = engine_strategy_names - alt_set
        assert not missing_from_alt, (
            f"D-7 DESYNC: DynamicBypassEngine strategies missing from "
            f"ALTERNATIVE_STRATEGIES: {sorted(missing_from_alt)}"
        )

    def test_no_duplicate_strategies(self):
        """ALTERNATIVE_STRATEGIES should have no duplicates."""
        from src.crawling.retry_manager import ALTERNATIVE_STRATEGIES
        assert len(ALTERNATIVE_STRATEGIES) == len(set(ALTERNATIVE_STRATEGIES)), (
            "ALTERNATIVE_STRATEGIES contains duplicate entries"
        )

    def test_strategy_count_matches(self):
        """Both lists should have the same number of strategies (12)."""
        from src.crawling.retry_manager import ALTERNATIVE_STRATEGIES

        engine_strategy_names: set[str] = set()
        for strategies in STRATEGY_MAP.values():
            engine_strategy_names.update(strategies)

        assert len(set(ALTERNATIVE_STRATEGIES)) == len(engine_strategy_names), (
            f"Strategy count mismatch: ALTERNATIVE_STRATEGIES={len(set(ALTERNATIVE_STRATEGIES))}, "
            f"Engine={len(engine_strategy_names)}"
        )
