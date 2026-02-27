"""Tests for anti_block.py — 6-Tier Escalation Engine.

Verifies:
    - Tier transitions (escalation and de-escalation) work correctly.
    - Profile persistence (save/load) round-trips correctly.
    - Block detection integration triggers escalation.
    - Per-site isolation: blocking on site A does not affect site B.
    - Tier 6 (human escalation) pauses the domain.
    - De-escalation after sustained success.
    - Statistics reporting.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.crawling.anti_block import (
    AntiBlockEngine,
    EscalationDecision,
    EscalationTier,
    SiteProfile,
    TIER_STRATEGIES,
    _DEESCALATION_SUCCESS_THRESHOLD,
    _ESCALATION_COOLDOWN_SECONDS,
    _ESCALATION_FAILURE_THRESHOLD,
)
from src.crawling.block_detector import (
    BlockDiagnosis,
    BlockDetector,
    BlockType,
    HttpResponse,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tmp_profiles(tmp_path: Path) -> Path:
    """Temporary path for site_profiles.json."""
    return tmp_path / "site_profiles.json"


@pytest.fixture
def engine(tmp_profiles: Path) -> AntiBlockEngine:
    """AntiBlockEngine with fresh state and temporary profile storage."""
    return AntiBlockEngine(profiles_path=tmp_profiles, auto_load=False)


# =============================================================================
# Profile Management
# =============================================================================

class TestSiteProfile:
    """Tests for SiteProfile serialization."""

    def test_to_dict_round_trip(self) -> None:
        """SiteProfile should serialize and deserialize correctly."""
        profile = SiteProfile(
            site_id="chosun",
            current_tier=3,
            consecutive_failures=2,
            total_blocks=10,
            total_successes=50,
            last_block_type="rate_limit",
            delay_seconds=10.0,
        )
        data = profile.to_dict()
        restored = SiteProfile.from_dict(data)
        assert restored.site_id == "chosun"
        assert restored.current_tier == 3
        assert restored.total_blocks == 10
        assert restored.total_successes == 50
        assert restored.delay_seconds == 10.0

    def test_from_dict_with_defaults(self) -> None:
        """SiteProfile.from_dict should use defaults for missing keys."""
        restored = SiteProfile.from_dict({"site_id": "test"})
        assert restored.site_id == "test"
        assert restored.current_tier == 1
        assert restored.consecutive_failures == 0

    def test_block_history_capped(self) -> None:
        """Block history should be capped at 50 entries."""
        profile = SiteProfile(
            site_id="test",
            block_history=["ip_block"] * 100,
        )
        data = profile.to_dict()
        assert len(data["block_history"]) == 50


# =============================================================================
# Escalation Logic
# =============================================================================

class TestEscalation:
    """Tests for tier escalation."""

    def test_initial_tier_is_one(self, engine: AntiBlockEngine) -> None:
        """New sites should start at Tier 1."""
        profile = engine.get_profile("new_site")
        assert profile.current_tier == 1

    def test_escalation_after_consecutive_failures(self, engine: AntiBlockEngine) -> None:
        """After ESCALATION_FAILURE_THRESHOLD consecutive failures, tier should escalate."""
        for i in range(_ESCALATION_FAILURE_THRESHOLD):
            decision = engine.record_result("test_site", was_blocked=True)

        profile = engine.get_profile("test_site")
        assert profile.current_tier == 2, (
            f"Expected tier 2 after {_ESCALATION_FAILURE_THRESHOLD} failures, "
            f"got tier {profile.current_tier}"
        )

    def test_fast_track_escalation_by_diagnosis(self, engine: AntiBlockEngine) -> None:
        """A diagnosis recommending a higher tier should fast-track escalation."""
        diagnosis = BlockDiagnosis(
            block_type=BlockType.CAPTCHA,
            confidence=0.9,
            evidence=["reCAPTCHA detected"],
            recommended_tier=4,
        )
        # Even a single failure with a high-tier recommendation should escalate
        for i in range(_ESCALATION_FAILURE_THRESHOLD):
            decision = engine.record_result("captcha_site", was_blocked=True, diagnosis=diagnosis)

        profile = engine.get_profile("captcha_site")
        assert profile.current_tier >= 4

    def test_escalation_caps_at_tier_6(self, engine: AntiBlockEngine) -> None:
        """Escalation should not exceed Tier 6."""
        # Force profile to tier 5
        profile = engine.get_profile("extreme_site")
        profile.current_tier = 5
        profile.last_escalation_time = 0.0  # Clear cooldown

        for i in range(_ESCALATION_FAILURE_THRESHOLD + 1):
            engine.record_result("extreme_site", was_blocked=True)

        assert engine.get_profile("extreme_site").current_tier <= 6

    def test_escalation_decision_has_evidence(self, engine: AntiBlockEngine) -> None:
        """EscalationDecision should contain reason and action strings."""
        for i in range(_ESCALATION_FAILURE_THRESHOLD):
            decision = engine.record_result("test_site", was_blocked=True)

        assert decision.action
        assert decision.reason
        assert decision.site_id == "test_site"

    def test_delay_increases_within_tier(self, engine: AntiBlockEngine) -> None:
        """Within a tier, delay should increase on each failure."""
        initial_delay = engine.get_profile("slow_site").delay_seconds
        engine.record_result("slow_site", was_blocked=True)
        after_one = engine.get_profile("slow_site").delay_seconds
        assert after_one > initial_delay


# =============================================================================
# De-Escalation Logic
# =============================================================================

class TestDeEscalation:
    """Tests for tier de-escalation."""

    def test_deescalation_after_consecutive_successes(self, engine: AntiBlockEngine) -> None:
        """After enough consecutive successes, tier should decrease."""
        # First, escalate to tier 2
        profile = engine.get_profile("recovery_site")
        profile.current_tier = 2
        profile.last_escalation_time = 0.0  # Clear cooldown
        profile.delay_seconds = TIER_STRATEGIES[2].min_delay

        for i in range(_DEESCALATION_SUCCESS_THRESHOLD):
            engine.record_result("recovery_site", was_blocked=False)

        assert engine.get_profile("recovery_site").current_tier == 1

    def test_deescalation_does_not_go_below_tier_1(self, engine: AntiBlockEngine) -> None:
        """De-escalation should never go below Tier 1."""
        profile = engine.get_profile("stable_site")
        profile.current_tier = 1
        profile.last_escalation_time = 0.0

        for i in range(_DEESCALATION_SUCCESS_THRESHOLD + 5):
            engine.record_result("stable_site", was_blocked=False)

        assert engine.get_profile("stable_site").current_tier == 1

    def test_failure_resets_success_counter(self, engine: AntiBlockEngine) -> None:
        """A single failure should reset the consecutive success counter."""
        profile = engine.get_profile("fragile_site")
        profile.current_tier = 2
        profile.last_escalation_time = 0.0

        # Almost enough successes
        for i in range(_DEESCALATION_SUCCESS_THRESHOLD - 1):
            engine.record_result("fragile_site", was_blocked=False)

        # One failure resets the counter
        engine.record_result("fragile_site", was_blocked=True)

        assert engine.get_profile("fragile_site").consecutive_successes == 0


# =============================================================================
# Per-Site Isolation
# =============================================================================

class TestSiteIsolation:
    """Tests for per-site state isolation."""

    def test_different_sites_independent(self, engine: AntiBlockEngine) -> None:
        """Blocking on site A should not affect site B."""
        # Block site A
        for i in range(_ESCALATION_FAILURE_THRESHOLD):
            engine.record_result("site_a", was_blocked=True)

        # Site B should still be at tier 1
        profile_b = engine.get_profile("site_b")
        assert profile_b.current_tier == 1
        assert profile_b.consecutive_failures == 0

    def test_success_on_one_site_does_not_help_another(self, engine: AntiBlockEngine) -> None:
        """Successes on site A should not de-escalate site B."""
        # Escalate site B
        profile_b = engine.get_profile("site_b")
        profile_b.current_tier = 3

        # Succeed on site A
        for i in range(_DEESCALATION_SUCCESS_THRESHOLD):
            engine.record_result("site_a", was_blocked=False)

        # Site B should still be at tier 3
        assert engine.get_profile("site_b").current_tier == 3


# =============================================================================
# Tier 6 (Human Escalation)
# =============================================================================

class TestHumanEscalation:
    """Tests for Tier 6 behavior."""

    def test_is_paused_at_tier_6(self, engine: AntiBlockEngine) -> None:
        """is_paused() should return True when site reaches Tier 6."""
        profile = engine.get_profile("blocked_site")
        profile.current_tier = 6
        assert engine.is_paused("blocked_site") is True

    def test_is_not_paused_below_tier_6(self, engine: AntiBlockEngine) -> None:
        """is_paused() should return False below Tier 6."""
        assert engine.is_paused("normal_site") is False

    def test_get_all_paused_sites(self, engine: AntiBlockEngine) -> None:
        """get_all_paused_sites() should list all Tier 6 sites."""
        engine.get_profile("paused_1").current_tier = 6
        engine.get_profile("paused_2").current_tier = 6
        engine.get_profile("active").current_tier = 3

        paused = engine.get_all_paused_sites()
        assert "paused_1" in paused
        assert "paused_2" in paused
        assert "active" not in paused

    def test_reset_site(self, engine: AntiBlockEngine) -> None:
        """reset_site() should bring a paused site back to Tier 1."""
        engine.get_profile("blocked_site").current_tier = 6
        engine.reset_site("blocked_site")
        assert engine.get_profile("blocked_site").current_tier == 1


# =============================================================================
# Persistence
# =============================================================================

class TestPersistence:
    """Tests for profile persistence (save/load)."""

    def test_save_and_load(self, tmp_profiles: Path) -> None:
        """Profiles should survive save/load cycle."""
        engine1 = AntiBlockEngine(profiles_path=tmp_profiles, auto_load=False)
        engine1.get_profile("site_a").current_tier = 3
        engine1.get_profile("site_b").total_blocks = 42
        engine1._save_profiles()

        assert tmp_profiles.exists()

        engine2 = AntiBlockEngine(profiles_path=tmp_profiles, auto_load=True)
        assert engine2.get_profile("site_a").current_tier == 3
        assert engine2.get_profile("site_b").total_blocks == 42

    def test_load_corrupt_file_starts_fresh(self, tmp_profiles: Path) -> None:
        """Corrupt profile file should not crash; starts fresh."""
        tmp_profiles.write_text("not valid json!!!")
        engine = AntiBlockEngine(profiles_path=tmp_profiles, auto_load=True)
        assert len(engine.profiles) == 0

    def test_load_missing_file_starts_fresh(self, tmp_profiles: Path) -> None:
        """Missing profile file should start fresh (no error)."""
        engine = AntiBlockEngine(profiles_path=tmp_profiles, auto_load=True)
        assert len(engine.profiles) == 0


# =============================================================================
# Strategy & Statistics
# =============================================================================

class TestStrategyAndStats:
    """Tests for strategy retrieval and statistics."""

    def test_get_strategy_returns_correct_tier(self, engine: AntiBlockEngine) -> None:
        """get_strategy() should return the strategy for the current tier."""
        engine.get_profile("test").current_tier = 3
        strategy = engine.get_strategy("test")
        assert strategy.tier == 3
        assert strategy.requires_browser is True

    def test_tier_strategies_complete(self) -> None:
        """All 6 tiers should be defined in TIER_STRATEGIES."""
        for tier in range(1, 7):
            assert tier in TIER_STRATEGIES
            assert TIER_STRATEGIES[tier].tier == tier

    def test_get_delay_includes_jitter(self, engine: AntiBlockEngine) -> None:
        """get_delay() should add jitter (not always the same value)."""
        delays = set()
        for _ in range(20):
            delays.add(round(engine.get_delay("jitter_test"), 3))
        # With jitter, we should get multiple distinct values
        assert len(delays) > 1

    def test_get_statistics(self, engine: AntiBlockEngine) -> None:
        """get_statistics() should return valid aggregate data."""
        engine.get_profile("site_a").current_tier = 1
        engine.get_profile("site_b").current_tier = 3
        engine.get_profile("site_c").current_tier = 6

        stats = engine.get_statistics()
        assert stats["total_sites"] == 3
        assert stats["tier_distribution"][1] == 1
        assert stats["tier_distribution"][3] == 1
        assert stats["tier_distribution"][6] == 1
        assert "site_c" in stats["paused_sites"]


# =============================================================================
# Block Detection Integration
# =============================================================================

class TestDetectionIntegration:
    """Tests for automatic block detection via response analysis."""

    def test_auto_detect_block_from_response(self, engine: AntiBlockEngine) -> None:
        """Passing a blocked response should auto-detect and escalate."""
        blocked_response = HttpResponse(
            status_code=429,
            headers={"Retry-After": "60"},
            body="Too Many Requests",
            url="https://example.com/article",
        )

        for i in range(_ESCALATION_FAILURE_THRESHOLD):
            decision = engine.record_result("auto_site", response=blocked_response)

        profile = engine.get_profile("auto_site")
        assert profile.total_blocks >= _ESCALATION_FAILURE_THRESHOLD
        assert profile.current_tier >= 2

    def test_normal_response_counts_as_success(self, engine: AntiBlockEngine) -> None:
        """A normal 200 response with real article content should count as a success."""
        normal_response = HttpResponse(
            status_code=200,
            body=(
                "<html><head><title>News</title></head>"
                "<body><article><h1>Breaking News Article</h1>"
                "<p>This is a substantial article with real content about "
                "current events and political developments around the world. "
                "The article continues with more detailed analysis.</p>"
                "</article></body></html>"
            ),
            url="https://example.com/article",
            original_url="https://example.com/article",
        )

        engine.record_result("success_site", response=normal_response)
        profile = engine.get_profile("success_site")
        assert profile.total_successes == 1
        assert profile.consecutive_successes == 1
